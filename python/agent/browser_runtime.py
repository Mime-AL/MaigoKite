"""Persistent Playwright browser sessions owned by Agent Core."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


class BrowserRuntimeUnavailable(RuntimeError):
    """Raised when the optional browser runtime cannot be started."""


async def _require_public_http_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("browser navigation requires an HTTP(S) URL")
    if parsed.username or parsed.password:
        raise ValueError("browser URLs must not contain embedded credentials")
    addresses = await asyncio.to_thread(
        socket.getaddrinfo,
        parsed.hostname,
        parsed.port or (443 if parsed.scheme == "https" else 80),
    )
    if any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("private, loopback, link-local, and reserved browser targets are not allowed")


class BrowserRuntime:
    """Lazily starts Chromium and keeps isolated pages by opaque session ID."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        headless: bool = True,
        executable_path: str | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root).expanduser().resolve()
        self.headless = headless
        self.executable_path = executable_path or None
        self._playwright: Any | None = None
        self._browser: Any | None = None
        self._pages: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def _ensure_browser(self) -> Any:
        async with self._lock:
            if self._browser is not None and self._browser.is_connected():
                return self._browser
            if self._playwright is not None:
                # A disconnected Chromium must not orphan its previous driver.
                await self._playwright.stop()
                self._playwright = self._browser = None
                self._pages.clear()
            try:
                from playwright.async_api import async_playwright
            except ImportError as exc:
                raise BrowserRuntimeUnavailable(
                    "Playwright is not installed; reinstall the Agent Core with browser dependencies"
                ) from exc
            self._playwright = await async_playwright().start()
            options: dict[str, Any] = {"headless": self.headless}
            if self.executable_path:
                options["executable_path"] = self.executable_path
            try:
                self._browser = await self._playwright.chromium.launch(**options)
            except BaseException as exc:
                await self._playwright.stop()
                self._playwright = None
                if not isinstance(exc, Exception):
                    raise
                raise BrowserRuntimeUnavailable(
                    "Chromium could not start; configure browser.executable_path or install Playwright Chromium"
                ) from exc
            return self._browser

    async def open(self, url: str) -> dict[str, Any]:
        await _require_public_http_url(url)
        browser = await self._ensure_browser()
        context = await browser.new_context(accept_downloads=False)
        session_id = f"browser_{uuid.uuid4().hex}"
        try:
            await context.route("**/*", self._guard_request)
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            self._pages[session_id] = page
            return await self.snapshot(session_id)
        except BaseException:
            self._pages.pop(session_id, None)
            await context.close()
            raise

    async def snapshot(self, session_id: str) -> dict[str, Any]:
        page = self._require_page(session_id)
        text = await page.locator("body").inner_text(timeout=10_000)
        return {
            "session_id": session_id,
            "url": page.url,
            "title": await page.title(),
            "text": text[:20_000],
            "truncated": len(text) > 20_000,
        }

    async def click(self, session_id: str, selector: str) -> dict[str, Any]:
        page = self._require_page(session_id)
        await page.locator(selector).first.click(timeout=10_000)
        await page.wait_for_timeout(250)
        return await self.snapshot(session_id)

    async def fill(self, session_id: str, selector: str, text: str) -> dict[str, Any]:
        page = self._require_page(session_id)
        await page.locator(selector).first.fill(text, timeout=10_000)
        return {"session_id": session_id, "url": page.url, "selector": selector, "filled": True}

    async def press(self, session_id: str, selector: str, key: str) -> dict[str, Any]:
        page = self._require_page(session_id)
        await page.locator(selector).first.press(key, timeout=10_000)
        await page.wait_for_timeout(250)
        return await self.snapshot(session_id)

    async def screenshot(
        self, session_id: str, path: str, *, workspace_root: str | Path | None = None
    ) -> dict[str, Any]:
        page = self._require_page(session_id)
        root = Path(workspace_root).expanduser().resolve() if workspace_root is not None else self.workspace_root
        target = Path(path).expanduser()
        if not target.is_absolute():
            target = root / target
        target = target.resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ValueError("browser screenshot path is outside the workspace") from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(target), full_page=True)
        return {"session_id": session_id, "url": page.url, "path": str(target)}

    async def close_session(self, session_id: str) -> dict[str, Any]:
        page = self._pages.pop(session_id, None)
        if page is None:
            raise KeyError(f"browser session not found: {session_id}")
        await page.context.close()
        return {"session_id": session_id, "closed": True}

    async def close(self) -> None:
        pages, self._pages = list(self._pages.values()), {}
        errors: list[Exception] = []
        for page in pages:
            try:
                await page.context.close()
            except Exception as exc:
                errors.append(exc)
        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception as exc:
                errors.append(exc)
            finally:
                self._browser = None
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception as exc:
                errors.append(exc)
            finally:
                self._playwright = None
        if errors:
            raise ExceptionGroup("Browser cleanup failed", errors)

    async def _guard_request(self, route: Any) -> None:
        """Apply the public-network boundary to redirects and page subresources too."""
        request_url = str(route.request.url)
        parsed = urlsplit(request_url)
        if parsed.scheme in {"data", "blob", "about"}:
            await route.continue_()
            return
        try:
            await _require_public_http_url(request_url)
        except (OSError, ValueError):
            await route.abort("blockedbyclient")
            return
        await route.continue_()

    def _require_page(self, session_id: str) -> Any:
        page = self._pages.get(session_id)
        if page is None or page.is_closed():
            raise KeyError(f"browser session not found: {session_id}")
        return page
