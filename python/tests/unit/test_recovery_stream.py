from __future__ import annotations

import asyncio

import grpc
import pytest

from agent.event_bus import EventBus
from agent.grpc_server import AgentServiceServicer
from agent.observability import Observability


@pytest.mark.asyncio
async def test_rejected_resume_does_not_forward_another_runs_events() -> None:
    bus = EventBus()
    service = AgentServiceServicer(None, bus, Observability())
    pending = {"conversation_id": "conversation", "task_id": "task"}

    class Rejected(Exception):
        pass

    class Context:
        async def abort(self, code, message):
            assert code == grpc.StatusCode.FAILED_PRECONDITION
            raise Rejected(message)

    async def rejected_operation():
        await bus.publish("task.resumed", {**pending, "trace_id": "accepted-request"})
        await bus.publish("message.delta", {**pending, "content": "another run"})
        await bus.publish("task.succeeded", pending)
        raise ValueError("already resumed")

    received = []
    with pytest.raises(Rejected, match="already resumed"):
        async for event in service._stream_interaction(
            pending, rejected_operation(), Context(), resume_trace_id="rejected-request",
        ):
            received.append(event)
    assert received == []
    await asyncio.sleep(0)  # Release the detached operation's completion callback.


@pytest.mark.asyncio
async def test_missing_historical_checkpoint_is_not_recoverable(core) -> None:
    conversation = await core.create_conversation(title="historical interrupted task")
    await core.repository.create_task_state(
        "old-task", "personal", conversation["id"], "historical", "interrupted", "old input",
    )
    task = await core.get_task("personal", "old-task")
    with pytest.raises(ValueError, match="no execution checkpoint"):
        await core.resume_task("personal", "old-task", "local-user", task["version"])
