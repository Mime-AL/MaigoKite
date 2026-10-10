"""Agent Core composition root, tool loop, and durable approval workflow."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import uuid
from collections.abc import Awaitable
from pathlib import Path
from typing import Any, cast

from agent.browser_runtime import BrowserRuntime
from agent.config_manager import ConfigManager
from agent.context_manager import ContextManager
from agent.event_bus import EventBus
from agent.execution_engine import ExecutionEngine
from agent.models.chat_provider import ChatMessage, ChatStreamChunk, IChatProvider, ToolCall
from agent.models.runtime import ChatModelRuntime, ChatModelSettings
from agent.mcp import MCPClient
from agent.observability import Observability
from agent.repository import ConversationBusyError, MessageReplay, SQLiteRepository
from agent.process_registry import ProcessRegistry
from agent.runtime import LangGraphRuntime, ProductToolSpec, RuntimeRunRequest
from agent.security.injection_filter import InjectionFilter
from agent.security.whitelist import Whitelist
from agent.skill_registry import SkillRegistry
from agent.task_manager import TaskManager, TaskStatus
from agent.tools.base import ExecutionContext, ToolResult
from agent.tools.native import (
    BashTool,
    BrowserTool,
    FileEditTool,
    FileReadTool,
    FileWriteTool,
    GlobTool,
    GrepTool,
    SkillTool,
    SleepTool,
    TodoWriteTool,
    WebFetchTool,
    WebSearchTool,
)
from agent.tools.permission_mgr import PermissionManager, PermissionRequired
from agent.tools.native.bash import ExecCommandTool
from agent.tools.tool_registry import ToolRegistry


class AgentPaused(RuntimeError):
    def __init__(self, approval: dict[str, Any]) -> None:
        super().__init__("approval required")
        self.approval = approval


class AgentCancelled(RuntimeError):
    pass


class AgentCore:
    RESPONSE_MODES = {"fast", "balanced", "thorough"}
    MEMORY_CATEGORIES = {"preference", "fact", "constraint", "project", "other"}
    MEMORY_SECRET_PATTERNS = (
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", re.IGNORECASE),
        re.compile(r"\b(?:api[_ -]?key|access[_ -]?token|password|secret)\s*[:=]\s*\S+", re.IGNORECASE),
        re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    )

    def __init__(
        self,
        config: ConfigManager,
        event_bus: EventBus,
        observability: Observability,
        provider: IChatProvider | None = None,
        repository: SQLiteRepository | None = None,
    ) -> None:
        self.config = config
        self.event_bus = event_bus
        self.observability = observability
        self.provider = provider
        db_path = config.get(
            "storage.sqlite_path", config.get("memory.storage.sqlite_path", "~/.maigokite/data/agent.db")
        )
        self.repository = repository or SQLiteRepository(db_path)
        self.models = ChatModelRuntime(config, self.repository)
        self._task_manager = TaskManager()
        self._context_manager = ContextManager(int(config.get("context.max_tokens", 32000)))
        self._registry = ToolRegistry()
        workspace_root = Path(config.get("workspace.root", Path.cwd())).expanduser().resolve()
        self._skills = SkillRegistry()
        self._browser: BrowserRuntime | None = None
        if bool(config.get("browser.enabled", True)):
            executable_path = str(config.get("browser.executable_path", "")).strip()
            self._browser = BrowserRuntime(
                workspace_root,
                headless=bool(config.get("browser.headless", True)),
                executable_path=executable_path or None,
            )
        allowlist_config = config.get("permissions.allowlist", {})
        if not isinstance(allowlist_config, dict):
            raise ValueError("permissions.allowlist must be an object")

        def string_set(key: str) -> set[str]:
            values = allowlist_config.get(key, [])
            if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
                raise ValueError(f"permissions.allowlist.{key} must be a string array")
            return {value for value in values if value.strip()}

        allowed_paths = set()
        for value in string_set("paths"):
            candidate = Path(value).expanduser()
            if not candidate.is_absolute():
                candidate = workspace_root / candidate
            allowed_paths.add(str(candidate.resolve()))
        allowlist = Whitelist(
            tools=string_set("tools"),
            command_prefixes=string_set("command_prefixes"),
            allowed_paths=allowed_paths,
        )
        circuit_breaker = config.get("permissions.circuit_breaker", {})
        if not isinstance(circuit_breaker, dict):
            raise ValueError("permissions.circuit_breaker must be an object")
        blocked_patterns = circuit_breaker.get("blocked_patterns", [])
        if not isinstance(blocked_patterns, list) or not all(isinstance(value, str) for value in blocked_patterns):
            raise ValueError("permissions.circuit_breaker.blocked_patterns must be a string array")
        if circuit_breaker.get("enabled", True) is False:
            blocked_patterns = []
        self._policy = PermissionManager(
            config.get("permissions.default_mode", "workspace"),
            workspace_root,
            allowlist,
            blocked_patterns,
        )
        self._execution_engine = ExecutionEngine(self._registry, self._policy, self.repository)
        self._input_filter = InjectionFilter()
        self._initialized = False
        self._max_tool_iterations = int(config.get("tools.max_iterations", 8))
        self._mcp_clients: list[MCPClient] = []
        self._mcp_runtime: list[dict[str, Any]] = []
        self._tool_credentials: dict[tuple[str, str], str] = {}
        self._cancelled_tasks: set[str] = set()
        self._runtime_backend = str(config.get("agent.runtime", "legacy")).strip().lower()
        if self._runtime_backend not in {"legacy", "langgraph"}:
            raise ValueError("agent.runtime must be 'legacy' or 'langgraph'")
        self._langgraph_runtime: LangGraphRuntime | None = None
        self._langgraph_entry_tasks: set[asyncio.Task[Any]] = set()
        self.processes = ProcessRegistry()

    async def initialize(self) -> None:
        if self._initialized:
            return
        await self.repository.open()
        self.event_bus.set_sink(self.repository.append_task_event)
        registry = ToolRegistry()
        self._mcp_runtime = []
        try:
            for tool_type in (
                FileReadTool,
                FileWriteTool,
                FileEditTool,
                BashTool,
                ExecCommandTool,
                WebSearchTool,
                WebFetchTool,
                GlobTool,
                GrepTool,
                SleepTool,
            ):
                registry.register(tool_type())
            registry.register(TodoWriteTool(self.repository))
            skill_directories = self.config.get("skills.scan_directories", [])
            if not isinstance(skill_directories, list) or not all(isinstance(item, str) for item in skill_directories):
                raise ValueError("skills.scan_directories must be a string array")
            self._skills = SkillRegistry()
            for error in self._skills.load_directories(skill_directories, self._policy.workspace_root):
                await self.observability.log("warning", f"Skill was not loaded: {error}")
            registry.register(SkillTool(self._skills))
            if self._browser is not None:
                registry.register(BrowserTool(self._browser))
            await self._initialize_mcp_servers(registry)
        except BaseException:
            await self._stop_mcp_servers()
            self.event_bus.set_sink(None)
            await self.repository.close()
            raise
        self._registry = registry
        self._execution_engine.registry = registry
        try:
            self._configured_tool_selection()
            if self._runtime_backend == "langgraph":
                await self._initialize_langgraph_runtime()
        except BaseException:
            await self._stop_mcp_servers()
            self.event_bus.set_sink(None)
            await self.repository.close()
            raise
        self._initialized = True
        await self.reconcile_interrupted_tasks()
        await self.observability.log("info", "Agent Core initialized")

    async def reconcile_interrupted_tasks(self) -> list[dict[str, Any]]:
        """Persist a truthful terminal state for work without a safe checkpoint."""
        interrupted = await self.repository.recover_interrupted_tasks()
        interrupted.extend(await self.repository.interrupt_ephemeral_approvals({"browser"}))
        for task in interrupted:
            await self.event_bus.publish(
                "task.interrupted",
                {
                    "task_id": task["id"],
                    "conversation_id": task["conversation_id"],
                    "message": task.get("last_error") or "Agent Core stopped before a safe continuation checkpoint",
                },
            )
        return interrupted

    async def shutdown(self) -> None:
        # Stop admission and drain entry tasks before closing their shared clients.
        self._initialized = False
        current = asyncio.current_task()
        entries = [task for task in self._langgraph_entry_tasks if task is not current]
        if entries:
            for task in entries:
                task.cancel()
            await asyncio.gather(*entries, return_exceptions=True)
        if self._langgraph_runtime is not None:
            await self._langgraph_runtime.close()
            self._langgraph_runtime = None
        await self._stop_mcp_servers()
        if self._browser is not None:
            await self._browser.close()
        await self.models.close()
        await self.repository.close()
        self.event_bus.clear()
        self._registry = ToolRegistry()
        self._execution_engine.registry = self._registry
        self._tool_credentials.clear()
        self._mcp_runtime.clear()
        self._cancelled_tasks.clear()
        self._initialized = False

    async def _initialize_mcp_servers(self, registry: ToolRegistry) -> None:
        servers = self.config.get("mcp.servers", {})
        if servers in (None, {}):
            return
        if not isinstance(servers, dict):
            raise ValueError("mcp.servers must be an object")

        workspace_root = self._policy.workspace_root
        for namespace, server in servers.items():
            if not isinstance(namespace, str) or not isinstance(server, dict):
                raise ValueError("each MCP server must have a string namespace and object configuration")
            if server.get("enabled", True) is False:
                self._mcp_runtime.append(
                    {
                        "namespace": namespace,
                        "status": "disabled",
                        "transport": "stdio",
                        "tool_names": [],
                    }
                )
                continue
            command = server.get("command")
            args = server.get("args", [])
            env_allowlist = server.get("env_allowlist", [])
            if not isinstance(command, str) or not command:
                raise ValueError(f"MCP server {namespace!r} requires a command")
            if not isinstance(args, list) or not all(isinstance(item, str) for item in args):
                raise ValueError(f"MCP server {namespace!r} args must be a string array")
            if not isinstance(env_allowlist, list) or not all(isinstance(item, str) for item in env_allowlist):
                raise ValueError(f"MCP server {namespace!r} env_allowlist must be a string array")

            replacements = {"{workspace}": str(workspace_root)}
            resolved_args = [argument.replace("{workspace}", replacements["{workspace}"]) for argument in args]
            raw_cwd = str(server.get("cwd") or workspace_root).replace("{workspace}", replacements["{workspace}"])
            cwd = Path(raw_cwd).expanduser()
            if not cwd.is_absolute():
                cwd = workspace_root / cwd
            cwd = cwd.resolve()
            try:
                cwd.relative_to(workspace_root)
            except ValueError as exc:
                raise ValueError(f"MCP server {namespace!r} cwd is outside the workspace") from exc
            if not cwd.is_dir():
                raise ValueError(f"MCP server {namespace!r} cwd does not exist")

            client = MCPClient(
                command,
                resolved_args,
                env={name: os.environ[name] for name in env_allowlist if name in os.environ},
                cwd=cwd,
            )
            await client.start()
            self._mcp_clients.append(client)
            enabled_tools = server.get("enabled_tools")
            disabled_tools = server.get("disabled_tools", [])
            for key, values in (("enabled_tools", enabled_tools), ("disabled_tools", disabled_tools)):
                if values is not None and (
                    not isinstance(values, list) or not all(isinstance(item, str) for item in values)
                ):
                    raise ValueError(f"MCP server {namespace!r} {key} must be a string array")
            discovered = await registry.discover_mcp(
                client, namespace, enabled_tools=enabled_tools, disabled_tools=disabled_tools or [],
            )
            self._mcp_runtime.append(
                {
                    "namespace": namespace,
                    "status": "running",
                    "transport": "stdio",
                    "tool_names": [tool.name for tool in discovered],
                }
            )
            await self.observability.log("info", f"MCP server {namespace} registered {len(discovered)} tool(s)")

    async def _stop_mcp_servers(self) -> None:
        clients, self._mcp_clients = list(reversed(self._mcp_clients)), []
        for client in clients:
            try:
                await client.stop()
            except Exception as exc:
                await self.observability.log("warning", f"Failed to stop MCP server: {type(exc).__name__}")

    async def _initialize_langgraph_runtime(self) -> None:
        """Reuse product tools; LangChain owns all runtime invocation."""
        from agent.tools.native.ask_user_question import AskUserQuestionTool

        self._registry.register(AskUserQuestionTool())
        specs = [
            ProductToolSpec(tool, tool.to_langchain_tool())
            for tool in self._registry.list_tools() if tool.name != "bash"
        ]

        configured = str(self.config.get("agent.langgraph_checkpoint_path", "")).strip()
        if configured:
            checkpoint_path = configured
        else:
            db_value = str(
                self.config.get(
                    "storage.sqlite_path",
                    self.config.get(
                        "memory.storage.sqlite_path",
                        "~/.maigokite/data/agent.db",
                    ),
                )
            )
            if db_value == ":memory:":
                checkpoint_path = str(
                    self._policy.workspace_root / ".maigokite-langgraph-checkpoints.sqlite"
                )
            else:
                database_path = Path(db_value).expanduser()
                checkpoint_path = str(
                    database_path.with_name(
                        f"{database_path.stem}.langgraph{database_path.suffix or '.sqlite'}"
                    )
                )
        runtime = LangGraphRuntime(
            model_resolver=self._resolve_langgraph_model,
            workspace_root=self._policy.workspace_root,
            checkpoint_path=checkpoint_path,
            repository=self.repository,
            policy=self._policy,
            event_publisher=self.event_bus.publish,
            tools=specs,
            system_prompt=self._skills.catalog_prompt(),
            context_max_tokens=self._context_manager.max_tokens,
            max_model_calls=self._max_tool_iterations,
            execution_metadata=self._langgraph_execution_metadata,
        )
        await runtime.open()
        self._langgraph_runtime = runtime

    async def _langgraph_execution_metadata(self, request: RuntimeRunRequest) -> dict[str, Any]:
        return await self._execution_metadata(
            request.workspace_id, request.conversation_id, request.principal_id,
        )

    def _configured_tool_selection(self) -> tuple[set[str], set[str]]:
        """Defaults are visibility preferences, disabled_tools is a config ceiling."""
        defaults = self.config.get("tools.default_tools", list(ToolRegistry.DEFAULT_TOOLS))
        disabled = self.config.get("tools.disabled_tools", [])
        for key, values in (("default_tools", defaults), ("disabled_tools", disabled)):
            if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
                raise ValueError(f"tools.{key} must be a string array")
        defaults = ["exec_command" if name == "bash" else name for name in defaults]
        disabled = ["exec_command" if name == "bash" else name for name in disabled]
        available = {tool.name for tool in self._registry.list_tools()}
        known = available | set(ToolRegistry.DEFAULT_TOOLS) | {"sleep", "todo_write"}
        if self._runtime_backend == "langgraph":
            known.add("ask_user_question")
        if unknown := (set(defaults) | set(disabled)) - known:
            raise ValueError(f"unknown configured tools: {', '.join(sorted(unknown))}")
        # Connected MCP tools are selected at their server boundary first.
        defaults = set(defaults) | {name for name in available if "__" in name}
        if self._runtime_backend == "langgraph":
            defaults |= {"ask_user_question"}
        return defaults - {"bash"}, set(disabled) | {"bash"}

    async def get_tool_settings(self, workspace_id: str) -> dict[str, Any]:
        defaults, disabled = self._configured_tool_selection()
        overrides = await self.repository.get_workspace_setting(workspace_id, "tools.selection")
        overrides = overrides if isinstance(overrides, dict) else {}
        return {"tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "source": "mcp" if "__" in tool.name else "builtin",
                "enabled": tool.name not in disabled and overrides.get(tool.name, tool.name in defaults) is True,
                "configurable": tool.name not in disabled,
                "default_enabled": tool.name in defaults and tool.name not in disabled,
            }
            for tool in self._registry.list_tools() if tool.name != "bash"
        ]}

    async def update_tool_settings(self, workspace_id: str, enabled: dict[str, bool]) -> dict[str, Any]:
        catalog = {item["name"]: item for item in (await self.get_tool_settings(workspace_id))["tools"]}
        for name, value in enabled.items():
            if name not in catalog or not isinstance(value, bool):
                raise ValueError(f"invalid tool selection: {name}")
            if value and not catalog[name]["configurable"]:
                raise ValueError(f"tool disabled by startup configuration: {name}")
        stored = await self.repository.get_workspace_setting(workspace_id, "tools.selection")
        overrides = dict(stored) if isinstance(stored, dict) else {}
        overrides.update(enabled)
        await self.repository.save_workspace_setting(workspace_id, "tools.selection", overrides)
        return await self.get_tool_settings(workspace_id)

    async def _enabled_tool_names(self, workspace_id: str) -> list[str]:
        return [item["name"] for item in (await self.get_tool_settings(workspace_id))["tools"] if item["enabled"]]

    async def _resolve_langgraph_model(
        self, workspace_id: str, model_id: str
    ) -> tuple[str, Any]:
        if self.provider is not None:
            model = getattr(self.provider, "langchain_model", None)
            if model is None:
                raise RuntimeError(
                    "the injected provider does not expose a LangChain chat model"
                )
            return f"injected:{id(self.provider)}", model
        return await self.models.get_langchain_model(workspace_id, model_id)

    async def get_permission_settings(self, workspace_id: str) -> dict[str, Any]:
        stored = await self.repository.get_workspace_setting(workspace_id, "permissions.policy")
        if not isinstance(stored, dict):
            return {"default_mode": self._policy.mode}
        try:
            mode = self._policy.normalize_mode(str(stored.get("default_mode", self._policy.mode)))
        except ValueError:
            mode = self._policy.mode
        return {"default_mode": mode}

    async def update_permission_settings(
        self, workspace_id: str, default_mode: str
    ) -> dict[str, Any]:
        try:
            default_mode = self._policy.normalize_mode(default_mode)
        except ValueError:
            raise ValueError("invalid permission mode")
        value = {"default_mode": default_mode}
        await self.repository.save_workspace_setting(workspace_id, "permissions.policy", value)
        return value

    async def create_conversation(
        self,
        workspace_id: str = "personal",
        title: str = "",
        model_id: str = "",
        permission_mode: str | None = None,
        response_mode: str = "balanced",
        folder_id: str = "",
    ) -> dict[str, Any]:
        mode = permission_mode or (await self.get_permission_settings(workspace_id))["default_mode"]
        try:
            mode = self._policy.normalize_mode(mode)
        except ValueError:
            raise ValueError("invalid permission mode")
        if response_mode not in self.RESPONSE_MODES:
            raise ValueError("invalid response mode")
        if model_id:
            await self.models.get_profile(workspace_id, model_id)
        else:
            _, model_id = await self.models.list_settings(workspace_id)
        return await self.repository.create_conversation(workspace_id, title, model_id, mode, response_mode, folder_id)

    async def update_conversation_permission(
        self, workspace_id: str, conversation_id: str, permission_mode: str
    ) -> dict[str, Any]:
        try:
            permission_mode = self._policy.normalize_mode(permission_mode)
        except ValueError:
            raise ValueError("invalid permission mode")
        return await self.repository.update_conversation_permission(workspace_id, conversation_id, permission_mode)

    async def update_conversation_settings(
        self,
        workspace_id: str,
        conversation_id: str,
        *,
        model_id: str | None = None,
        response_mode: str | None = None,
        permission_mode: str | None = None,
        title: str | None = None,
        folder_id: str | None = None,
        archived: bool | None = None,
    ) -> dict[str, Any]:
        if folder_id is not None or archived is not None:
            self._require_inactive_conversation(conversation_id)
        if folder_id is not None:
            await self.get_workspace_folder(workspace_id, folder_id)
        if title is not None:
            title = title.strip()
            if not title or len(title) > 200:
                raise ValueError("对话名称须为 1–200 个字符。")
        if permission_mode is not None:
            try:
                permission_mode = self._policy.normalize_mode(permission_mode)
            except ValueError:
                raise ValueError("invalid permission mode")
        if response_mode is not None and response_mode not in self.RESPONSE_MODES:
            raise ValueError("invalid response mode")
        if model_id is not None and model_id:
            await self.models.get_profile(workspace_id, model_id)
        return await self.repository.update_conversation_settings(
            workspace_id,
            conversation_id,
            model_id=model_id,
            response_mode=response_mode,
            permission_mode=permission_mode,
            title=title,
            folder_id=folder_id,
            archived=archived,
        )

    async def list_conversations(self, workspace_id: str = "personal") -> list[dict[str, Any]]:
        return await self.repository.list_conversations(workspace_id)

    async def get_conversation(self, workspace_id: str, conversation_id: str) -> dict[str, Any]:
        return await self.repository.get_conversation(workspace_id, conversation_id)

    def _require_inactive_conversation(self, conversation_id: str) -> None:
        if self._langgraph_runtime is not None and self._langgraph_runtime.has_active_conversation(conversation_id):
            raise ConversationBusyError("此对话的任务尚未结束，请稍后再管理。")

    async def delete_conversation(self, workspace_id: str, conversation_id: str) -> None:
        self._require_inactive_conversation(conversation_id)
        task_ids = await self.repository.delete_conversation(workspace_id, conversation_id)
        if self._langgraph_runtime is not None:
            await self._langgraph_runtime.delete_threads(task_ids)

    async def get_workspace_folder(self, workspace_id: str, folder_id: str) -> dict[str, Any]:
        if not folder_id:
            return {"id": "", "name": "默认工作区", "root_path": str(self._policy.workspace_root)}
        item = await self.repository.get_workspace_folder(workspace_id, folder_id)
        root = Path(item["root_path"])
        if not root.is_dir() or str(root.resolve(strict=True)) != item["root_path"]:
            raise ValueError("工作区文件夹不存在或路径已变更，请重新选择文件夹。")
        return item

    async def list_workspace_folders(self, workspace_id: str) -> list[dict[str, Any]]:
        return [await self.get_workspace_folder(workspace_id, ""),
                *await self.repository.list_workspace_folders(workspace_id)]

    async def create_workspace_folder(self, workspace_id: str, root_path: str, name: str = "") -> dict[str, Any]:
        if not root_path.strip() or len(root_path) > 4096 or "\0" in root_path:
            raise ValueError("请选择有效的文件夹。")
        root = Path(root_path).expanduser()
        if not root.is_absolute():
            raise ValueError("工作区文件夹须使用绝对路径。")
        root = root.resolve(strict=True)
        if not root.is_dir():
            raise ValueError("工作区路径不是文件夹。")
        self._policy.for_workspace(root)  # Preserve the existing filesystem-root boundary.
        if root == self._policy.workspace_root:
            return await self.get_workspace_folder(workspace_id, "")
        name = name.strip() or root.name
        if len(name) > 120:
            raise ValueError("工作区名称不能超过 120 个字符。")
        return await self.repository.create_workspace_folder(workspace_id, name, str(root))

    async def list_messages(self, conversation_id: str, workspace_id: str = "personal") -> list[dict[str, Any]]:
        await self.repository.get_conversation(workspace_id, conversation_id)
        return await self.repository.list_messages(conversation_id)

    async def run(self, prompt: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self._initialized:
            raise RuntimeError("Agent Core is not initialized")
        metadata = dict(metadata or {})
        key = str(metadata.get("idempotency_key") or "")
        if key:
            if len(key) > 128 or not key.isascii() or any(ord(char) < 33 or ord(char) > 126 for char in key):
                raise ValueError("Idempotency-Key must contain 1 to 128 printable ASCII characters without spaces")
            conversation_id = str(metadata.get("conversation_id") or metadata.get("session_id") or "")
            if not conversation_id:
                raise ValueError("a conversation is required for an idempotent message")
            workspace_id = str(metadata.get("workspace_id", "personal"))
            await self.repository.get_conversation(workspace_id, conversation_id)
            identity = "\x00".join((workspace_id, conversation_id, str(metadata.get("principal_id", "local-user")), key))
            metadata["task_id"] = "task_" + hashlib.sha256(identity.encode()).hexdigest()
            body = json.dumps({"content": prompt, "attachments": metadata.get("attachments", [])},
                              sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            metadata["request_hash"] = hashlib.sha256(body.encode()).hexdigest()
        try:
            if key:
                await self.repository.check_message_replay(workspace_id, metadata["task_id"], metadata["request_hash"])
            return await self._run_chat(prompt, metadata)
        except MessageReplay as replay:
            return {"task_id": replay.task["id"], "conversation_id": replay.task["conversation_id"],
                    "status": replay.task["status"], "replayed": True}

    async def _run_chat(self, prompt: str, metadata: dict[str, Any]) -> dict[str, Any]:
        prompt = self._input_filter.sanitize_input(prompt)
        if self._runtime_backend == "langgraph":
            return await self._track_langgraph_entry(
                self._run_langgraph_chat(prompt, metadata)
            )
        workspace_id = str(metadata.get("workspace_id", "personal"))
        principal_id = str(metadata.get("principal_id", "local-user"))
        conversation_id = str(metadata.get("conversation_id") or metadata.get("session_id") or "")
        if not conversation_id:
            conversation_id = (await self.create_conversation(workspace_id, title=prompt[:30]))["id"]
        else:
            try:
                await self.repository.get_conversation(workspace_id, conversation_id)
            except KeyError:
                conversation_id = (await self.create_conversation(workspace_id, title=prompt[:30]))["id"]

        task_id = str(metadata.get("task_id") or f"task_{uuid.uuid4().hex}")
        await self.repository.start_chat_turn(task_id, workspace_id, conversation_id, prompt,
                                              str(metadata.get("request_hash") or ""))
        task = await self._task_manager.create_task(prompt[:60] or "message", prompt, task_id=task_id)
        await self._task_manager.update_status(task.id, TaskStatus.RUNNING)
        trace_id = str(metadata.get("trace_id") or f"trace_{uuid.uuid4().hex}")
        await self.event_bus.publish(
            "task.started", {"task_id": task.id, "trace_id": trace_id, "conversation_id": conversation_id}
        )
        try:
            execution_metadata = {
                **metadata,
                "workspace_id": workspace_id,
                "principal_id": principal_id,
                "conversation_id": conversation_id,
            }
            if prompt.startswith("/tool "):
                response = await self._run_tool_command(prompt, task.id, trace_id, execution_metadata)
            else:
                response = await self._run_agent(workspace_id, conversation_id, task.id, trace_id, execution_metadata)
            self._raise_if_cancelled(task.id)
            await self._finish_task(task.id, conversation_id, response)
            self._cancelled_tasks.discard(task.id)
            return {"task_id": task.id, "conversation_id": conversation_id, "response": response, "status": "succeeded"}
        except AgentPaused as paused:
            await self._task_manager.update_status(task.id, TaskStatus.WAITING_APPROVAL)
            return {
                "task_id": task.id,
                "conversation_id": conversation_id,
                "status": "waiting_approval",
                "approval": self._approval_payload(paused.approval),
            }
        except AgentCancelled:
            memory_task = await self._task_manager.get_task(task.id)
            if memory_task is not None:
                await self._task_manager.cancel_task(task.id)
            await self.repository.cancel_task(workspace_id, task.id)
            self._cancelled_tasks.discard(task.id)
            return {
                "task_id": task.id,
                "conversation_id": conversation_id,
                "status": "cancelled",
                "error_code": "TASK_CANCELLED",
            }
        except Exception as exc:
            await self._task_manager.update_status(task.id, TaskStatus.FAILED)
            await self.repository.update_task_status(task.id, "failed", str(exc))
            await self.event_bus.publish(
                "task.failed",
                {
                    "task_id": task.id,
                    "conversation_id": conversation_id,
                    "message": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            self._cancelled_tasks.discard(task.id)
            return {
                "task_id": task.id,
                "conversation_id": conversation_id,
                "error": str(exc),
                "error_code": "AGENT_ERROR",
                "retryable": False,
            }

    async def _run_langgraph_chat(
        self, prompt: str, metadata: dict[str, Any]
    ) -> dict[str, Any]:
        runtime = self._langgraph_runtime
        if runtime is None:
            raise RuntimeError("LangGraph runtime is not initialized")
        workspace_id = str(metadata.get("workspace_id", "personal"))
        principal_id = str(metadata.get("principal_id", "local-user"))
        conversation_id = str(
            metadata.get("conversation_id") or metadata.get("session_id") or ""
        )
        if not conversation_id:
            conversation_id = (
                await self.create_conversation(workspace_id, title=prompt[:30])
            )["id"]
        else:
            try:
                await self.repository.get_conversation(workspace_id, conversation_id)
            except KeyError:
                conversation_id = (
                    await self.create_conversation(workspace_id, title=prompt[:30])
                )["id"]
        conversation = await self.repository.get_conversation(
            workspace_id, conversation_id
        )
        await self.get_workspace_folder(workspace_id, str(conversation.get("folder_id") or ""))
        request = RuntimeRunRequest(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            principal_id=principal_id,
            permission_mode=str(conversation["permission_mode"]),
            trace_id=str(metadata.get("trace_id") or f"trace_{uuid.uuid4().hex}"),
            task_id=str(metadata.get("task_id") or ""),
            request_hash=str(metadata.get("request_hash") or ""),
        )
        handle = await runtime.start(prompt, request)
        try:
            await handle.collect()
            await handle.wait()
        except asyncio.CancelledError:
            current = asyncio.current_task()
            if current is not None and current.cancelling():
                await asyncio.shield(handle.cancel())
                raise
        return await self._langgraph_result(
            workspace_id, handle.request.task_id, conversation_id
        )

    async def _track_langgraph_entry(
        self, operation: Awaitable[dict[str, Any]]
    ) -> dict[str, Any]:
        current = asyncio.current_task()
        if current is not None:
            self._langgraph_entry_tasks.add(current)
        try:
            return await operation
        finally:
            if current is not None:
                self._langgraph_entry_tasks.discard(current)

    async def _langgraph_result(
        self, workspace_id: str, task_id: str, conversation_id: str
    ) -> dict[str, Any]:
        task = await self.repository.get_task(workspace_id, task_id)
        status = str(task["status"])
        if status == "waiting_approval":
            questions = [item for item in await self.repository.list_questions(workspace_id, conversation_id)
                         if str(item["task_id"]) == task_id]
            if questions:
                return {"task_id": task_id, "conversation_id": conversation_id,
                        "status": status, "questions": questions}
            approvals = await self.repository.list_approvals(
                workspace_id, conversation_id
            )
            approval = next(
                item for item in approvals if str(item["task_id"]) == task_id
            )
            return {
                "task_id": task_id,
                "conversation_id": conversation_id,
                "status": status,
                "approval": self._approval_payload(approval),
            }
        if status == "succeeded":
            messages = await self.repository.list_messages(conversation_id)
            response = next(
                (
                    str(item["content"])
                    for item in reversed(messages)
                    if str(item["role"]) == "assistant"
                ),
                "",
            )
            return {
                "task_id": task_id,
                "conversation_id": conversation_id,
                "response": response,
                "status": status,
            }
        if status == "cancelled":
            return {
                "task_id": task_id,
                "conversation_id": conversation_id,
                "status": status,
                "error_code": "TASK_CANCELLED",
            }
        return {
            "task_id": task_id,
            "conversation_id": conversation_id,
            "status": status,
            "error": str(task.get("last_error") or "Agent execution failed"),
            "error_code": "AGENT_ERROR",
            "retryable": False,
        }

    async def _finish_task(self, task_id: str, conversation_id: str, response: str) -> None:
        self._raise_if_cancelled(task_id)
        message = await self.repository.append_message(conversation_id, "assistant", response)
        task = await self._task_manager.get_task(task_id)
        if task is not None:
            await self._task_manager.complete_task(task_id, {"response": response})
        await self.repository.update_task_status(task_id, "succeeded")
        await self.event_bus.publish(
            "message.completed",
            {
                "task_id": task_id,
                "conversation_id": conversation_id,
                "message_id": message["id"],
                "content": response,
            },
        )
        await self.event_bus.publish("task.succeeded", {"task_id": task_id, "conversation_id": conversation_id})

    def _tool_schemas(self, enabled: list[str] | None = None) -> list[dict[str, Any]]:
        if enabled is None:
            defaults, disabled = self._configured_tool_selection()
            enabled = sorted(defaults - disabled)
        return [
            {
                "type": "function",
                "function": {"name": tool.name, "description": tool.description, "parameters": tool.parameters_schema},
            }
            for tool in self._registry.list_tools()
            if tool.name in enabled
        ]

    async def _conversation_history(self, conversation_id: str) -> list[ChatMessage]:
        history = await self.repository.list_messages(conversation_id)
        messages = [ChatMessage(item["role"], item["content"]) for item in history]
        if catalog := self._skills.catalog_prompt():
            messages.insert(0, ChatMessage("system", catalog))
        return messages

    async def _stream_model(
        self,
        provider: IChatProvider,
        history: list[ChatMessage],
        task_id: str,
        conversation_id: str,
        generation_options: dict[str, Any] | None = None,
        workspace_id: str = "personal",
    ) -> tuple[str, list[ToolCall]]:
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        fragments: dict[int, dict[str, str]] = {}
        tools = self._tool_schemas(await self._enabled_tool_names(workspace_id))
        prepared = self._context_manager.prepare(history, tools)
        usage: dict[str, int] = {}
        async for value in provider.stream(prepared, tools=tools, **(generation_options or {})):
            self._raise_if_cancelled(task_id)
            chunk = value if isinstance(value, ChatStreamChunk) else ChatStreamChunk(content=str(value))
            for key, count in chunk.usage.items():
                usage[key] = usage.get(key, 0) + count
            if chunk.content:
                content_parts.append(chunk.content)
            if chunk.reasoning:
                reasoning_parts.append(chunk.reasoning)
            for fragment in chunk.tool_call_chunks:
                current = fragments.setdefault(fragment.index, {"id": "", "name": "", "arguments": ""})
                if fragment.id:
                    current["id"] = fragment.id
                if fragment.name:
                    current["name"] += fragment.name
                current["arguments"] += fragment.arguments
        if usage:
            await self.event_bus.publish("model.usage", {
                "task_id": task_id, "conversation_id": conversation_id,
                "model": provider.model_name, "usage": usage,
            })
        calls: list[ToolCall] = []
        for index in sorted(fragments):
            item = fragments[index]
            try:
                arguments = json.loads(item["arguments"] or "{}")
            except json.JSONDecodeError as exc:
                raise ValueError(f"model returned invalid arguments for tool {item['name']}") from exc
            if not isinstance(arguments, dict) or not item["name"]:
                raise ValueError("model returned an invalid tool call")
            calls.append(ToolCall(item["id"] or f"call_{uuid.uuid4().hex}", item["name"], arguments))
        content = "".join(content_parts)
        embedded_reasoning, content = self._split_visible_reasoning(content)
        provider_reasoning = "".join(reasoning_parts).strip()
        process_parts = [provider_reasoning] if provider_reasoning else []
        if embedded_reasoning:
            process_parts.append(embedded_reasoning)
        if calls and content.strip():
            process_parts.append(content.strip())
        if process_parts:
            await self.event_bus.publish(
                "reasoning.completed",
                {
                    "activity_id": f"reasoning_{uuid.uuid4().hex}",
                    "task_id": task_id,
                    "conversation_id": conversation_id,
                    "summary": "\n\n".join(process_parts),
                },
            )
        if not calls and content:
            await self.event_bus.publish(
                "message.delta",
                {
                    "content": content,
                    "task_id": task_id,
                    "conversation_id": conversation_id,
                },
            )
        return content, calls

    def _raise_if_cancelled(self, task_id: str) -> None:
        if task_id in self._cancelled_tasks:
            raise AgentCancelled("task cancelled")

    @staticmethod
    def _split_visible_reasoning(content: str) -> tuple[str, str]:
        """Separate a leading, provider-visible <think> block from the final answer."""
        candidate = content.lstrip()
        if not candidate.lower().startswith("<think>"):
            return "", content
        end = candidate.lower().find("</think>", len("<think>"))
        if end < 0:
            return "", content
        reasoning = candidate[len("<think>") : end].strip()
        answer = candidate[end + len("</think>") :].lstrip()
        return reasoning, answer

    async def _run_agent(
        self,
        workspace_id: str,
        conversation_id: str,
        task_id: str,
        trace_id: str,
        metadata: dict[str, Any],
        history: list[ChatMessage] | None = None,
    ) -> str:
        conversation = await self.repository.get_conversation(workspace_id, conversation_id)
        response_mode = str(conversation.get("response_mode") or "balanced")
        generation_options: dict[str, Any] = {}
        if self.provider is not None:
            provider = self.provider
        else:
            profile = await self.models.get_profile(workspace_id, str(conversation.get("model_id") or ""))
            provider = await self.models.get_provider(workspace_id, profile.id)
            token_caps = {"fast": 2048, "balanced": 8192, "thorough": profile.max_tokens}
            generation_options["max_tokens"] = min(profile.max_tokens, token_caps[response_mode])
        working_history = history or await self._conversation_history(conversation_id)
        for _ in range(self._max_tool_iterations):
            assistant_content, calls = await self._stream_model(
                provider, working_history, task_id, conversation_id, generation_options, workspace_id
            )
            if not calls:
                return assistant_content
            tool_call_values = [
                {"id": call.id, "name": call.name, "args": call.arguments, "type": "tool_call"} for call in calls
            ]
            working_history.append(ChatMessage("assistant", assistant_content, {"tool_calls": tool_call_values}))
            await self._execute_tool_batch(
                calls,
                assistant_content,
                tool_call_values,
                working_history,
                workspace_id,
                conversation_id,
                task_id,
                trace_id,
                metadata,
            )
        raise RuntimeError(f"tool iteration limit ({self._max_tool_iterations}) reached")

    async def _execute_tool_batch(
        self,
        calls: list[ToolCall],
        assistant_content: str,
        tool_call_values: list[dict[str, Any]],
        working_history: list[ChatMessage],
        workspace_id: str,
        conversation_id: str,
        task_id: str,
        trace_id: str,
        metadata: dict[str, Any],
        *,
        start_index: int = 0,
        completed_results: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        completed = list(completed_results or [])
        for index in range(start_index, len(calls)):
            call = calls[index]
            continuation = {
                "tool_calls": tool_call_values,
                "call_index": index,
                "completed_results": completed,
            }
            result = await self._execute_model_tool_call(
                call,
                assistant_content,
                workspace_id,
                conversation_id,
                task_id,
                trace_id,
                metadata,
                continuation=continuation,
            )
            record = self._tool_result_record(call, result)
            completed.append(record)
            working_history.append(self._tool_result_message(record))
        return completed

    @staticmethod
    def _tool_result_record(call: ToolCall, result: ToolResult) -> dict[str, Any]:
        return {
            "tool_call_id": call.id,
            "summary": result.summary,
            "data": result.data,
        }

    @staticmethod
    def _tool_result_message(record: dict[str, Any]) -> ChatMessage:
        return ChatMessage(
            "tool",
            json.dumps(
                {"summary": record.get("summary", ""), "data": record.get("data", {})},
                ensure_ascii=False,
                default=str,
            ),
            {"tool_call_id": str(record.get("tool_call_id", ""))},
        )

    async def _execution_metadata(
        self,
        workspace_id: str,
        conversation_id: str,
        principal_id: str,
        *,
        approved: bool = False,
    ) -> dict[str, Any]:
        conversation = await self.repository.get_conversation(workspace_id, conversation_id)
        folder = await self.get_workspace_folder(workspace_id, str(conversation.get("folder_id") or ""))
        api_keys = {
            service: secret
            for (scope, service), secret in self._tool_credentials.items()
            if scope == workspace_id and secret
        }
        return {
            "workspace_id": workspace_id,
            "conversation_id": conversation_id,
            "principal_id": principal_id,
            "permission_mode": conversation["permission_mode"],
            "process_registry": self.processes,
            "approved": approved,
            "workspace_root": folder["root_path"],
            "api_keys": api_keys,
            "enabled_tools": await self._enabled_tool_names(workspace_id),
        }

    async def _execute_model_tool_call(
        self,
        call: ToolCall,
        assistant_content: str,
        workspace_id: str,
        conversation_id: str,
        task_id: str,
        trace_id: str,
        metadata: dict[str, Any],
        *,
        continuation: dict[str, Any] | None = None,
    ) -> ToolResult:
        await self.repository.create_tool_call(
            call.id,
            workspace_id,
            conversation_id,
            task_id,
            call.name,
            call.arguments,
            assistant_content,
            continuation,
        )
        await self.event_bus.publish(
            "tool.proposed",
            {
                "task_id": task_id,
                "conversation_id": conversation_id,
                "tool_call_id": call.id,
                "tool_name": call.name,
                "arguments": call.arguments,
            },
        )
        context = ExecutionContext(
            trace_id,
            task_id,
            call.id,
            metadata=await self._execution_metadata(
                workspace_id,
                conversation_id,
                str(metadata.get("principal_id", "local-user")),
            ),
        )
        try:
            policy = await self._execution_engine.authorize_tool(call.name, call.arguments, context)
        except PermissionRequired as exc:
            approval = await self.repository.create_approval(
                workspace_id,
                conversation_id,
                str(metadata.get("principal_id", "local-user")),
                task_id,
                call.id,
                exc.decision.arguments,
                exc.decision.risk.name,
            )
            await self.repository.record_audit(
                workspace_id,
                str(metadata.get("principal_id", "local-user")),
                "approval.created",
                approval["id"],
                "pending",
                {"tool_call_id": call.id, "tool_name": call.name, "risk": exc.decision.risk.name},
            )
            task = await self._task_manager.get_task(task_id)
            if task is not None:
                await self._task_manager.update_status(task_id, TaskStatus.WAITING_APPROVAL)
            await self.event_bus.publish(
                "task.waiting_approval",
                {
                    "task_id": task_id,
                    "conversation_id": conversation_id,
                    "tool_call_id": call.id,
                    "approval_id": approval["id"],
                },
            )
            await self.event_bus.publish("approval.requested", self._approval_payload(approval))
            raise AgentPaused(approval) from exc
        except PermissionError as exc:
            await self.repository.update_tool_call(call.id, "denied", summary=str(exc))
            await self.event_bus.publish(
                "tool.failed",
                {
                    "task_id": task_id,
                    "conversation_id": conversation_id,
                    "tool_call_id": call.id,
                    "tool_name": call.name,
                    "message": str(exc),
                    "denied": True,
                },
            )
            return ToolResult({"error": str(exc), "denied": True}, f"Tool denied: {exc}")
        except Exception as exc:
            await self.repository.update_tool_call(call.id, "failed", summary=str(exc))
            await self.event_bus.publish(
                "tool.failed",
                {
                    "task_id": task_id,
                    "conversation_id": conversation_id,
                    "tool_call_id": call.id,
                    "tool_name": call.name,
                    "message": str(exc),
                },
            )
            return ToolResult({"error": str(exc)}, f"Tool failed: {exc}")
        await self.repository.update_tool_call(
            call.id,
            "running",
            arguments=policy.arguments,
            risk_level=policy.risk.name,
        )
        await self.event_bus.publish(
            "tool.started",
            {
                "task_id": task_id,
                "conversation_id": conversation_id,
                "tool_call_id": call.id,
                "tool_name": call.name,
                "arguments": policy.arguments,
                "resource_scope": policy.resource_scope,
                "risk_level": policy.risk.name,
            },
        )
        try:
            result = cast(
                ToolResult,
                await self._execution_engine.execute_authorized(
                    call.name, policy, context
                ),
            )
        except Exception as exc:
            await self.repository.update_tool_call(call.id, "failed", summary=str(exc))
            await self.event_bus.publish(
                "tool.failed",
                {
                    "task_id": task_id,
                    "conversation_id": conversation_id,
                    "tool_call_id": call.id,
                    "tool_name": call.name,
                    "message": str(exc),
                },
            )
            return ToolResult({"error": str(exc)}, f"Tool failed: {exc}")
        self._raise_if_cancelled(task_id)
        await self._complete_tool_call(call, result, task_id, conversation_id)
        return result

    async def _complete_tool_call(self, call: ToolCall, result: ToolResult, task_id: str, conversation_id: str) -> None:
        if not result.success:
            await self.repository.update_tool_call(
                call.id,
                "failed",
                result={"data": result.data, "metadata": result.metadata},
                summary=result.summary,
            )
            await self.event_bus.publish(
                "tool.failed",
                {
                    "task_id": task_id,
                    "conversation_id": conversation_id,
                    "tool_call_id": call.id,
                    "tool_name": call.name,
                    "message": result.summary,
                    "code": result.error_code or "TOOL_FAILED",
                    "user_hint": result.user_hint,
                    "action": result.action,
                    "data": result.data,
                },
            )
            return
        await self.repository.update_tool_call(
            call.id,
            "succeeded",
            result={"data": result.data, "metadata": result.metadata},
            summary=result.summary,
        )
        await self.event_bus.publish(
            "tool.completed",
            {
                "task_id": task_id,
                "conversation_id": conversation_id,
                "tool_call_id": call.id,
                "tool_name": call.name,
                "summary": result.summary,
                "data": result.data,
            },
        )
        change = result.metadata.get("file_change")
        if isinstance(change, dict):
            await self.event_bus.publish("file.changed", {
                **change, "task_id": task_id, "conversation_id": conversation_id,
                "tool_call_id": call.id,
            })

    async def _run_tool_command(self, prompt: str, task_id: str, trace_id: str, metadata: dict[str, Any]) -> str:
        try:
            _, name, payload = prompt.split(" ", 2)
            arguments = json.loads(payload)
        except (ValueError, json.JSONDecodeError) as exc:
            raise ValueError("tool command format: /tool <name> <json-object>") from exc
        if not isinstance(arguments, dict):
            raise ValueError("tool arguments must be a JSON object")
        call = ToolCall(f"call_{uuid.uuid4().hex}", name, arguments)
        result = await self._execute_model_tool_call(
            call,
            "__direct_tool__",
            str(metadata["workspace_id"]),
            str(metadata["conversation_id"]),
            task_id,
            trace_id,
            metadata,
        )
        response = result.summary if result.raw in (None, "") else str(result.raw)
        await self.event_bus.publish(
            "message.delta",
            {
                "task_id": task_id,
                "conversation_id": metadata["conversation_id"],
                "content": response,
            },
        )
        return response

    @staticmethod
    def _approval_payload(approval: dict[str, Any]) -> dict[str, Any]:
        arguments = dict(approval.get("arguments") or {})
        scope = (
            arguments.get("path")
            or arguments.get("root_dir")
            or arguments.get("workdir")
            or arguments.get("url")
            or "current workspace"
        )
        return {
            "approval_id": approval["id"],
            "task_id": approval["task_id"],
            "conversation_id": approval["conversation_id"],
            "tool_call_id": approval["tool_call_id"],
            "tool_name": approval["tool_name"],
            "arguments": arguments,
            "resource_scope": str(scope),
            "risk_level": approval["risk_level"],
            "status": approval["status"],
            "version": int(approval["version"]),
            "expires_at": approval["expires_at"],
            "note": approval.get("note", ""),
            "decided_at": approval.get("decided_at") or "",
        }

    async def list_approvals(self, workspace_id: str, conversation_id: str | None = None) -> list[dict[str, Any]]:
        return [
            self._approval_payload(item) for item in await self.repository.list_approvals(workspace_id, conversation_id)
        ]

    async def decide_approval(
        self,
        workspace_id: str,
        approval_id: str,
        principal_id: str,
        decision: str,
        version: int,
        note: str = "",
    ) -> dict[str, Any]:
        if self._langgraph_runtime is not None:
            pending = await self.repository.get_approval(workspace_id, approval_id)
            task_id = str(pending["task_id"])
            if await self._langgraph_runtime.has_checkpoint(task_id):
                return await self._track_langgraph_entry(
                    self._resume_langgraph_approval(
                        workspace_id,
                        approval_id,
                        principal_id,
                        decision,
                        version,
                        task_id,
                        str(pending["conversation_id"]),
                        note,
                    )
                )
        approval = await self.repository.decide_approval(
            workspace_id, approval_id, principal_id, decision, version, note,
        )
        payload = self._approval_payload(approval)
        payload["decision"] = decision
        await self.event_bus.publish("approval.decided", payload)
        task_id = str(approval["task_id"])
        conversation_id = str(approval["conversation_id"])
        if decision == "deny":
            response = f"已拒绝执行 {approval['tool_name']}。"
            task = await self._task_manager.get_task(task_id)
            if task is not None:
                await self._task_manager.cancel_task(task_id)
            message = await self.repository.append_message(conversation_id, "assistant", response)
            await self.event_bus.publish(
                "message.delta", {"task_id": task_id, "conversation_id": conversation_id, "content": response}
            )
            await self.event_bus.publish(
                "message.completed",
                {
                    "task_id": task_id,
                    "conversation_id": conversation_id,
                    "message_id": message["id"],
                    "content": response,
                },
            )
            await self.event_bus.publish(
                "task.cancelled", {"task_id": task_id, "conversation_id": conversation_id, "message": "approval denied"}
            )
            return {"task_id": task_id, "conversation_id": conversation_id, "status": "denied", "response": response}

        task = await self._task_manager.get_task(task_id)
        if task is not None:
            await self._task_manager.update_status(task_id, TaskStatus.RUNNING)
        tool_row = await self.repository.get_tool_call(str(approval["tool_call_id"]))
        arguments = json.loads(tool_row["arguments_json"])
        call = ToolCall(str(tool_row["id"]), str(tool_row["tool_name"]), arguments)
        context = ExecutionContext(
            f"trace_{uuid.uuid4().hex}",
            task_id,
            call.id,
            metadata=await self._execution_metadata(workspace_id, conversation_id, principal_id, approved=True),
        )
        try:
            policy = await self._execution_engine.authorize_tool(call.name, call.arguments, context)
            await self.repository.update_tool_call(
                call.id,
                "running",
                arguments=policy.arguments,
                risk_level=policy.risk.name,
            )
            await self.event_bus.publish(
                "tool.started",
                {
                    "task_id": task_id,
                    "conversation_id": conversation_id,
                    "tool_call_id": call.id,
                    "tool_name": call.name,
                    "arguments": policy.arguments,
                    "resource_scope": policy.resource_scope,
                    "risk_level": policy.risk.name,
                },
            )
            result = cast(
                ToolResult,
                await self._execution_engine.execute_authorized(
                    call.name, policy, context
                ),
            )
            self._raise_if_cancelled(task_id)
        except AgentCancelled:
            if task is not None:
                await self._task_manager.cancel_task(task_id)
            await self.repository.cancel_task(workspace_id, task_id)
            self._cancelled_tasks.discard(task_id)
            return {
                "task_id": task_id,
                "conversation_id": conversation_id,
                "status": "cancelled",
            }
        except Exception as exc:
            await self.repository.update_tool_call(call.id, "failed", summary=str(exc))
            await self.repository.update_task_status(task_id, "failed")
            if task is not None:
                await self._task_manager.update_status(task_id, TaskStatus.FAILED)
            await self.event_bus.publish(
                "tool.failed",
                {
                    "task_id": task_id,
                    "conversation_id": conversation_id,
                    "tool_call_id": call.id,
                    "tool_name": call.name,
                    "message": str(exc),
                },
            )
            await self.event_bus.publish(
                "task.failed",
                {
                    "task_id": task_id,
                    "conversation_id": conversation_id,
                    "message": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            raise
        await self._complete_tool_call(call, result, task_id, conversation_id)
        if tool_row["assistant_content"] == "__direct_tool__":
            response = result.summary if result.raw in (None, "") else str(result.raw)
            await self.event_bus.publish(
                "message.delta", {"task_id": task_id, "conversation_id": conversation_id, "content": response}
            )
        else:
            history = await self._conversation_history(conversation_id)
            try:
                continuation = json.loads(str(tool_row.get("continuation_json") or "{}"))
            except (TypeError, json.JSONDecodeError):
                continuation = {}
            tool_call_values = continuation.get("tool_calls")
            if not isinstance(tool_call_values, list) or not tool_call_values:
                tool_call_values = [{"id": call.id, "name": call.name, "args": call.arguments, "type": "tool_call"}]
            history.append(
                ChatMessage(
                    "assistant",
                    str(tool_row["assistant_content"]),
                    {"tool_calls": tool_call_values},
                )
            )
            completed_results = continuation.get("completed_results")
            if not isinstance(completed_results, list):
                completed_results = []
            for completed in completed_results:
                if isinstance(completed, dict):
                    history.append(self._tool_result_message(completed))
            current_result = self._tool_result_record(call, result)
            completed_results.append(current_result)
            history.append(self._tool_result_message(current_result))
            metadata = {"workspace_id": workspace_id, "conversation_id": conversation_id, "principal_id": principal_id}
            try:
                calls = [
                    ToolCall(str(item["id"]), str(item["name"]), dict(item.get("args") or {}))
                    for item in tool_call_values
                    if isinstance(item, dict)
                ]
                call_index = int(continuation.get("call_index", 0))
                if call_index + 1 < len(calls):
                    await self._execute_tool_batch(
                        calls,
                        str(tool_row["assistant_content"]),
                        tool_call_values,
                        history,
                        workspace_id,
                        conversation_id,
                        task_id,
                        f"trace_{uuid.uuid4().hex}",
                        metadata,
                        start_index=call_index + 1,
                        completed_results=completed_results,
                    )
                response = await self._run_agent(
                    workspace_id,
                    conversation_id,
                    task_id,
                    f"trace_{uuid.uuid4().hex}",
                    metadata,
                    history,
                )
            except AgentPaused as paused:
                return {
                    "task_id": task_id,
                    "conversation_id": conversation_id,
                    "status": "waiting_approval",
                    "approval": self._approval_payload(paused.approval),
                }
        await self._finish_task(task_id, conversation_id, response)
        return {"task_id": task_id, "conversation_id": conversation_id, "status": "succeeded", "response": response}

    async def _resume_langgraph_approval(
        self,
        workspace_id: str,
        approval_id: str,
        principal_id: str,
        decision: str,
        version: int,
        task_id: str,
        conversation_id: str,
        note: str = "",
    ) -> dict[str, Any]:
        runtime = self._langgraph_runtime
        if runtime is None:
            raise RuntimeError("LangGraph runtime is not initialized")
        handle = await runtime.resume_approval(
            workspace_id,
            approval_id,
            principal_id,
            decision,
            version,
            note,
        )
        try:
            await handle.collect()
            await handle.wait()
        except asyncio.CancelledError:
            current = asyncio.current_task()
            if current is not None and current.cancelling():
                await asyncio.shield(handle.cancel())
                raise
        return await self._langgraph_result(
            workspace_id, task_id, conversation_id
        )

    async def interrupt(self) -> None:
        for task in await self._task_manager.list_tasks(TaskStatus.RUNNING):
            await self._execution_engine.cancel(task.id)
            await self._task_manager.cancel_task(task.id)
            await self.repository.update_task_status(task.id, "cancelled")

    async def get_task(self, workspace_id: str, task_id: str) -> dict[str, Any]:
        return await self.repository.get_task(workspace_id, task_id)

    async def answer_question(self, workspace_id: str, question_id: str, principal_id: str,
                              answer: str, version: int) -> dict[str, Any]:
        return await self._track_langgraph_entry(
            self._answer_question(workspace_id, question_id, principal_id, answer, version),
        )

    async def _answer_question(self, workspace_id: str, question_id: str, principal_id: str,
                               answer: str, version: int) -> dict[str, Any]:
        runtime = self._langgraph_runtime
        if runtime is None:
            raise NotImplementedError("structured questions require the LangGraph runtime")
        handle = await runtime.answer_question(workspace_id, question_id, principal_id, answer, version)
        try:
            await handle.collect()
            await handle.wait()
        except asyncio.CancelledError:
            current = asyncio.current_task()
            if current is not None and current.cancelling():
                await asyncio.shield(handle.cancel())
                raise
        return await self._langgraph_result(workspace_id, handle.request.task_id, handle.request.conversation_id)

    async def list_jobs(self, workspace_id: str, conversation_id: str = "") -> list[dict[str, Any]]:
        jobs = []
        for call in await self.repository.list_command_calls(workspace_id, conversation_id):
            result = json.loads(call["result_json"] or "{}")
            data = result.get("data", result)
            data = data if isinstance(data, dict) else {}
            status = str(call["status"])
            active = self.processes.snapshot(workspace_id, str(call["id"]))
            if active is None and "return_code" not in data:
                # A proposal (or sandbox setup failure) is not a spawned job.
                continue
            if not active and status == "running" and call["task_status"] in {"interrupted", "cancelled", "failed"}:
                status = str(call["task_status"])
            jobs.append({
                "id": str(call["id"]), "task_id": str(call["task_id"]),
                "conversation_id": str(call["conversation_id"]), "command": str(json.loads(call["arguments_json"]).get("command", "")),
                "status": status, "live": bool(active and active["live"]),
                "live_logs_available": bool(active and active["live_logs_available"]),
                "log_tail": str(active["log_tail"]) if active else "\n".join(
                    str(data.get(key) or "")[-4000:] for key in ("stdout", "stderr")),
            })
        return jobs

    async def stop_job(self, workspace_id: str, job_id: str, principal_id: str = "local-user") -> None:
        call = await self.repository.get_tool_call(job_id)
        if call["workspace_id"] != workspace_id or call["tool_name"] not in {"exec_command", "bash"}:
            raise KeyError(job_id)
        await self.processes.stop(workspace_id, job_id)
        await self.repository.record_audit(workspace_id, principal_id, "process.stopped", job_id, "success", {})

    async def list_tasks(self, workspace_id: str, conversation_id: str = "", limit: int = 100) -> list[dict[str, Any]]:
        return await self.repository.list_tasks(workspace_id, conversation_id, limit)

    async def list_task_events(
        self,
        workspace_id: str,
        conversation_id: str,
        after_sequence: int = 0,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        await self.repository.get_conversation(workspace_id, conversation_id)
        return await self.repository.list_task_events(workspace_id, conversation_id, after_sequence, limit)

    async def cancel_task(self, workspace_id: str, task_id: str) -> dict[str, Any]:
        task = await self.repository.get_task(workspace_id, task_id)
        if task["status"] in {"succeeded", "failed", "cancelled", "timed_out", "expired"}:
            return task
        if (
            self._langgraph_runtime is not None
            and await self._langgraph_runtime.owns_task(task_id)
        ):
            return await self._langgraph_runtime.cancel(workspace_id, task_id)
        self._cancelled_tasks.add(task_id)
        await self._execution_engine.cancel(task_id)
        memory_task = await self._task_manager.get_task(task_id)
        if memory_task is not None:
            await self._task_manager.cancel_task(task_id)
        cancelled = await self.repository.cancel_task(workspace_id, task_id)
        await self.event_bus.publish(
            "task.cancelled",
            {
                "task_id": task_id,
                "conversation_id": cancelled["conversation_id"],
                "message": "Cancelled by user",
            },
        )
        return cancelled

    @property
    def task_manager(self) -> TaskManager:
        return self._task_manager

    @property
    def execution_engine(self) -> ExecutionEngine:
        return self._execution_engine

    @property
    def tool_registry(self) -> ToolRegistry:
        return self._registry

    @property
    def context_manager(self) -> ContextManager:
        return self._context_manager

    async def get_chat_model_settings(self, workspace_id: str) -> ChatModelSettings:
        return await self.models.get_settings(workspace_id)

    async def update_chat_model_settings(self, workspace_id: str, settings: ChatModelSettings) -> ChatModelSettings:
        return await self.models.update_settings(workspace_id, settings)

    async def list_chat_models(self, workspace_id: str) -> tuple[list[ChatModelSettings], str]:
        return await self.models.list_settings(workspace_id)

    async def upsert_chat_model(self, workspace_id: str, settings: ChatModelSettings) -> ChatModelSettings:
        return await self.models.upsert_settings(workspace_id, settings)

    async def delete_chat_model(self, workspace_id: str, model_id: str) -> None:
        await self.models.delete_settings(workspace_id, model_id)

    async def set_default_chat_model(self, workspace_id: str, model_id: str) -> tuple[list[ChatModelSettings], str]:
        return await self.models.set_default(workspace_id, model_id)

    async def set_chat_model_credential(
        self, workspace_id: str, provider: str, api_key: str, model_id: str = ""
    ) -> None:
        await self.models.set_credential(workspace_id, provider, api_key, model_id)

    async def set_tool_credential(self, workspace_id: str, service: str, api_key: str) -> None:
        if service not in {"tavily", "google"}:
            raise ValueError("unsupported tool credential service")
        key = (workspace_id, service)
        if api_key:
            self._tool_credentials[key] = api_key
        else:
            self._tool_credentials.pop(key, None)

    async def validate_chat_model(self, settings: ChatModelSettings, api_key: str = "") -> str:
        return await self.models.validate_connection(settings, api_key)

    async def get_user_preferences(self, workspace_id: str, user_id: str) -> dict[str, str]:
        value = await self.repository.get_preference(workspace_id, user_id, "interface.assistant_name")
        name = str(value).strip() if value is not None else ""
        return {"assistant_name": name or "助手"}

    async def update_user_preferences(self, workspace_id: str, user_id: str, assistant_name: str) -> dict[str, str]:
        name = " ".join(assistant_name.split())
        if not name:
            raise ValueError("assistant name is required")
        if len(name) > 32:
            raise ValueError("assistant name must not exceed 32 characters")
        if any(ord(char) < 32 or ord(char) == 127 for char in name):
            raise ValueError("assistant name contains control characters")
        await self.repository.save_preference(workspace_id, user_id, "interface.assistant_name", name)
        return {"assistant_name": name}

    async def list_memories(
        self, workspace_id: str, user_id: str, query: str = "", limit: int = 100
    ) -> list[dict[str, Any]]:
        if len(query) > 200:
            raise ValueError("memory search query must not exceed 200 characters")
        return await self.repository.list_user_memories(workspace_id, user_id, query, limit)

    async def upsert_memory(
        self,
        workspace_id: str,
        user_id: str,
        *,
        memory_id: str = "",
        category: str,
        content: str,
        confidence: float = 1.0,
    ) -> dict[str, Any]:
        category = category.strip().lower()
        normalized_content = " ".join(content.split())
        if category not in self.MEMORY_CATEGORIES:
            raise ValueError("invalid memory category")
        if not normalized_content:
            raise ValueError("memory content is required")
        if len(normalized_content) > 4000:
            raise ValueError("memory content must not exceed 4000 characters")
        if any(pattern.search(normalized_content) for pattern in self.MEMORY_SECRET_PATTERNS):
            raise ValueError("memory content must not contain credentials or private keys")
        if not 0 <= confidence <= 1:
            raise ValueError("memory confidence must be between 0 and 1")
        item = await self.repository.upsert_user_memory(
            workspace_id,
            user_id,
            memory_id=memory_id,
            category=category,
            content=normalized_content,
            source_type="user",
            source_id=user_id,
            confidence=confidence,
        )
        return item

    async def delete_memory(self, workspace_id: str, user_id: str, memory_id: str) -> None:
        await self.repository.delete_user_memory(workspace_id, user_id, memory_id)

    async def get_workspace_data_summary(self, workspace_id: str) -> dict[str, Any]:
        return await self.repository.get_workspace_data_summary(workspace_id)

    async def list_mcp_servers(self) -> list[dict[str, Any]]:
        return [{**server, "tool_names": list(server.get("tool_names", []))} for server in self._mcp_runtime]

    async def list_skills(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in self._skills.list_skills()]
