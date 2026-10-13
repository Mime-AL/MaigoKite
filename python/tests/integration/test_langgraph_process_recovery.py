from __future__ import annotations

import asyncio
import hashlib
import json
import os
import socket
import sqlite3
import sys
from pathlib import Path
from typing import Any

import grpc
import pytest
from aiohttp import web

from agent.grpc_generated import agent_pb2, agent_pb2_grpc


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _openai_chunk(delta: dict[str, Any], finish_reason: str | None = None) -> bytes:
    body = {
        "id": "chatcmpl-process-recovery",
        "object": "chat.completion.chunk",
        "created": 1,
        "model": "process-recovery",
        "choices": [
            {"index": 0, "delta": delta, "finish_reason": finish_reason}
        ],
    }
    return f"data: {json.dumps(body)}\n\n".encode()


async def _start_model_server(*, two_writes: bool = False) -> tuple[web.AppRunner, str, list[dict[str, Any]]]:
    requests: list[dict[str, Any]] = []

    async def completion(request: web.Request) -> web.StreamResponse:
        body = await request.json()
        requests.append(body)
        response = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
        await response.prepare(request)
        if any(message.get("role") == "tool" for message in body["messages"]):
            await response.write(
                _openai_chunk(
                    {"role": "assistant", "content": "PROCESS_RESUME_OK"},
                    "stop",
                )
            )
        else:
            tool_calls = [
                {
                    "index": index, "id": f"call-process-write-{index}", "type": "function",
                    "function": {"name": "file_write", "arguments": json.dumps({
                        "path": "process-recovery.txt" if index == 0 else "second.txt", "content": "written once",
                    })},
                }
                for index in range(2 if two_writes else 1)
            ]
            await response.write(
                _openai_chunk(
                    {
                        "role": "assistant",
                        "tool_calls": tool_calls,
                    }
                )
            )
            await response.write(_openai_chunk({}, "tool_calls"))
        await response.write(b"data: [DONE]\n\n")
        await response.write_eof()
        return response

    application = web.Application()
    application.router.add_post("/v1/chat/completions", completion)
    runner = web.AppRunner(application)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    assert site._server is not None
    port = int(site._server.sockets[0].getsockname()[1])
    return runner, f"http://127.0.0.1:{port}/v1", requests


async def _start_core(
    tmp_path: Path, grpc_port: int, model_base_url: str, *, barrier: str = "", observe_writes: bool = False,
) -> tuple[asyncio.subprocess.Process, grpc.aio.Channel, Any]:
    python_root = Path(__file__).resolve().parents[2]
    repository_root = python_root.parent
    environment = os.environ.copy()
    # Do not inherit a developer's provider/workspace override into a child.
    for name in list(environment):
        if name.startswith("MAIGOKITE_"):
            environment.pop(name)
    environment.update(
        {
            "PYTHONPATH": str(python_root),
            "MAIGOKITE_DB_PATH": str(tmp_path / "product.sqlite"),
            "MAIGOKITE_WORKSPACE_ROOT": str(tmp_path),
            "MAIGOKITE_PERMISSION_MODE": "read_only",
            "MAIGOKITE_MODEL_PROVIDER": "openai_compatible",
            "MAIGOKITE_MODEL_NAME": "process-recovery",
            "MAIGOKITE_MODEL_BASE_URL": model_base_url,
            "NO_PROXY": "127.0.0.1,localhost",
            "MAIGOKITE_TEST_WRITE_BARRIER": barrier,
        }
    )
    entry = (
        [str(Path(__file__).with_name("runtime_recovery_worker.py"))]
        if barrier or observe_writes else ["-m", "agent.main"]
    )
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        *entry,
        "run",
        "--host",
        "127.0.0.1",
        "--port",
        str(grpc_port),
        cwd=repository_root,
        env=environment,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    channel = grpc.aio.insecure_channel(f"127.0.0.1:{grpc_port}")
    try:
        await asyncio.wait_for(channel.channel_ready(), timeout=15)
    except BaseException:
        if process.returncode is None:
            process.kill()
        stdout, stderr = await process.communicate()
        await channel.close()
        raise AssertionError(
            f"Core failed to start:\n{stdout.decode()}\n{stderr.decode()}"
        )
    return process, channel, agent_pb2_grpc.AgentServiceStub(channel)


async def _crash_core(
    process: asyncio.subprocess.Process, channel: grpc.aio.Channel
) -> None:
    await channel.close()
    if process.returncode is None:
        process.kill()
    await asyncio.wait_for(process.wait(), timeout=5)


@pytest.mark.asyncio
@pytest.mark.parametrize("partial_batch", [False, True])
async def test_approval_survives_real_core_process_restart(tmp_path: Path, partial_batch: bool) -> None:
    model_runner, model_base_url, model_requests = await _start_model_server(two_writes=partial_batch)
    grpc_port = _free_port()
    first_process: asyncio.subprocess.Process | None = None
    first_channel: grpc.aio.Channel | None = None
    second_process: asyncio.subprocess.Process | None = None
    second_channel: grpc.aio.Channel | None = None
    try:
        first_process, first_channel, first = await _start_core(
            tmp_path, grpc_port, model_base_url
        )
        conversation = await first.CreateConversation(
            agent_pb2.ConversationRequest(
                workspace_id="personal",
                title="process recovery",
                permission_mode="read_only",
            )
        )
        before_restart = [
            event
            async for event in first.ProcessMessage(
                agent_pb2.ProcessMessageRequest(
                    workspace_id="personal",
                    conversation_id=conversation.id,
                    principal_id="local-user",
                    content="write the recovery marker",
                )
            )
        ]
        assert [event.type for event in before_restart][-2:] == [
            "task.waiting_approval",
            "approval.requested",
        ]
        assert not (tmp_path / "process-recovery.txt").exists()
        approvals = await first.ListApprovals(
            agent_pb2.ApprovalListRequest(
                workspace_id="personal", conversation_id=conversation.id
            )
        )
        assert len(approvals.approvals) == 1
        approval = approvals.approvals[0]
        assert approval.version == 1
        first_approval = approval
        if partial_batch:
            partial = [event async for event in first.DecideApproval(agent_pb2.ApprovalDecisionRequest(
                workspace_id="personal", approval_id=approval.id, principal_id="local-user",
                decision="allow", version=approval.version,
            ), timeout=15)]
            assert partial[-1].type == "approval.requested"
            assert not any(event.type == "tool.started" for event in partial)
            assert not (tmp_path / "process-recovery.txt").exists()
            assert not (tmp_path / "second.txt").exists()
            approvals = await first.ListApprovals(agent_pb2.ApprovalListRequest(
                workspace_id="personal", conversation_id=conversation.id,
            ), timeout=10)
            assert len(approvals.approvals) == 1
            approval = approvals.approvals[0]
            assert approval.id != first_approval.id and approval.version == 1

        await _crash_core(first_process, first_channel)
        first_process = None
        first_channel = None

        second_process, second_channel, second = await _start_core(
            tmp_path, grpc_port, model_base_url
        )
        after_restart = [
            event
            async for event in second.DecideApproval(
                agent_pb2.ApprovalDecisionRequest(
                    workspace_id="personal",
                    approval_id=approval.id,
                    principal_id="local-user",
                    decision="allow",
                    version=approval.version,
                )
            )
        ]
        assert [event.type for event in after_restart] == ["approval.decided"] + [
            "tool.started", "tool.completed", "file.changed",
        ] * (2 if partial_batch else 1) + [
            "context.updated",
            "model.call.started",
            "message.delta",
            "model.call.completed",
            "message.completed",
            "task.succeeded",
        ]
        assert (
            tmp_path / "process-recovery.txt"
        ).read_text(encoding="utf-8") == "written once"
        task = await second.GetTask(
            agent_pb2.TaskRequest(
                workspace_id="personal", task_id=approval.task_id
            )
        )
        assert task.status == "succeeded"
        history = await second.ListTaskEvents(
            agent_pb2.TaskEventListRequest(
                workspace_id="personal", conversation_id=conversation.id
            )
        )
        assert [item.event_type for item in history.events].count("tool.started") == (2 if partial_batch else 1)
        if partial_batch:
            assert (tmp_path / "second.txt").read_text(encoding="utf-8") == "written once"
        assert len(model_requests) == 2

        with sqlite3.connect(tmp_path / "product.sqlite") as database:
            continuation = database.execute(
                "SELECT continuation_json FROM tool_calls WHERE id=?",
                (approval.tool_call_id,),
            ).fetchone()
            stored_approval = database.execute(
                "SELECT arguments_hash,status,version FROM approvals WHERE id=?",
                (approval.id,),
            ).fetchone()
            if partial_batch:
                assert database.execute("SELECT status,version FROM approvals WHERE id=?",
                                        (first_approval.id,)).fetchone() == ("consumed", 2)
        assert continuation == ("{}",)
        assert stored_approval is not None
        assert stored_approval[0]
        assert stored_approval[1:] == ("consumed", 2)
    finally:
        if first_process is not None and first_channel is not None:
            await _crash_core(first_process, first_channel)
        if second_process is not None and second_channel is not None:
            await _crash_core(second_process, second_channel)
        await model_runner.cleanup()


@pytest.mark.asyncio
@pytest.mark.parametrize("crash_point", ["before", "after"])
async def test_file_write_survives_core_process_crash(tmp_path: Path, crash_point: str) -> None:
    model_runner, model_url, model_requests = await _start_model_server()
    port = _free_port()
    process = channel = restarted = restarted_channel = None
    decision_stream = None
    try:
        process, channel, client = await _start_core(tmp_path, port, model_url, barrier=crash_point)
        conversation = await client.CreateConversation(agent_pb2.ConversationRequest(
            workspace_id="personal", title="file crash recovery", permission_mode="read_only",
        ), timeout=10)
        events = [event async for event in client.ProcessMessage(agent_pb2.ProcessMessageRequest(
            workspace_id="personal", conversation_id=conversation.id, principal_id="local-user", content="write a file",
        ), timeout=15)]
        assert events[-1].type == "approval.requested"
        pending = await client.ListApprovals(agent_pb2.ApprovalListRequest(
            workspace_id="personal", conversation_id=conversation.id,
        ), timeout=10)
        approval = pending.approvals[0]
        target = tmp_path / "process-recovery.txt"
        assert not target.exists()
        expected_hash = hashlib.sha256(json.dumps(
            json.loads(approval.arguments_json), ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode()).hexdigest()
        decision_stream = client.DecideApproval(agent_pb2.ApprovalDecisionRequest(
            workspace_id="personal", approval_id=approval.id, principal_id="local-user",
            decision="allow", version=approval.version,
        ), timeout=20)
        assert (await decision_stream.read()).type == "approval.decided"

        async def wait_for_barrier() -> None:
            while not (tmp_path / "write-barrier").exists():
                if process.returncode is not None:
                    raise AssertionError("Core exited before reaching the file-write barrier")
                await asyncio.sleep(0.02)

        await asyncio.wait_for(wait_for_barrier(), timeout=10)
        if crash_point == "before":
            assert not target.exists()
            mtime = None
        else:
            assert target.read_bytes() == b"written once"
            mtime = target.stat().st_mtime_ns
        with sqlite3.connect(tmp_path / "product.sqlite") as database:
            assert database.execute("SELECT status,version,arguments_hash FROM approvals WHERE id=?",
                                    (approval.id,)).fetchone() == ("consumed", 2, expected_hash)
            assert database.execute("SELECT status FROM tool_calls WHERE id=?",
                                    (approval.tool_call_id,)).fetchone() == ("running",)
        await _crash_core(process, channel)
        assert process.returncode != 0
        process = channel = None
        decision_stream.cancel()

        restarted, restarted_channel, client = await _start_core(
            tmp_path, port, model_url, observe_writes=True,
        )
        task = await client.GetTask(agent_pb2.TaskRequest(
            workspace_id="personal", task_id=approval.task_id,
        ), timeout=10)
        assert task.status == "interrupted"
        # The restarted process has no test-only recovery hook. Exercise the
        # production entry, including its owner/version checks, before replay.
        for principal, version, expected in [
            ("", task.version, grpc.StatusCode.PERMISSION_DENIED),
            ("unrelated-user", task.version, grpc.StatusCode.PERMISSION_DENIED),
            ("local-user", 0, grpc.StatusCode.INVALID_ARGUMENT),
            ("local-user", task.version - 1, grpc.StatusCode.FAILED_PRECONDITION),
        ]:
            with pytest.raises(grpc.aio.AioRpcError) as rejected:
                _ = [event async for event in client.ResumeTask(agent_pb2.ResumeTaskRequest(
                    workspace_id="personal", task_id=task.id, principal_id=principal, version=version,
                ), timeout=10)]
            assert rejected.value.code() == expected
        resumed = [event async for event in client.ResumeTask(agent_pb2.ResumeTaskRequest(
            workspace_id="personal", task_id=task.id, principal_id="local-user", version=task.version,
        ), timeout=15)]
        assert resumed[0].type == "task.resumed" and resumed[-1].type == "task.succeeded"
        assert all(event.event_id and event.sequence > 0 for event in resumed)
        with pytest.raises(grpc.aio.AioRpcError) as repeated:
            _ = [event async for event in client.ResumeTask(agent_pb2.ResumeTaskRequest(
                workspace_id="personal", task_id=task.id, principal_id="local-user", version=task.version,
            ), timeout=10)]
        assert repeated.value.code() == grpc.StatusCode.FAILED_PRECONDITION
        task = await client.GetTask(agent_pb2.TaskRequest(workspace_id="personal", task_id=task.id), timeout=10)
        assert task.status == "succeeded", task.last_error
        assert target.read_bytes() == b"written once"
        receipt_sizes = [int(value) for value in (tmp_path / "write-receipts").read_text().splitlines()]
        assert receipt_sizes == ([12] if crash_point == "before" else [12, 0])
        if mtime is not None:
            assert target.stat().st_mtime_ns == mtime
        history = await client.ListTaskEvents(agent_pb2.TaskEventListRequest(
            workspace_id="personal", conversation_id=conversation.id,
        ), timeout=10)
        kinds = [event.event_type for event in history.events]
        assert kinds.count("task.resumed") == 1
        persisted = {event.id: event for event in history.events}
        for event in resumed:
            assert persisted[event.event_id].sequence == event.sequence
            assert persisted[event.event_id].occurred_at == event.occurred_at
            live_payload = json.loads(event.payload_json)
            for identity in ("event_id", "sequence", "occurred_at"):
                live_payload.pop(identity, None)
            assert json.loads(persisted[event.event_id].payload_json) == live_payload
        assert kinds.count("tool.started") == 2  # At-least-once invocation is visible.
        assert kinds.count("tool.completed") == 1
        assert kinds.count("task.succeeded") == 1 and kinds[-1] == "task.succeeded"
        assert "task.failed" not in kinds and "task.cancelled" not in kinds
        assert len({event.id for event in history.events}) == len(history.events)
        assert [event.sequence for event in history.events] == sorted(event.sequence for event in history.events)
        completed = next(event for event in history.events if event.event_type == "tool.completed")
        result = json.loads(completed.payload_json)["result"]
        assert bool(result.get("reconciled")) == (crash_point == "after")
        assert len(model_requests) == 2
        assert model_requests[-1]["messages"][-1]["role"] == "tool"
        with sqlite3.connect(tmp_path / "product.sqlite") as database:
            assert database.execute("SELECT status,version,arguments_hash FROM approvals WHERE id=?",
                                    (approval.id,)).fetchone() == ("consumed", 2, expected_hash)
            assert database.execute("SELECT status,continuation_json FROM tool_calls WHERE id=?",
                                    (approval.tool_call_id,)).fetchone() == ("succeeded", "{}")
            assert database.execute("SELECT content FROM messages WHERE conversation_id=? AND role='assistant'",
                                    (conversation.id,)).fetchall() == [("PROCESS_RESUME_OK",)]
    finally:
        if decision_stream is not None:
            decision_stream.cancel()
        if process is not None and channel is not None:
            await _crash_core(process, channel)
        if restarted is not None and restarted_channel is not None:
            await _crash_core(restarted, restarted_channel)
        await model_runner.cleanup()
