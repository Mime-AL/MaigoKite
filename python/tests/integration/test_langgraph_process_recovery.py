from __future__ import annotations

import asyncio
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


async def _start_model_server() -> tuple[web.AppRunner, str, list[dict[str, Any]]]:
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
            await response.write(
                _openai_chunk(
                    {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call-process-write",
                                "type": "function",
                                "function": {
                                    "name": "file_write",
                                    "arguments": json.dumps(
                                        {
                                            "path": "process-recovery.txt",
                                            "content": "written once",
                                        }
                                    ),
                                },
                            }
                        ],
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
    tmp_path: Path, grpc_port: int, model_base_url: str
) -> tuple[asyncio.subprocess.Process, grpc.aio.Channel, Any]:
    python_root = Path(__file__).resolve().parents[2]
    repository_root = python_root.parent
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONPATH": str(python_root),
            "MAIGOKITE_AGENT_RUNTIME": "langgraph",
            "MAIGOKITE_DB_PATH": str(tmp_path / "product.sqlite"),
            "MAIGOKITE_WORKSPACE_ROOT": str(tmp_path),
            "MAIGOKITE_PERMISSION_MODE": "read_only",
            "MAIGOKITE_MODEL_PROVIDER": "openai_compatible",
            "MAIGOKITE_MODEL_NAME": "process-recovery",
            "MAIGOKITE_MODEL_BASE_URL": model_base_url,
            "NO_PROXY": "127.0.0.1,localhost",
        }
    )
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "agent.main",
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
async def test_approval_survives_real_core_process_restart(tmp_path: Path) -> None:
    model_runner, model_base_url, model_requests = await _start_model_server()
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
        assert [event.type for event in after_restart] == [
            "approval.decided",
            "tool.started",
            "tool.completed",
            "message.delta",
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
        assert [item.event_type for item in history.events].count("tool.started") == 1
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
