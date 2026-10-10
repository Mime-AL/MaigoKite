"""BrowserTool - controlled browser operations backed by Playwright."""

from __future__ import annotations

import asyncio
from typing import Any

from agent.browser_runtime import BrowserRuntime, BrowserRuntimeUnavailable
from agent.tools.base import BaseTool, ExecutionContext, ToolResult


class BrowserTool(BaseTool):
    def __init__(self, runtime: BrowserRuntime) -> None:
        self.runtime = runtime

    @property
    def name(self) -> str:
        return "browser"

    @property
    def description(self) -> str:
        return (
            "Operate an isolated Chromium page. Open a public HTTP(S) URL, read a text snapshot, "
            "fill fields, click or press keys, save a screenshot inside the workspace, or close the session. "
            "Reuse the session_id returned by open for subsequent actions."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["open", "snapshot", "fill", "click", "press", "screenshot", "close"],
                },
                "session_id": {"type": "string", "maxLength": 128},
                "url": {"type": "string", "maxLength": 2048},
                "selector": {"type": "string", "maxLength": 1000},
                "text": {"type": "string", "maxLength": 10000},
                "key": {"type": "string", "maxLength": 100},
                "path": {"type": "string", "maxLength": 1000},
            },
            "required": ["action"],
            "additionalProperties": False,
        }

    async def execute(self, context: ExecutionContext, arguments: dict[str, Any]) -> ToolResult:
        action = str(arguments["action"])
        session_id = str(arguments.get("session_id", ""))
        try:
            if action == "open":
                result = await self.runtime.open(self._required(arguments, "url"))
            elif action == "snapshot":
                result = await self.runtime.snapshot(self._required(arguments, "session_id"))
            elif action == "fill":
                result = await self.runtime.fill(
                    session_id,
                    self._required(arguments, "selector"),
                    self._required(arguments, "text", allow_empty=True),
                )
            elif action == "click":
                result = await self.runtime.click(session_id, self._required(arguments, "selector"))
            elif action == "press":
                result = await self.runtime.press(
                    session_id,
                    self._required(arguments, "selector"),
                    self._required(arguments, "key"),
                )
            elif action == "screenshot":
                result = await self.runtime.screenshot(
                    session_id,
                    self._required(arguments, "path"),
                    workspace_root=context.metadata.get("workspace_root"),
                )
            elif action == "close":
                result = await self.runtime.close_session(self._required(arguments, "session_id"))
            else:
                raise ValueError(f"unsupported browser action: {action}")
        except asyncio.CancelledError:
            # Stop remote navigation/actions too, without closing other sessions.
            if session_id:
                try:
                    await self.runtime.close_session(session_id)
                except KeyError:
                    pass
            raise
        except BrowserRuntimeUnavailable as exc:
            return ToolResult.failure(
                {"action": action, "error": str(exc)},
                "Browser runtime is unavailable.",
                error_code="BROWSER_RUNTIME_UNAVAILABLE",
                user_hint="浏览器运行时未安装或无法启动，请检查 Playwright 与 Chromium 配置。",
            )
        except (KeyError, ValueError) as exc:
            return ToolResult.failure(
                {"action": action, "error": str(exc)},
                f"Browser action failed: {exc}",
                error_code="BROWSER_ACTION_INVALID",
            )
        except Exception as exc:
            return ToolResult.failure(
                {"action": action, "error": type(exc).__name__},
                f"Browser action {action} failed.",
                error_code="BROWSER_ACTION_FAILED",
            )
        raw = result.get("text") if isinstance(result.get("text"), str) else None
        return ToolResult(result, f"Browser {action} completed.", raw=raw)

    @staticmethod
    def _required(arguments: dict[str, Any], name: str, *, allow_empty: bool = False) -> str:
        value = arguments.get(name)
        if not isinstance(value, str) or (not allow_empty and not value.strip()):
            raise ValueError(f"{name} is required for this browser action")
        return value
