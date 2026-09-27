from __future__ import annotations
import json
import grpc
import pytest
from agent.grpc_generated import agent_pb2, agent_pb2_grpc
from agent.grpc_server import AgentServiceServicer


@pytest.mark.asyncio
async def test_grpc_conversation_and_stream(core, tmp_path):
    server = grpc.aio.server()
    agent_pb2_grpc.add_AgentServiceServicer_to_server(
        AgentServiceServicer(core, core.event_bus, core.observability), server
    )
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    try:
        async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
            stub = agent_pb2_grpc.AgentServiceStub(channel)
            access = await stub.CheckWorkspaceAccess(
                agent_pb2.WorkspaceAccessRequest(workspace_id="personal", principal_id="local-user")
            )
            assert access.allowed and access.role == "owner"
            configured = await stub.UpdateChatModelSettings(
                agent_pb2.UpdateChatModelSettingsRequest(
                    workspace_id="personal",
                    settings=agent_pb2.ChatModelSettings(
                        provider="openai_compatible",
                        model="local-model",
                        base_url="http://127.0.0.1:1234/v1",
                        temperature=0.7,
                        max_tokens=4096,
                        timeout_seconds=60,
                    ),
                )
            )
            loaded = await stub.GetChatModelSettings(agent_pb2.WorkspaceRequest(workspace_id="personal"))
            assert loaded.provider == configured.provider == "openai_compatible" and loaded.base_url.endswith("/v1")
            second = await stub.UpsertChatModel(
                agent_pb2.UpsertChatModelRequest(
                    workspace_id="personal",
                    settings=agent_pb2.ChatModelSettings(
                        name="Second",
                        provider="ollama",
                        model="qwen",
                        base_url="http://127.0.0.1:11434",
                        temperature=0.4,
                        max_tokens=2048,
                        timeout_seconds=30,
                    ),
                )
            )
            catalog = await stub.SetDefaultChatModel(
                agent_pb2.ChatModelRequest(workspace_id="personal", model_id=second.id)
            )
            assert len(catalog.models) == 2 and catalog.default_model_id == second.id
            preferences = await stub.UpdateUserPreferences(
                agent_pb2.UpdateUserPreferencesRequest(
                    workspace_id="personal",
                    subject_user_id="local-user",
                    preferences=agent_pb2.UserPreferences(assistant_name="小七"),
                )
            )
            loaded_preferences = await stub.GetUserPreferences(
                agent_pb2.UserPreferencesRequest(workspace_id="personal", subject_user_id="local-user")
            )
            assert preferences.assistant_name == loaded_preferences.assistant_name == "小七"
            memory = await stub.UpsertMemory(
                agent_pb2.UpsertMemoryRequest(
                    workspace_id="personal",
                    subject_user_id="local-user",
                    memory=agent_pb2.Memory(category="preference", content="使用中文", confidence=1),
                )
            )
            memories = await stub.ListMemories(
                agent_pb2.MemoryListRequest(
                    workspace_id="personal",
                    subject_user_id="local-user",
                    query="中文",
                )
            )
            assert [item.id for item in memories.memories] == [memory.id]
            summary = await stub.GetWorkspaceDataSummary(agent_pb2.WorkspaceRequest(workspace_id="personal"))
            assert summary.storage_backend == "sqlite" and summary.memory_count == 1
            mcp = await stub.ListMCPServers(agent_pb2.WorkspaceRequest(workspace_id="personal"))
            assert list(mcp.servers) == []
            await stub.DeleteMemory(
                agent_pb2.MemoryRequest(
                    workspace_id="personal",
                    subject_user_id="local-user",
                    memory_id=memory.id,
                )
            )
            await stub.SetToolCredential(
                agent_pb2.SetToolCredentialRequest(
                    workspace_id="personal",
                    service="tavily",
                    api_key="secret-search-key",
                )
            )
            assert core._tool_credentials[("personal", "tavily")] == "secret-search-key"
            conversation = await stub.CreateConversation(
                agent_pb2.ConversationRequest(workspace_id="personal", title="grpc")
            )
            await core.repository.ensure_workspace("team-a", "Team A", "team")
            foreign = await core.create_conversation("team-a", "foreign")
            with pytest.raises(grpc.aio.AioRpcError) as denied:
                await stub.ProcessMessage(
                    agent_pb2.ProcessMessageRequest(
                        workspace_id="personal", conversation_id=foreign["id"], content="must not cross workspace"
                    )
                ).read()
            assert denied.value.code() == grpc.StatusCode.NOT_FOUND
            updated = await stub.UpdateConversationPermission(
                agent_pb2.ConversationPermissionRequest(
                    workspace_id="personal", conversation_id=conversation.id, permission_mode="read_only"
                )
            )
            assert updated.permission_mode == "read_only"
            runtime = await stub.UpdateConversationSettings(
                agent_pb2.ConversationSettingsRequest(
                    workspace_id="personal",
                    conversation_id=conversation.id,
                    model_id=configured.id,
                    response_mode="fast",
                )
            )
            assert runtime.model_id == configured.id and runtime.response_mode == "fast"
            permissions = await stub.GetPermissionSettings(agent_pb2.WorkspaceRequest(workspace_id="personal"))
            assert permissions.default_mode == "read_only" and permissions.tool_levels["file_write"] == 4
            events = [
                event
                async for event in stub.ProcessMessage(
                    agent_pb2.ProcessMessageRequest(
                        workspace_id="personal", conversation_id=conversation.id, content="ping"
                    )
                )
            ]
            assert any(event.type == "message.delta" and "reply:ping" in event.content for event in events)
            command = "/tool file_write " + json.dumps({"path": "grpc.txt", "content": "ok"})
            approval_events = [
                event
                async for event in stub.ProcessMessage(
                    agent_pb2.ProcessMessageRequest(
                        workspace_id="personal",
                        conversation_id=conversation.id,
                        principal_id="local-user",
                        content=command,
                    )
                )
            ]
            approval_types = [event.type for event in approval_events]
            assert approval_types == [
                "task.started",
                "tool.proposed",
                "task.waiting_approval",
                "approval.requested",
            ]
            approvals = await stub.ListApprovals(
                agent_pb2.ApprovalListRequest(workspace_id="personal", conversation_id=conversation.id)
            )
            assert len(approvals.approvals) == 1
            approval = approvals.approvals[0]
            decision_events = [
                event
                async for event in stub.DecideApproval(
                    agent_pb2.ApprovalDecisionRequest(
                        workspace_id="personal",
                        approval_id=approval.id,
                        principal_id="local-user",
                        decision="allow",
                        version=approval.version,
                    )
                )
            ]
            decision_types = [event.type for event in decision_events]
            assert decision_types == [
                "approval.decided",
                "tool.started",
                "tool.completed",
                "message.delta",
                "message.completed",
                "task.succeeded",
            ]
            assert (tmp_path / "grpc.txt").read_text() == "ok"
            messages = await stub.ListMessages(
                agent_pb2.ConversationRequest(workspace_id="personal", conversation_id=conversation.id)
            )
            assert len(messages.messages) == 4
            tasks = await stub.ListTasks(
                agent_pb2.TaskListRequest(
                    workspace_id="personal",
                    conversation_id=conversation.id,
                )
            )
            assert len(tasks.tasks) == 2 and all(item.conversation_id == conversation.id for item in tasks.tasks)
            task = await stub.GetTask(
                agent_pb2.TaskRequest(
                    workspace_id="personal",
                    task_id=tasks.tasks[0].id,
                )
            )
            assert task.status in {"succeeded", "waiting_approval"}
            history = await stub.ListTaskEvents(
                agent_pb2.TaskEventListRequest(
                    workspace_id="personal",
                    conversation_id=conversation.id,
                    after_sequence=0,
                )
            )
            assert history.events and [item.sequence for item in history.events] == sorted(
                item.sequence for item in history.events
            )
            assert all(item.id and item.occurred_at for item in history.events)
            skills = await stub.ListSkills(agent_pb2.WorkspaceRequest(workspace_id="personal"))
            assert list(skills.skills) == []

            cancel_events = [
                event
                async for event in stub.ProcessMessage(
                    agent_pb2.ProcessMessageRequest(
                        workspace_id="personal",
                        conversation_id=conversation.id,
                        principal_id="local-user",
                        content="/tool file_write " + json.dumps({"path": "cancelled.txt", "content": "no"}),
                    )
                )
            ]
            pending_task_id = cancel_events[0].task_id
            cancelled = await stub.CancelTask(
                agent_pb2.TaskRequest(
                    workspace_id="personal",
                    task_id=pending_task_id,
                )
            )
            assert cancelled.status == "cancelled" and not (tmp_path / "cancelled.txt").exists()
            await stub.RecordAuditEvent(
                agent_pb2.AuditWriteRequest(
                    workspace_id="personal", actor="local-user", action="test", resource="grpc", result="success"
                )
            )
            audit = await stub.ListAuditEvents(agent_pb2.ListConversationsRequest(workspace_id="personal"))
            assert audit.events[0].action == "test"
    finally:
        await server.stop(0)
