"""Agent Core composition root, tool loop, and durable approval workflow."""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from agent.config_manager import ConfigManager
from agent.context_manager import ContextManager
from agent.event_bus import EventBus
from agent.execution_engine import ExecutionEngine
from agent.models.chat_provider import ChatMessage, ChatStreamChunk, IChatProvider, ToolCall
from agent.models.runtime import ChatModelRuntime, ChatModelSettings
from agent.mcp import MCPClient
from agent.observability import Observability
from agent.repository import SQLiteRepository
from agent.security.injection_filter import InjectionFilter
from agent.security.whitelist import Whitelist
from agent.task_manager import TaskManager, TaskStatus
from agent.tools.base import ExecutionContext, ToolResult
from agent.tools.native import (
    BashTool, FileEditTool, FileReadTool, FileWriteTool, GlobTool, GrepTool,
    SleepTool, TodoWriteTool, WebFetchTool, WebSearchTool,
)
from agent.tools.permission_mgr import PermissionManager, PermissionRequired
from agent.tools.tool_registry import ToolRegistry


class AgentPaused(RuntimeError):
    def __init__(self, approval: dict[str, Any]) -> None:
        super().__init__("approval required")
        self.approval = approval


class AgentCore:
    RESPONSE_MODES = {"fast", "balanced", "thorough"}
    def __init__(
        self, config: ConfigManager, event_bus: EventBus, observability: Observability,
        provider: IChatProvider | None = None, repository: SQLiteRepository | None = None,
    ) -> None:
        self.config = config
        self.event_bus = event_bus
        self.observability = observability
        self.provider = provider
        db_path = config.get("storage.sqlite_path", config.get("memory.storage.sqlite_path", "~/.nanamigopher/data/agent.db"))
        self.repository = repository or SQLiteRepository(db_path)
        self.models = ChatModelRuntime(config, self.repository)
        self._task_manager = TaskManager()
        self._context_manager = ContextManager(int(config.get("context.max_tokens", 32000)))
        self._registry = ToolRegistry()
        workspace_root = Path(config.get("workspace.root", Path.cwd())).expanduser().resolve()
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
        if not isinstance(blocked_patterns, list) or not all(
            isinstance(value, str) for value in blocked_patterns
        ):
            raise ValueError("permissions.circuit_breaker.blocked_patterns must be a string array")
        if circuit_breaker.get("enabled", True) is False:
            blocked_patterns = []
        self._policy = PermissionManager(
            config.get("permissions.default_mode", "workspace"), workspace_root, allowlist,
            blocked_patterns,
        )
        self._execution_engine = ExecutionEngine(self._registry, self._policy, self.repository)
        self._input_filter = InjectionFilter()
        self._initialized = False
        self._max_tool_iterations = int(config.get("tools.max_iterations", 8))
        self._mcp_clients: list[MCPClient] = []
        self._tool_credentials: dict[tuple[str, str], str] = {}

    async def initialize(self) -> None:
        if self._initialized:
            return
        await self.repository.open()
        registry = ToolRegistry()
        try:
            for tool_type in (FileReadTool, FileWriteTool, FileEditTool, BashTool, WebSearchTool, WebFetchTool, GlobTool, GrepTool, SleepTool):
                registry.register(tool_type())
            registry.register(TodoWriteTool(self.repository))
            await self._initialize_mcp_servers(registry)
        except BaseException:
            await self._stop_mcp_servers()
            await self.repository.close()
            raise
        self._registry = registry
        self._execution_engine.registry = registry
        self._initialized = True
        await self.observability.log("info", "Agent Core initialized")

    async def shutdown(self) -> None:
        await self._stop_mcp_servers()
        await self.models.close()
        await self.repository.close()
        self.event_bus.clear()
        self._registry = ToolRegistry()
        self._execution_engine.registry = self._registry
        self._tool_credentials.clear()
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
            resolved_args = [
                argument.replace("{workspace}", replacements["{workspace}"])
                for argument in args
            ]
            raw_cwd = str(server.get("cwd") or workspace_root).replace(
                "{workspace}", replacements["{workspace}"]
            )
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
            discovered = await registry.discover_mcp(client, namespace)
            await self.observability.log(
                "info", f"MCP server {namespace} registered {len(discovered)} tool(s)"
            )

    async def _stop_mcp_servers(self) -> None:
        clients, self._mcp_clients = list(reversed(self._mcp_clients)), []
        for client in clients:
            try:
                await client.stop()
            except Exception as exc:
                await self.observability.log("warning", f"Failed to stop MCP server: {type(exc).__name__}")

    async def get_permission_settings(self, workspace_id: str) -> dict[str, Any]:
        stored = await self.repository.get_workspace_setting(workspace_id, "permissions.policy")
        base_levels = {name: int(level) for name, level in self._policy.BASE_RISK.items()}
        if not isinstance(stored, dict):
            return {"default_mode": self._policy.mode, "tool_levels": base_levels}
        try:
            mode = self._policy.normalize_mode(str(stored.get("default_mode", self._policy.mode)))
        except ValueError:
            mode = self._policy.mode
        return {"default_mode": mode, "tool_levels": base_levels}

    async def update_permission_settings(
        self, workspace_id: str, default_mode: str, tool_levels: dict[str, int]
    ) -> dict[str, Any]:
        try:
            default_mode = self._policy.normalize_mode(default_mode)
        except ValueError:
            raise ValueError("invalid permission mode")
        normalized = {name: int(base) for name, base in self._policy.BASE_RISK.items()}
        value = {"default_mode": default_mode, "tool_levels": normalized}
        await self.repository.save_workspace_setting(workspace_id, "permissions.policy", value)
        return value

    async def create_conversation(
        self, workspace_id: str = "personal", title: str = "", model_id: str = "",
        permission_mode: str | None = None, response_mode: str = "balanced",
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
        return await self.repository.create_conversation(
            workspace_id, title, model_id, mode, response_mode
        )

    async def update_conversation_permission(
        self, workspace_id: str, conversation_id: str, permission_mode: str
    ) -> dict[str, Any]:
        try:
            permission_mode = self._policy.normalize_mode(permission_mode)
        except ValueError:
            raise ValueError("invalid permission mode")
        return await self.repository.update_conversation_permission(workspace_id, conversation_id, permission_mode)

    async def update_conversation_settings(
        self, workspace_id: str, conversation_id: str, *, model_id: str | None = None,
        response_mode: str | None = None, permission_mode: str | None = None,
    ) -> dict[str, Any]:
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
            workspace_id, conversation_id, model_id=model_id,
            response_mode=response_mode, permission_mode=permission_mode,
        )

    async def list_conversations(self, workspace_id: str = "personal") -> list[dict[str, Any]]:
        return await self.repository.list_conversations(workspace_id)

    async def get_conversation(self, workspace_id: str, conversation_id: str) -> dict[str, Any]:
        return await self.repository.get_conversation(workspace_id, conversation_id)

    async def delete_conversation(self, workspace_id: str, conversation_id: str) -> None:
        await self.repository.delete_conversation(workspace_id, conversation_id)

    async def list_messages(self, conversation_id: str, workspace_id: str = "personal") -> list[dict[str, Any]]:
        await self.repository.get_conversation(workspace_id, conversation_id)
        return await self.repository.list_messages(conversation_id)

    async def run(self, prompt: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self._initialized:
            raise RuntimeError("Agent Core is not initialized")
        prompt = self._input_filter.sanitize_input(prompt)
        metadata = metadata or {}
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

        task = await self._task_manager.create_task(prompt[:60] or "message", prompt)
        await self._task_manager.update_status(task.id, TaskStatus.RUNNING)
        await self.repository.create_task_state(task.id, workspace_id, conversation_id, task.title, "running")
        trace_id = str(metadata.get("trace_id") or f"trace_{uuid.uuid4().hex}")
        await self.repository.append_message(conversation_id, "user", prompt)
        await self.event_bus.publish("task.started", {"task_id": task.id, "trace_id": trace_id, "conversation_id": conversation_id})
        try:
            execution_metadata = {
                **metadata, "workspace_id": workspace_id, "principal_id": principal_id,
                "conversation_id": conversation_id,
            }
            if prompt.startswith("/tool "):
                response = await self._run_tool_command(prompt, task.id, trace_id, execution_metadata)
            else:
                response = await self._run_agent(workspace_id, conversation_id, task.id, trace_id, execution_metadata)
            await self._finish_task(task.id, conversation_id, response)
            return {"task_id": task.id, "conversation_id": conversation_id, "response": response, "status": "succeeded"}
        except AgentPaused as paused:
            await self._task_manager.update_status(task.id, TaskStatus.WAITING_APPROVAL)
            return {
                "task_id": task.id, "conversation_id": conversation_id,
                "status": "waiting_approval", "approval": self._approval_payload(paused.approval),
            }
        except Exception as exc:
            await self._task_manager.update_status(task.id, TaskStatus.FAILED)
            await self.repository.update_task_status(task.id, "failed")
            await self.event_bus.publish("task.failed", {
                "task_id": task.id, "conversation_id": conversation_id,
                "message": str(exc), "error_type": type(exc).__name__,
            })
            return {
                "task_id": task.id, "conversation_id": conversation_id,
                "error": str(exc), "error_code": "AGENT_ERROR", "retryable": False,
            }

    async def _finish_task(self, task_id: str, conversation_id: str, response: str) -> None:
        await self.repository.append_message(conversation_id, "assistant", response)
        task = await self._task_manager.get_task(task_id)
        if task is not None:
            await self._task_manager.complete_task(task_id, {"response": response})
        await self.repository.update_task_status(task_id, "succeeded")
        await self.event_bus.publish("message.completed", {"task_id": task_id, "conversation_id": conversation_id, "content": response})
        await self.event_bus.publish("task.succeeded", {"task_id": task_id, "conversation_id": conversation_id})

    def _tool_schemas(self) -> list[dict[str, Any]]:
        return [{
            "type": "function",
            "function": {"name": tool.name, "description": tool.description, "parameters": tool.parameters_schema},
        } for tool in self._registry.list_tools()]

    async def _conversation_history(self, conversation_id: str) -> list[ChatMessage]:
        history = await self.repository.list_messages(conversation_id)
        self._context_manager.clear()
        for item in history:
            self._context_manager.add_message(item["role"], item["content"])
        return [ChatMessage(item.role, item.content) for item in self._context_manager.get_messages()]

    async def _stream_model(
        self, provider: IChatProvider, history: list[ChatMessage], task_id: str,
        conversation_id: str, generation_options: dict[str, Any] | None = None,
    ) -> tuple[str, list[ToolCall]]:
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        fragments: dict[int, dict[str, str]] = {}
        async for value in provider.stream(
            history, tools=self._tool_schemas(), **(generation_options or {})
        ):
            chunk = value if isinstance(value, ChatStreamChunk) else ChatStreamChunk(content=str(value))
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
            await self.event_bus.publish("reasoning.completed", {
                "activity_id": f"reasoning_{uuid.uuid4().hex}",
                "task_id": task_id,
                "conversation_id": conversation_id,
                "summary": "\n\n".join(process_parts),
            })
        if not calls and content:
            await self.event_bus.publish("message.delta", {
                "content": content, "task_id": task_id, "conversation_id": conversation_id,
            })
        return content, calls

    @staticmethod
    def _split_visible_reasoning(content: str) -> tuple[str, str]:
        """Separate a leading, provider-visible <think> block from the final answer."""
        candidate = content.lstrip()
        if not candidate.lower().startswith("<think>"):
            return "", content
        end = candidate.lower().find("</think>", len("<think>"))
        if end < 0:
            return "", content
        reasoning = candidate[len("<think>"):end].strip()
        answer = candidate[end + len("</think>"):].lstrip()
        return reasoning, answer

    async def _run_agent(
        self, workspace_id: str, conversation_id: str, task_id: str, trace_id: str,
        metadata: dict[str, Any], history: list[ChatMessage] | None = None,
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
                provider, working_history, task_id, conversation_id, generation_options
            )
            if not calls:
                return assistant_content
            tool_call_values = [{"id": call.id, "name": call.name, "args": call.arguments, "type": "tool_call"} for call in calls]
            working_history.append(ChatMessage("assistant", assistant_content, {"tool_calls": tool_call_values}))
            await self._execute_tool_batch(
                calls, assistant_content, tool_call_values, working_history,
                workspace_id, conversation_id, task_id, trace_id, metadata,
            )
        raise RuntimeError(f"tool iteration limit ({self._max_tool_iterations}) reached")

    async def _execute_tool_batch(
        self, calls: list[ToolCall], assistant_content: str,
        tool_call_values: list[dict[str, Any]], working_history: list[ChatMessage],
        workspace_id: str, conversation_id: str, task_id: str, trace_id: str,
        metadata: dict[str, Any], *, start_index: int = 0,
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
                call, assistant_content, workspace_id, conversation_id, task_id, trace_id,
                metadata, continuation=continuation,
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
                ensure_ascii=False, default=str,
            ),
            {"tool_call_id": str(record.get("tool_call_id", ""))},
        )

    async def _execution_metadata(
        self, workspace_id: str, conversation_id: str, principal_id: str,
        *, approved: bool = False,
    ) -> dict[str, Any]:
        conversation = await self.repository.get_conversation(workspace_id, conversation_id)
        permission_settings = await self.get_permission_settings(workspace_id)
        api_keys = {
            service: secret
            for (scope, service), secret in self._tool_credentials.items()
            if scope == workspace_id and secret
        }
        return {
            "workspace_id": workspace_id, "conversation_id": conversation_id,
            "principal_id": principal_id, "permission_mode": conversation["permission_mode"],
            "tool_risk_levels": permission_settings["tool_levels"], "approved": approved,
            "workspace_root": str(self._policy.workspace_root),
            "api_keys": api_keys,
        }

    async def _execute_model_tool_call(
        self, call: ToolCall, assistant_content: str, workspace_id: str, conversation_id: str,
        task_id: str, trace_id: str, metadata: dict[str, Any],
        *, continuation: dict[str, Any] | None = None,
    ) -> ToolResult:
        await self.repository.create_tool_call(
            call.id, workspace_id, conversation_id, task_id, call.name, call.arguments, assistant_content,
            continuation,
        )
        await self.event_bus.publish("tool.proposed", {
            "task_id": task_id, "conversation_id": conversation_id, "tool_call_id": call.id,
            "tool_name": call.name, "arguments": call.arguments,
        })
        context = ExecutionContext(trace_id, task_id, call.id, metadata=await self._execution_metadata(
            workspace_id, conversation_id, str(metadata.get("principal_id", "local-user")),
        ))
        try:
            policy = await self._execution_engine.authorize_tool(call.name, call.arguments, context)
        except PermissionRequired as exc:
            approval = await self.repository.create_approval(
                workspace_id, conversation_id, str(metadata.get("principal_id", "local-user")),
                task_id, call.id, exc.decision.arguments, exc.decision.risk.name,
            )
            await self.repository.record_audit(
                workspace_id, str(metadata.get("principal_id", "local-user")),
                "approval.created", approval["id"], "pending",
                {"tool_call_id": call.id, "tool_name": call.name, "risk": exc.decision.risk.name},
            )
            task = await self._task_manager.get_task(task_id)
            if task is not None:
                await self._task_manager.update_status(task_id, TaskStatus.WAITING_APPROVAL)
            await self.event_bus.publish("task.waiting_approval", {
                "task_id": task_id, "conversation_id": conversation_id,
                "tool_call_id": call.id, "approval_id": approval["id"],
            })
            await self.event_bus.publish("approval.requested", self._approval_payload(approval))
            raise AgentPaused(approval) from exc
        except PermissionError as exc:
            await self.repository.update_tool_call(call.id, "denied", summary=str(exc))
            await self.event_bus.publish("tool.failed", {
                "task_id": task_id, "conversation_id": conversation_id, "tool_call_id": call.id,
                "tool_name": call.name, "message": str(exc), "denied": True,
            })
            return ToolResult({"error": str(exc), "denied": True}, f"Tool denied: {exc}")
        except Exception as exc:
            await self.repository.update_tool_call(call.id, "failed", summary=str(exc))
            await self.event_bus.publish("tool.failed", {
                "task_id": task_id, "conversation_id": conversation_id, "tool_call_id": call.id,
                "tool_name": call.name, "message": str(exc),
            })
            return ToolResult({"error": str(exc)}, f"Tool failed: {exc}")
        await self.repository.update_tool_call(
            call.id, "running", arguments=policy.arguments, risk_level=policy.risk.name,
        )
        await self.event_bus.publish("tool.started", {
            "task_id": task_id, "conversation_id": conversation_id,
            "tool_call_id": call.id, "tool_name": call.name,
            "arguments": policy.arguments, "resource_scope": policy.resource_scope,
            "risk_level": policy.risk.name,
        })
        try:
            result = await self._execution_engine.execute_authorized(call.name, policy, context)
        except Exception as exc:
            await self.repository.update_tool_call(call.id, "failed", summary=str(exc))
            await self.event_bus.publish("tool.failed", {
                "task_id": task_id, "conversation_id": conversation_id, "tool_call_id": call.id,
                "tool_name": call.name, "message": str(exc),
            })
            return ToolResult({"error": str(exc)}, f"Tool failed: {exc}")
        await self._complete_tool_call(call, result, task_id, conversation_id)
        return result

    async def _complete_tool_call(self, call: ToolCall, result: ToolResult, task_id: str, conversation_id: str) -> None:
        if not result.success:
            await self.repository.update_tool_call(
                call.id, "failed",
                result={"data": result.data, "metadata": result.metadata},
                summary=result.summary,
            )
            await self.event_bus.publish("tool.failed", {
                "task_id": task_id, "conversation_id": conversation_id,
                "tool_call_id": call.id, "tool_name": call.name,
                "message": result.summary, "code": result.error_code or "TOOL_FAILED",
                "user_hint": result.user_hint, "action": result.action, "data": result.data,
            })
            return
        await self.repository.update_tool_call(
            call.id, "succeeded", result={"data": result.data, "metadata": result.metadata}, summary=result.summary,
        )
        await self.event_bus.publish("tool.completed", {
            "task_id": task_id, "conversation_id": conversation_id, "tool_call_id": call.id,
            "tool_name": call.name, "summary": result.summary, "data": result.data,
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
            call, "__direct_tool__", str(metadata["workspace_id"]), str(metadata["conversation_id"]),
            task_id, trace_id, metadata,
        )
        response = result.summary if result.raw in (None, "") else str(result.raw)
        await self.event_bus.publish("message.delta", {
            "task_id": task_id, "conversation_id": metadata["conversation_id"], "content": response,
        })
        return response

    @staticmethod
    def _approval_payload(approval: dict[str, Any]) -> dict[str, Any]:
        arguments = dict(approval.get("arguments") or {})
        scope = (
            arguments.get("path") or arguments.get("root_dir") or arguments.get("workdir")
            or arguments.get("url") or "current workspace"
        )
        return {
            "approval_id": approval["id"], "task_id": approval["task_id"],
            "conversation_id": approval["conversation_id"], "tool_call_id": approval["tool_call_id"],
            "tool_name": approval["tool_name"], "arguments": arguments,
            "resource_scope": str(scope), "risk_level": approval["risk_level"],
            "status": approval["status"], "version": int(approval["version"]),
            "expires_at": approval["expires_at"],
        }

    async def list_approvals(self, workspace_id: str, conversation_id: str | None = None) -> list[dict[str, Any]]:
        return [self._approval_payload(item) for item in await self.repository.list_approvals(workspace_id, conversation_id)]

    async def decide_approval(
        self, workspace_id: str, approval_id: str, principal_id: str,
        decision: str, version: int,
    ) -> dict[str, Any]:
        approval = await self.repository.decide_approval(workspace_id, approval_id, principal_id, decision, version)
        await self.repository.record_audit(
            workspace_id, principal_id, "approval.decided", approval_id,
            "approved" if decision == "allow" else "denied",
            {"tool_call_id": approval["tool_call_id"], "tool_name": approval["tool_name"]},
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
            await self.repository.append_message(conversation_id, "assistant", response)
            await self.event_bus.publish("message.delta", {"task_id": task_id, "conversation_id": conversation_id, "content": response})
            await self.event_bus.publish("message.completed", {"task_id": task_id, "conversation_id": conversation_id, "content": response})
            await self.event_bus.publish("task.cancelled", {"task_id": task_id, "conversation_id": conversation_id, "message": "approval denied"})
            return {"task_id": task_id, "conversation_id": conversation_id, "status": "denied", "response": response}

        task = await self._task_manager.get_task(task_id)
        if task is not None:
            await self._task_manager.update_status(task_id, TaskStatus.RUNNING)
        tool_row = await self.repository.get_tool_call(str(approval["tool_call_id"]))
        arguments = json.loads(tool_row["arguments_json"])
        call = ToolCall(str(tool_row["id"]), str(tool_row["tool_name"]), arguments)
        context = ExecutionContext(
            f"trace_{uuid.uuid4().hex}", task_id, call.id,
            metadata=await self._execution_metadata(workspace_id, conversation_id, principal_id, approved=True),
        )
        try:
            policy = await self._execution_engine.authorize_tool(call.name, call.arguments, context)
            await self.repository.update_tool_call(
                call.id, "running", arguments=policy.arguments, risk_level=policy.risk.name,
            )
            await self.event_bus.publish("tool.started", {
                "task_id": task_id, "conversation_id": conversation_id,
                "tool_call_id": call.id, "tool_name": call.name,
                "arguments": policy.arguments, "resource_scope": policy.resource_scope,
                "risk_level": policy.risk.name,
            })
            result = await self._execution_engine.execute_authorized(call.name, policy, context)
        except Exception as exc:
            await self.repository.update_tool_call(call.id, "failed", summary=str(exc))
            await self.repository.update_task_status(task_id, "failed")
            if task is not None:
                await self._task_manager.update_status(task_id, TaskStatus.FAILED)
            await self.event_bus.publish("tool.failed", {
                "task_id": task_id, "conversation_id": conversation_id,
                "tool_call_id": call.id, "tool_name": call.name, "message": str(exc),
            })
            await self.event_bus.publish("task.failed", {
                "task_id": task_id, "conversation_id": conversation_id,
                "message": str(exc), "error_type": type(exc).__name__,
            })
            raise
        await self._complete_tool_call(call, result, task_id, conversation_id)
        if tool_row["assistant_content"] == "__direct_tool__":
            response = result.summary if result.raw in (None, "") else str(result.raw)
            await self.event_bus.publish("message.delta", {"task_id": task_id, "conversation_id": conversation_id, "content": response})
        else:
            history = await self._conversation_history(conversation_id)
            try:
                continuation = json.loads(str(tool_row.get("continuation_json") or "{}"))
            except (TypeError, json.JSONDecodeError):
                continuation = {}
            tool_call_values = continuation.get("tool_calls")
            if not isinstance(tool_call_values, list) or not tool_call_values:
                tool_call_values = [
                    {"id": call.id, "name": call.name, "args": call.arguments, "type": "tool_call"}
                ]
            history.append(ChatMessage(
                "assistant", str(tool_row["assistant_content"]), {"tool_calls": tool_call_values},
            ))
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
                    for item in tool_call_values if isinstance(item, dict)
                ]
                call_index = int(continuation.get("call_index", 0))
                if call_index + 1 < len(calls):
                    await self._execute_tool_batch(
                        calls, str(tool_row["assistant_content"]), tool_call_values, history,
                        workspace_id, conversation_id, task_id, f"trace_{uuid.uuid4().hex}",
                        metadata, start_index=call_index + 1, completed_results=completed_results,
                    )
                response = await self._run_agent(
                    workspace_id, conversation_id, task_id, f"trace_{uuid.uuid4().hex}", metadata, history,
                )
            except AgentPaused as paused:
                return {
                    "task_id": task_id, "conversation_id": conversation_id,
                    "status": "waiting_approval", "approval": self._approval_payload(paused.approval),
                }
        await self._finish_task(task_id, conversation_id, response)
        return {"task_id": task_id, "conversation_id": conversation_id, "status": "succeeded", "response": response}

    async def interrupt(self) -> None:
        for task in await self._task_manager.list_tasks(TaskStatus.RUNNING):
            await self._execution_engine.cancel(task.id)
            await self._task_manager.cancel_task(task.id)
            await self.repository.update_task_status(task.id, "cancelled")

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

    async def set_default_chat_model(
        self, workspace_id: str, model_id: str
    ) -> tuple[list[ChatModelSettings], str]:
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
