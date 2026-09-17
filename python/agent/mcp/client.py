"""Minimal line-delimited JSON-RPC client for explicitly configured stdio MCP servers."""

from __future__ import annotations

import asyncio
import json
import os
import signal
from pathlib import Path
from typing import Any


class MCPError(RuntimeError):
    pass


class MCPClient:
    def __init__(
        self,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        cwd: str | Path | None = None,
        request_timeout: float = 30,
    ) -> None:
        if not command or any(character in command for character in "\x00\r\n"):
            raise ValueError("MCP command must be a single executable")
        if any("\x00" in argument for argument in (args or [])):
            raise ValueError("MCP arguments must not contain NUL bytes")
        if request_timeout <= 0:
            raise ValueError("MCP request timeout must be positive")
        if any("\x00" in key or "\x00" in value for key, value in (env or {}).items()):
            raise ValueError("MCP environment must not contain NUL bytes")
        self.command = command
        self.args = list(args or [])
        self.env = dict(env or {})
        self.cwd = str(Path(cwd).expanduser().resolve()) if cwd is not None else None
        self.request_timeout = request_timeout
        self._process: asyncio.subprocess.Process | None = None
        self._next_id = 0
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self._process and self._process.returncode is None:
            return
        minimal = {
            key: value
            for key, value in os.environ.items()
            if key in {"PATH", "LANG", "LC_ALL", "SYSTEMROOT", "WINDIR"}
        }
        minimal.update(self.env)
        self._process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            env=minimal,
            cwd=self.cwd,
            start_new_session=os.name == "posix",
            limit=1_048_576,
        )
        try:
            result = await self.request(
                "initialize",
                {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "NanamiGopher", "version": "0.1.0"},
                },
            )
            if not isinstance(result, dict) or not result.get("protocolVersion"):
                raise MCPError("MCP server returned an invalid initialize response")
            await self.notify("notifications/initialized", {})
        except BaseException:
            await self.stop()
            raise

    async def stop(self) -> None:
        process = self._process
        if process is None:
            return
        self._process = None
        if process.returncode is None:
            if os.name == "posix":
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            else:
                process.terminate()
            deadline = asyncio.get_running_loop().time() + 5
            while process.returncode is None and asyncio.get_running_loop().time() < deadline:
                await asyncio.sleep(0.02)
            if process.returncode is None:
                if os.name == "posix":
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    process.kill()
                while process.returncode is None:
                    await asyncio.sleep(0.01)

    async def notify(self, method: str, params: dict[str, Any]) -> None:
        await self._write({"jsonrpc": "2.0", "method": method, "params": params})

    async def request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        async with self._lock:
            self._next_id += 1
            request_id = self._next_id
            await self._write(
                {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}
            )
            process = self._process
            if process is None or process.stdout is None:
                raise MCPError("MCP client is not started")
            while True:
                try:
                    line = await asyncio.wait_for(
                        process.stdout.readline(), self.request_timeout
                    )
                except asyncio.TimeoutError as exc:
                    raise MCPError(f"MCP request timed out: {method}") from exc
                if not line:
                    raise MCPError("MCP server closed stdout")
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if message.get("id") != request_id:
                    continue
                if "error" in message:
                    raise MCPError(str(message["error"]))
                return message.get("result")

    async def list_tools(self) -> list[dict[str, Any]]:
        result = await self.request("tools/list") or {}
        tools = result.get("tools", []) if isinstance(result, dict) else []
        if not isinstance(tools, list):
            raise MCPError("MCP tools/list returned an invalid tool list")
        return [item for item in tools if isinstance(item, dict)]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        return await self.request("tools/call", {"name": name, "arguments": arguments})

    async def _write(self, message: dict[str, Any]) -> None:
        if not self._process or not self._process.stdin:
            raise MCPError("MCP client is not started")
        self._process.stdin.write(
            json.dumps(message, separators=(",", ":")).encode() + b"\n"
        )
        await self._process.stdin.drain()
