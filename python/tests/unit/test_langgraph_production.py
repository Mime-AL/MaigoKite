from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from pydantic import Field

from agent.config_manager import ConfigManager
from agent.core import AgentCore
from agent.event_bus import EventBus
from agent.models.chat_provider import (
    ChatMessage,
    ChatResponse,
    ChatStreamChunk,
    IChatProvider,
    ToolCallChunk,
)
from agent.observability import Observability
from agent.repository import SQLiteRepository


class RuleModel(BaseChatModel):
    tool_name: str = ""
    tool_args: dict[str, Any] = Field(default_factory=dict)
    final_text: str = "done"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "RuleModel":
        return self

    def _reply(self, messages: list[BaseMessage]) -> AIMessage:
        if self.tool_name and not isinstance(messages[-1], ToolMessage):
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": self.tool_name,
                        "args": self.tool_args,
                        "id": f"call-{self.tool_name}",
                        "type": "tool_call",
                    }
                ],
            )
        return AIMessage(content=self.final_text)

    def _generate(self, messages: list[BaseMessage], **kwargs: Any) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self._reply(messages))])

    async def _agenerate(self, messages: list[BaseMessage], **kwargs: Any) -> ChatResult:
        return self._generate(messages, **kwargs)

    async def _astream(
        self, messages: list[BaseMessage], **kwargs: Any
    ) -> AsyncIterator[ChatGenerationChunk]:
        message = self._reply(messages)
        if message.tool_calls:
            yield ChatGenerationChunk(
                message=AIMessageChunk(content="", tool_calls=message.tool_calls)
            )
            return
        for character in str(message.content):
            yield ChatGenerationChunk(message=AIMessageChunk(content=character))

    @property
    def _llm_type(self) -> str:
        return "nanami-production-rule-model"


class SlowModel(BaseChatModel):
    started: Any = Field(default_factory=asyncio.Event, exclude=True)
    cancelled: Any = Field(default_factory=asyncio.Event, exclude=True)

    def bind_tools(self, tools: Any, **kwargs: Any) -> "SlowModel":
        return self

    def _generate(self, messages: list[BaseMessage], **kwargs: Any) -> ChatResult:
        raise AssertionError("async streaming is required")

    async def _astream(
        self, messages: list[BaseMessage], **kwargs: Any
    ) -> AsyncIterator[ChatGenerationChunk]:
        try:
            self.started.set()
            yield ChatGenerationChunk(message=AIMessageChunk(content="first"))
            await asyncio.Event().wait()
        finally:
            self.cancelled.set()

    @property
    def _llm_type(self) -> str:
        return "nanami-production-slow-model"


class SerialWritesModel(BaseChatModel):
    def bind_tools(self, tools: Any, **kwargs: Any) -> "SerialWritesModel":
        return self

    @staticmethod
    def _reply(messages: list[BaseMessage]) -> AIMessage:
        tool_results = [message for message in messages if isinstance(message, ToolMessage)]
        calls = [
            {
                "name": "file_write",
                "args": {"path": "first.txt", "content": "first"},
                "id": "call-first-write",
                "type": "tool_call",
            },
            {
                "name": "file_write",
                "args": {"path": "second.txt", "content": "second"},
                "id": "call-second-write",
                "type": "tool_call",
            },
        ]
        if not tool_results:
            return AIMessage(content="", tool_calls=calls)
        if len(tool_results) == 1:
            return AIMessage(content="", tool_calls=[calls[1]])
        return AIMessage(content="both complete")

    def _generate(self, messages: list[BaseMessage], **kwargs: Any) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self._reply(messages))])

    async def _agenerate(self, messages: list[BaseMessage], **kwargs: Any) -> ChatResult:
        return self._generate(messages, **kwargs)

    async def _astream(
        self, messages: list[BaseMessage], **kwargs: Any
    ) -> AsyncIterator[ChatGenerationChunk]:
        reply = self._reply(messages)
        yield ChatGenerationChunk(
            message=AIMessageChunk(content=reply.content, tool_calls=reply.tool_calls)
        )

    @property
    def _llm_type(self) -> str:
        return "nanami-production-serial-writes-model"


class ModelOwner(IChatProvider):
    def __init__(self, model: BaseChatModel) -> None:
        self.langchain_model = model
        self.closed = False

    @property
    def model_name(self) -> str:
        return "runtime-test-model"

    async def chat(self, messages: list[ChatMessage], **kwargs: Any) -> ChatResponse:
        raise AssertionError("new Runtime must use the native LangChain model")

    async def stream(
        self, messages: list[ChatMessage], **kwargs: Any
    ) -> AsyncIterator[ChatStreamChunk]:
        raise AssertionError("new Runtime must use the native LangChain model")
        yield

    async def aclose(self) -> None:
        self.closed = True


class LegacyWriteProvider(IChatProvider):
    @property
    def model_name(self) -> str:
        return "legacy-write"

    async def chat(self, messages: list[ChatMessage], **kwargs: Any) -> ChatResponse:
        return ChatResponse("unused")

    async def stream(
        self, messages: list[ChatMessage], **kwargs: Any
    ) -> AsyncIterator[ChatStreamChunk]:
        if messages[-1].role == "tool":
            yield ChatStreamChunk(content="write complete")
            return
        yield ChatStreamChunk(
            tool_call_chunks=[
                ToolCallChunk(
                    index=0,
                    id="call-file_write",
                    name="file_write",
                    arguments='{"path":"result.txt","content":"same"}',
                )
            ]
        )


async def make_langgraph_core(
    tmp_path: Path, model: BaseChatModel
) -> tuple[AgentCore, EventBus, ModelOwner]:
    config = ConfigManager()
    config.set("agent.runtime", "langgraph")
    config.set("agent.langgraph_checkpoint_path", str(tmp_path / "checkpoints.sqlite"))
    config.set("storage.sqlite_path", str(tmp_path / "product.sqlite"))
    config.set("workspace.root", str(tmp_path))
    config.set("permissions.default_mode", "read_only")
    config.set(
        "models.chat",
        {
            "provider": "ollama",
            "default": "runtime-test",
            "base_url": "http://127.0.0.1:11434",
        },
    )
    event_bus = EventBus()
    core = AgentCore(
        config,
        event_bus,
        Observability(),
        repository=SQLiteRepository(tmp_path / "product.sqlite"),
    )
    owner = ModelOwner(model)
    core.models._provider_factory = lambda **_kwargs: owner
    await core.initialize()
    return core, event_bus, owner


@pytest.mark.asyncio
async def test_production_langgraph_chat_read_and_write_approval(tmp_path: Path) -> None:
    model = RuleModel(
        tool_name="file_write",
        tool_args={"path": "created.txt", "content": "created once"},
        final_text="write complete",
    )
    core, event_bus, owner = await make_langgraph_core(tmp_path, model)
    events: list[tuple[str, dict[str, Any]]] = []

    async def capture(kind: str, payload: dict[str, Any]) -> None:
        events.append((kind, payload))

    event_bus.subscribe("*", capture)
    try:
        conversation = await core.create_conversation(
            title="production runtime", permission_mode="read_only"
        )
        blocked = await core.run(
            "write created.txt",
            {"conversation_id": conversation["id"]},
        )
        assert blocked["status"] == "waiting_approval"
        assert not (tmp_path / "created.txt").exists()
        approval = blocked["approval"]
        result = await core.decide_approval(
            "personal",
            approval["approval_id"],
            "local-user",
            "allow",
            approval["version"],
        )
        assert result["status"] == "succeeded"
        assert result["response"] == "write complete"
        assert (tmp_path / "created.txt").read_text(encoding="utf-8") == "created once"
        task = await core.get_task("personal", blocked["task_id"])
        assert task["status"] == "succeeded"
        kinds = [kind for kind, _payload in events]
        assert kinds.index("tool.proposed") < kinds.index("approval.requested")
        assert kinds.index("approval.decided") < kinds.index("tool.started")
        assert kinds[-1] == "task.succeeded"
        assert all(
            not any(key.startswith("langgraph") for key in payload)
            for _kind, payload in events
        )
    finally:
        await core.shutdown()
    assert owner.closed is True


@pytest.mark.asyncio
async def test_production_langgraph_chat_executes_file_read_without_approval(
    tmp_path: Path,
) -> None:
    (tmp_path / "note.txt").write_text("hello", encoding="utf-8")
    core, event_bus, _owner = await make_langgraph_core(
        tmp_path,
        RuleModel(
            tool_name="file_read",
            tool_args={"path": "note.txt"},
            final_text="read complete",
        ),
    )
    events: list[str] = []

    async def capture(kind: str, _payload: dict[str, Any]) -> None:
        events.append(kind)

    event_bus.subscribe("*", capture)
    try:
        conversation = await core.create_conversation(title="read")
        result = await core.run(
            "read note.txt", {"conversation_id": conversation["id"]}
        )
        assert result["status"] == "succeeded"
        assert result["response"] == "read complete"
        assert "tool.started" in events and "tool.completed" in events
        assert "approval.requested" not in events
        tool_call = await core.repository.get_tool_call("call-file_read")
        assert tool_call["status"] == "succeeded"
    finally:
        await core.shutdown()


@pytest.mark.asyncio
async def test_parallel_protected_calls_are_serialized_into_two_approvals(
    tmp_path: Path,
) -> None:
    core, _event_bus, _owner = await make_langgraph_core(
        tmp_path, SerialWritesModel()
    )
    try:
        conversation = await core.create_conversation(
            title="serial approvals", permission_mode="read_only"
        )
        first = await core.run(
            "write both files", {"conversation_id": conversation["id"]}
        )
        assert first["status"] == "waiting_approval", first
        assert first["approval"]["tool_call_id"] == "call-first-write"
        second = await core.decide_approval(
            "personal",
            first["approval"]["approval_id"],
            "local-user",
            "allow",
            first["approval"]["version"],
        )
        assert second["status"] == "waiting_approval"
        assert second["approval"]["tool_call_id"] == "call-second-write"
        assert (tmp_path / "first.txt").read_text(encoding="utf-8") == "first"
        assert not (tmp_path / "second.txt").exists()
        final = await core.decide_approval(
            "personal",
            second["approval"]["approval_id"],
            "local-user",
            "allow",
            second["approval"]["version"],
        )
        assert final["status"] == "succeeded"
        assert final["response"] == "both complete"
        assert (tmp_path / "second.txt").read_text(encoding="utf-8") == "second"
    finally:
        await core.shutdown()


@pytest.mark.asyncio
async def test_production_cancel_waits_for_model_and_stops_events(tmp_path: Path) -> None:
    model = SlowModel()
    core, event_bus, owner = await make_langgraph_core(tmp_path, model)
    events: list[tuple[str, dict[str, Any]]] = []
    first_delta = asyncio.Event()

    async def capture(kind: str, payload: dict[str, Any]) -> None:
        events.append((kind, payload))
        if kind == "message.delta":
            first_delta.set()

    event_bus.subscribe("*", capture)
    conversation = await core.create_conversation(title="cancel")
    run_task = asyncio.create_task(
        core.run("stream", {"conversation_id": conversation["id"]})
    )
    try:
        await asyncio.wait_for(first_delta.wait(), timeout=2)
        task_id = next(payload["task_id"] for kind, payload in events if kind == "task.started")
        cancelled = await core.cancel_task("personal", task_id)
        result = await asyncio.wait_for(run_task, timeout=2)
        assert cancelled["status"] == "cancelled"
        assert result["status"] == "cancelled"
        await asyncio.wait_for(model.cancelled.wait(), timeout=1)
        cancelled_index = next(
            index for index, event in enumerate(events) if event[0] == "task.cancelled"
        )
        assert events[cancelled_index + 1 :] == []
    finally:
        if not run_task.done():
            run_task.cancel()
            await asyncio.gather(run_task, return_exceptions=True)
        await core.shutdown()
    assert owner.closed is True


@pytest.mark.asyncio
async def test_sync_file_read_cancel_stops_runtime_but_not_worker_thread(
    tmp_path: Path,
) -> None:
    (tmp_path / "slow.txt").write_text("value", encoding="utf-8")
    model = RuleModel(
        tool_name="file_read",
        tool_args={"path": "slow.txt"},
        final_text="must not be emitted",
    )
    core, event_bus, _owner = await make_langgraph_core(tmp_path, model)
    runtime = core._langgraph_runtime
    assert runtime is not None
    read_spec = next(spec for spec in runtime.tool_specs if spec.tool.name == "file_read")
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()

    def slow_read(
        path: str, encoding: str = "utf-8", max_bytes: int = 100_000
    ) -> dict[str, Any]:
        started.set()
        release.wait(timeout=5)
        finished.set()
        return {
            "path": path,
            "content": "value",
            "size_bytes": 5,
            "truncated": False,
        }

    read_spec.runtime_tool.func = slow_read
    events: list[tuple[str, dict[str, Any]]] = []

    async def capture(kind: str, payload: dict[str, Any]) -> None:
        events.append((kind, payload))

    event_bus.subscribe("*", capture)
    conversation = await core.create_conversation(title="sync cancel")
    run_task = asyncio.create_task(
        core.run("read slow.txt", {"conversation_id": conversation["id"]})
    )
    try:
        await asyncio.wait_for(asyncio.to_thread(started.wait), timeout=2)
        task_id = next(
            payload["task_id"] for kind, payload in events if kind == "task.started"
        )
        await core.cancel_task("personal", task_id)
        result = await asyncio.wait_for(run_task, timeout=2)
        assert result["status"] == "cancelled"
        assert finished.is_set() is False
        cancelled_index = next(
            index for index, event in enumerate(events) if event[0] == "task.cancelled"
        )
        release.set()
        await asyncio.wait_for(asyncio.to_thread(finished.wait), timeout=2)
        await asyncio.sleep(0)
        assert events[cancelled_index + 1 :] == []
    finally:
        release.set()
        if not run_task.done():
            run_task.cancel()
            await asyncio.gather(run_task, return_exceptions=True)
        await core.shutdown()


@pytest.mark.asyncio
async def test_core_shutdown_cancels_runs_before_closing_model_owner(
    tmp_path: Path,
) -> None:
    model = SlowModel()
    core, event_bus, owner = await make_langgraph_core(tmp_path, model)
    first_delta = asyncio.Event()

    async def capture(kind: str, _payload: dict[str, Any]) -> None:
        if kind == "message.delta":
            first_delta.set()

    event_bus.subscribe("*", capture)
    conversation = await core.create_conversation(title="shutdown")
    run_task = asyncio.create_task(
        core.run("stream", {"conversation_id": conversation["id"]})
    )
    await asyncio.wait_for(first_delta.wait(), timeout=2)
    await core.shutdown()
    result = await asyncio.wait_for(run_task, timeout=2)

    assert result["status"] == "cancelled"
    await asyncio.wait_for(model.cancelled.wait(), timeout=1)
    assert owner.closed is True


@pytest.mark.asyncio
async def test_legacy_and_new_runtime_keep_product_write_semantics(tmp_path: Path) -> None:
    legacy_root = tmp_path / "legacy"
    new_root = tmp_path / "new"
    legacy_root.mkdir()
    new_root.mkdir()

    legacy_config = ConfigManager()
    legacy_config.set("workspace.root", str(legacy_root))
    legacy_config.set("permissions.default_mode", "read_only")
    legacy_bus = EventBus()
    legacy = AgentCore(
        legacy_config,
        legacy_bus,
        Observability(),
        provider=LegacyWriteProvider(),
        repository=SQLiteRepository(legacy_root / "product.sqlite"),
    )
    await legacy.initialize()
    new, new_bus, _owner = await make_langgraph_core(
        new_root,
        RuleModel(
            tool_name="file_write",
            tool_args={"path": "result.txt", "content": "same"},
            final_text="write complete",
        ),
    )
    legacy_events: list[str] = []
    new_events: list[str] = []

    async def legacy_capture(kind: str, _payload: dict[str, Any]) -> None:
        legacy_events.append(kind)

    async def new_capture(kind: str, _payload: dict[str, Any]) -> None:
        new_events.append(kind)

    legacy_bus.subscribe("*", legacy_capture)
    new_bus.subscribe("*", new_capture)
    try:
        legacy_conversation = await legacy.create_conversation(title="compare")
        new_conversation = await new.create_conversation(title="compare")
        legacy_blocked = await legacy.run(
            "write result.txt", {"conversation_id": legacy_conversation["id"]}
        )
        new_blocked = await new.run(
            "write result.txt", {"conversation_id": new_conversation["id"]}
        )
        for core, blocked in ((legacy, legacy_blocked), (new, new_blocked)):
            approval = blocked["approval"]
            completed = await core.decide_approval(
                "personal",
                approval["approval_id"],
                "local-user",
                "allow",
                approval["version"],
            )
            assert completed["status"] == "succeeded"
            assert completed["response"] == "write complete"
        assert (legacy_root / "result.txt").read_text(encoding="utf-8") == "same"
        assert (new_root / "result.txt").read_text(encoding="utf-8") == "same"
        required = {
            "task.started",
            "tool.proposed",
            "approval.requested",
            "approval.decided",
            "tool.started",
            "tool.completed",
            "message.completed",
            "task.succeeded",
        }
        assert required <= set(legacy_events)
        assert required <= set(new_events)
        milestones = [
            "task.started",
            "tool.proposed",
            "task.waiting_approval",
            "approval.requested",
            "approval.decided",
            "tool.started",
            "tool.completed",
            "message.completed",
            "task.succeeded",
        ]
        assert [event for event in legacy_events if event in milestones] == milestones
        assert [event for event in new_events if event in milestones] == milestones
    finally:
        await legacy.shutdown()
        await new.shutdown()
