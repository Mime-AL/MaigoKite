"""Persistent Playwright browser sessions owned by Agent Core."""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import logging
import os
import re
import socket
import tempfile
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
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
        profile_directory: str | Path | None = None,
        max_sessions: int = 4,
        idle_timeout_seconds: float = 1800,
    ) -> None:
        self.workspace_root = Path(workspace_root).expanduser().resolve()
        self.headless = headless
        self.executable_path = executable_path or None
        self.profile_directory = Path(profile_directory or "~/.maigokite/browser-profiles").expanduser().resolve()
        self._playwright: Any | None = None
        self._browser: Any | None = None
        self._pages: dict[str, Any] = {}
        self._contexts: dict[str, Any] = {}
        self._owners: dict[str, tuple[str, str, str]] = {}
        self._profiles: dict[str, str] = {}
        self._lock = asyncio.Lock()
        if not 1 <= max_sessions <= 16 or not 60 <= idle_timeout_seconds <= 86400:
            raise ValueError("browser limits require 1–16 sessions and 60–86400 idle seconds")
        self.max_sessions = max_sessions
        self.idle_timeout_seconds = idle_timeout_seconds
        self._opening: set[str] = set()
        self._operations: dict[str, asyncio.Lock] = {}
        self._last_used: dict[str, float] = {}
        self._reaper: asyncio.Task[None] | None = None
        self._closing = False

    @asynccontextmanager
    async def operation(self, session_id: str, owner: tuple[str, str, str]) -> AsyncIterator[None]:
        """Serialize one page; cancelling a queued caller never closes its owner."""
        if self._closing:
            raise BrowserRuntimeUnavailable("Browser runtime is shutting down")
        self.require_owner(session_id, owner)
        lock = self._operations[session_id]
        async with lock:
            self.require_owner(session_id, owner)
            try:
                async with asyncio.timeout(90):
                    yield
            except (asyncio.CancelledError, TimeoutError):
                # Cancellation of the Python waiter alone does not stop Chromium.
                # Only the caller holding this page's lock may close the context.
                if session_id in self._pages:
                    await self.close_session(session_id)
                raise
            finally:
                if session_id in self._pages:
                    self._last_used[session_id] = asyncio.get_running_loop().time()

    async def _reap_idle(self) -> None:
        now = asyncio.get_running_loop().time()
        for session_id, used in list(self._last_used.items()):
            lock = self._operations.get(session_id)
            if (lock is None or lock.locked() or session_id in self._opening
                    or now - used < self.idle_timeout_seconds):
                continue
            async with lock:
                # Keep ownership if close fails; Core shutdown will retry it.
                if session_id in self._contexts:
                    try:
                        await self.close_session(session_id)
                    except Exception as exc:
                        logging.getLogger(__name__).warning("Idle browser cleanup: %s", type(exc).__name__)

    async def _reap_loop(self) -> None:
        while True:
            await asyncio.sleep(min(60, self.idle_timeout_seconds))
            await self._reap_idle()

    async def _ensure_playwright(self) -> Any:
        async with self._lock:
            if self._playwright is not None:
                return self._playwright
            try:
                from playwright.async_api import async_playwright
            except ImportError as exc:
                raise BrowserRuntimeUnavailable(
                    "Playwright is not installed; reinstall the Agent Core with browser dependencies"
                ) from exc
            self._playwright = await async_playwright().start()
            return self._playwright

    async def _ensure_browser(self) -> Any:
        driver = await self._ensure_playwright()
        async with self._lock:
            if self._browser is not None and self._browser.is_connected():
                return self._browser
            options: dict[str, Any] = {"headless": self.headless, "chromium_sandbox": True}
            if self.executable_path:
                options["executable_path"] = self.executable_path
            try:
                self._browser = await driver.chromium.launch(**options)
            except BaseException as exc:
                # Other persistent contexts may still own this shared driver.
                if not isinstance(exc, Exception):
                    raise
                raise BrowserRuntimeUnavailable(
                    "Chromium could not start with its native sandbox; use a supported non-root environment "
                    "and install Playwright Chromium. Sandboxing will not be disabled automatically."
                ) from exc
            return self._browser

    async def open(
        self, url: str, *, owner: tuple[str, str, str] = ("personal", "", ""),
        profile: str = "", visible: bool = False,
    ) -> dict[str, Any]:
        if self._closing:
            raise BrowserRuntimeUnavailable("Browser runtime is shutting down")
        await _require_public_http_url(url)
        await self._reap_idle()
        if self._closing:
            raise BrowserRuntimeUnavailable("Browser runtime is shutting down")
        session_id = f"browser_{uuid.uuid4().hex}"
        context = None
        profile_key = ""
        if visible and not profile:
            raise ValueError("visible login requires an explicit browser profile")
        if profile:
            if not re.fullmatch(r"[a-zA-Z0-9_-]{1,48}", profile):
                raise ValueError("browser profile must be a short name, not a path")
            # Reusable within one workspace, but never concurrently shared by
            # two conversations. No import of the user's everyday Chrome profile.
            profile_key = hashlib.sha256(f"{owner[0]}:{owner[2]}:{profile}".encode()).hexdigest()
            if profile_key in self._profiles:
                raise ValueError("browser profile is already open; close its current session first")
            self._profiles[profile_key] = session_id
        # Reserve before the first launch await, including in-flight openings.
        if len(self._contexts.keys() | self._opening) >= self.max_sessions:
            self._forget(session_id)
            raise ValueError("浏览器会话已达上限，请先关闭不再使用的页面。")
        self._opening.add(session_id)
        try:
            if profile_key:
                driver = await self._ensure_playwright()
                directory = self.profile_directory / profile_key
                if directory.is_symlink():
                    raise ValueError("browser profile must not be a symbolic link")
                directory.mkdir(mode=0o700, parents=True, exist_ok=True)
                self.profile_directory.chmod(0o700)
                directory.chmod(0o700)
                options: dict[str, Any] = {
                    "headless": False if visible else self.headless,
                    "chromium_sandbox": True,
                    "accept_downloads": True, "service_workers": "block",
                }
                if self.executable_path:
                    options["executable_path"] = self.executable_path
                try:
                    context = await driver.chromium.launch_persistent_context(str(directory), **options)
                except Exception as exc:
                    raise BrowserRuntimeUnavailable(
                        "无法带原生沙箱打开独立浏览器配置；请使用受支持的非 root 环境并检查 Chromium、"
                        "配置目录是否被占用；可见登录还需要桌面显示环境。不会自动禁用沙箱。"
                    ) from exc
            else:
                browser = await self._ensure_browser()
                context = await browser.new_context(accept_downloads=True, service_workers="block")
            # Own the context before navigation; a failed/cancelled opening must
            # remain reclaimable even if Playwright's first close attempt fails.
            self._contexts[session_id] = context
            self._owners[session_id] = owner
            self._operations[session_id] = asyncio.Lock()
            self._last_used[session_id] = asyncio.get_running_loop().time()
            context.on("close", lambda: self._forget(session_id))
            await context.route("**/*", self._guard_request)
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            self._pages[session_id] = page
            self._last_used[session_id] = asyncio.get_running_loop().time()
            if self._reaper is None or self._reaper.done():
                self._reaper = asyncio.create_task(self._reap_loop(), name="browser-idle-cleanup")
            return {**await self.snapshot(session_id), "profile": profile, "visible": visible,
                    "login_hint": "Complete login in the browser window, then ask the agent to continue." if visible else ""}
        except BaseException:
            if context is not None:
                await context.close()
            self._forget(session_id)
            raise
        finally:
            self._opening.discard(session_id)

    def require_owner(self, session_id: str, owner: tuple[str, str, str]) -> None:
        self._require_page(session_id)
        if self._owners.get(session_id) != owner:
            raise ValueError("browser session belongs to another conversation or workspace")

    def _forget(self, session_id: str) -> None:
        self._pages.pop(session_id, None)
        self._contexts.pop(session_id, None)
        self._owners.pop(session_id, None)
        self._operations.pop(session_id, None)
        self._last_used.pop(session_id, None)
        for key, value in list(self._profiles.items()):
            if value == session_id:
                self._profiles.pop(key, None)

    def _workspace_path(self, path: str, workspace_root: str | Path | None, *, unrestricted: bool = False) -> Path:
        root = Path(workspace_root).expanduser().resolve() if workspace_root is not None else self.workspace_root
        target = Path(path).expanduser()
        target = (target if target.is_absolute() else root / target).resolve()
        if not unrestricted and (not target.is_relative_to(root) or target.is_relative_to(self.profile_directory)):
            raise ValueError("browser file path is outside the allowed workspace")
        return target

    async def upload(self, session_id: str, selector: str, path: str, *, expected_url: str, workspace_root: str | Path | None = None, unrestricted: bool = False) -> dict[str, Any]:
        page = self._require_page(session_id)
        if page.url != expected_url:
            raise ValueError("browser page changed after approval; inspect it and request approval again")
        target = self._workspace_path(path, workspace_root, unrestricted=unrestricted)
        if not target.is_file() or target.stat().st_size > 50 * 1024 * 1024:
            raise ValueError("upload requires a regular workspace file no larger than 50 MiB")
        await page.locator(selector).first.set_input_files(str(target), timeout=10_000)
        return {"session_id": session_id, "url": page.url, "path": str(target), "uploaded": True}

    async def download(self, session_id: str, selector: str, path: str, *, expected_url: str, workspace_root: str | Path | None = None, unrestricted: bool = False) -> dict[str, Any]:
        page = self._require_page(session_id)
        if page.url != expected_url:
            raise ValueError("browser page changed after approval; inspect it and request approval again")
        target = self._workspace_path(path, workspace_root, unrestricted=unrestricted)
        if target.exists():
            raise ValueError("download destination already exists; choose a new filename")
        target.parent.mkdir(parents=True, exist_ok=True)
        download = None
        try:
            async with asyncio.timeout(60):
                async with page.expect_download(timeout=30_000) as pending:
                    await page.locator(selector).first.click(timeout=10_000)
                download = await pending.value
                with tempfile.TemporaryDirectory(prefix=".maigokite-download-", dir=target.parent) as staging:
                    temporary = Path(staging) / "download"
                    await download.save_as(str(temporary))
                    if temporary.stat().st_size > 50 * 1024 * 1024:
                        raise ValueError("download exceeds 50 MiB")
                    # Publish atomically without overwriting an existing file.
                    if self._workspace_path(str(target), workspace_root, unrestricted=unrestricted) != target:
                        raise ValueError("download destination changed during execution")
                    os.link(temporary, target)
            return {"session_id": session_id, "url": page.url, "path": str(target), "downloaded": True}
        finally:
            if download is not None:
                try:
                    await download.cancel()
                    await download.delete()
                except Exception as exc:
                    # The file may already be committed. Do not report that a
                    # successful download failed merely because Chromium closed.
                    logging.getLogger(__name__).warning("Browser download cleanup: %s", type(exc).__name__)

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
        self, session_id: str, path: str, *, workspace_root: str | Path | None = None, unrestricted: bool = False
    ) -> dict[str, Any]:
        page = self._require_page(session_id)
        target = self._workspace_path(path, workspace_root, unrestricted=unrestricted)
        target.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(target), full_page=True)
        return {"session_id": session_id, "url": page.url, "path": str(target)}

    async def close_session(self, session_id: str) -> dict[str, Any]:
        context = self._contexts.get(session_id)
        if context is None:
            raise KeyError(f"browser session not found: {session_id}")
        await context.close()
        self._forget(session_id)
        return {"session_id": session_id, "closed": True}

    async def close(self) -> None:
        self._closing = True
        if self._reaper is not None:
            self._reaper.cancel()
            await asyncio.gather(self._reaper, return_exceptions=True)
            self._reaper = None
        errors: list[Exception] = []
        for session_id in list(self._contexts):
            try:
                await self.close_session(session_id)
            except Exception as exc:
                errors.append(exc)
        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception as exc:
                errors.append(exc)
            else:
                self._browser = None
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception as exc:
                errors.append(exc)
            else:
                self._playwright = None
                self._browser = None
                for session_id in list(self._contexts):
                    self._forget(session_id)
        if errors:
            raise ExceptionGroup("Browser cleanup failed", errors)
        # Core controls admission; allow an explicit Core initialize after a
        # successful shutdown to lazily acquire a fresh Playwright lifecycle.
        self._closing = False

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
