"""Python gRPC service; all domain writes delegate to AgentCore."""

from __future__ import annotations
import asyncio
import json
import os
import uuid
from typing import Any, AsyncIterator
import grpc
from agent.grpc_generated import agent_pb2, agent_pb2_grpc
from agent.models.runtime import ChatModelSettings
from agent.repository import ConversationBusyError, MessageConflictError
from pydantic import ValidationError


class AgentServiceServicer(agent_pb2_grpc.AgentServiceServicer):
    def __init__(self, agent_core, event_bus, observability) -> None:
        self._core = agent_core
        self._event_bus = event_bus
        self._obs = observability
        self._background_tasks: set[asyncio.Task[Any]] = set()

    def _keep_alive(self, task: asyncio.Task[Any]) -> None:
        """Retain detached work after an HTTP/gRPC client disconnects."""
        self._background_tasks.add(task)

        def release(completed: asyncio.Task[Any]) -> None:
            self._background_tasks.discard(completed)
            if completed.cancelled():
                return
            exception = completed.exception()
            if exception is not None:
                asyncio.create_task(
                    self._obs.log(
                        "error",
                        "Detached Agent task failed",
                        {"error_type": type(exception).__name__},
                    )
                )

        task.add_done_callback(release)

    async def stop_background(self, grace: float = 5) -> None:
        """Drain detached work, then interrupt it before Core resources close."""
        active = set(self._background_tasks)
        if active:
            _, pending = await asyncio.wait(active, timeout=max(grace, 0))
            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
        await self._core.reconcile_interrupted_tasks()

    @staticmethod
    def _conversation(item: dict[str, Any]) -> agent_pb2.Conversation:
        return agent_pb2.Conversation(
            id=item["id"],
            workspace_id=item["workspace_id"],
            title=item["title"],
            model_id=item["model_id"],
            permission_mode=item["permission_mode"],
            response_mode=item.get("response_mode", "balanced"),
            created_at=item["created_at"],
            updated_at=item["updated_at"],
            message_count=int(item.get("message_count", 0)),
            folder_id=str(item.get("folder_id") or ""),
            archived=bool(item.get("archived", False)),
            max_subagent_calls=int(item.get("max_subagent_calls", 0)),
            max_concurrent_subagents=int(item.get("max_concurrent_subagents", 1)),
            subagent_model_ids=json.loads(item.get("subagent_model_ids_json", "[]")),
        )

    @staticmethod
    def _message(item: dict[str, Any]) -> agent_pb2.Message:
        return agent_pb2.Message(**item)

    @staticmethod
    def _approval(item: dict[str, Any]) -> agent_pb2.Approval:
        arguments = item.get("arguments", {})
        scope = arguments.get("path") or arguments.get("workdir") or arguments.get("url") or "current workspace"
        return agent_pb2.Approval(
            id=item["id"],
            workspace_id=item["workspace_id"],
            conversation_id=item["conversation_id"],
            task_id=item["task_id"],
            tool_call_id=item["tool_call_id"],
            tool_name=item["tool_name"],
            arguments_json=json.dumps(arguments, ensure_ascii=False),
            resource_scope=str(scope),
            risk_level=item["risk_level"],
            status=item["status"],
            version=int(item["version"]),
            expires_at=item["expires_at"],
            note=item.get("note", ""),
            decided_at=item.get("decided_at") or "",
            allowed_scopes=["once", "task", "session"] if item.get("reuse_scope") else ["once"],
            reuse_scope_json=json.dumps(item.get("reuse_scope") or {}, ensure_ascii=False),
            authorization_scope=item.get("authorization_scope", "once"),
            authorization_expires_at=item.get("authorization_expires_at", ""),
            authorization_revoked_at=item.get("authorization_revoked_at", ""),
        )

    @staticmethod
    def _event(kind: str, payload: dict[str, Any]) -> agent_pb2.AgentEvent:
        return agent_pb2.AgentEvent(
            type=kind,
            task_id=str(payload.get("task_id", "")),
            conversation_id=str(payload.get("conversation_id", "")),
            content=str(payload.get("content", "")),
            payload_json=json.dumps(payload, ensure_ascii=False, default=str),
            event_id=str(payload.get("event_id", "")),
            sequence=int(payload.get("sequence", 0)),
            occurred_at=str(payload.get("occurred_at", "")),
        )

    @staticmethod
    def _task(item: dict[str, Any]) -> agent_pb2.Task:
        return agent_pb2.Task(
            id=item["id"],
            workspace_id=item["workspace_id"],
            conversation_id=item["conversation_id"],
            title=item["title"],
            status=item["status"],
            input_text=item.get("input_text", ""),
            last_error=item.get("last_error", ""),
            version=int(item.get("version", 1)),
            created_at=item["created_at"],
            updated_at=item["updated_at"],
            subagent_model_ids=json.loads(item.get("subagent_model_ids_json", "[]")),
        )

    async def ProcessMessage(self, request, context) -> AsyncIterator[agent_pb2.AgentEvent]:
        if not request.conversation_id:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "conversation_id is required")
            return
        try:
            await self._core.get_conversation(request.workspace_id or "personal", request.conversation_id)
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "conversation not found")
            return
        # Core checks an existing submission before Repository rejects a new
        # turn in an archived conversation. Replaying a receipt is not a write.
        queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()
        trace_id = f"trace_{uuid.uuid4().hex}"
        accepted_task_id = ""

        async def receive(kind: str, payload: dict[str, Any]) -> None:
            nonlocal accepted_task_id
            if kind == "task.started" and payload.get("trace_id") == trace_id:
                accepted_task_id = str(payload.get("task_id") or "")
            # A duplicate submission must not steal/broadcast another stream's
            # live events before returning its replay acknowledgement.
            if accepted_task_id and str(payload.get("task_id", "")) == accepted_task_id:
                await queue.put((kind, payload))

        self._event_bus.subscribe("*", receive)
        metadata = {
            "conversation_id": request.conversation_id,
            "workspace_id": request.workspace_id or "personal",
            "principal_id": request.principal_id or "local-user",
            "attachments": [{"type": a.type, "path": a.path, "url": a.url} for a in request.attachments],
            "idempotency_key": request.idempotency_key,
            "trace_id": trace_id,
        }
        task = asyncio.create_task(self._core.run(request.content, metadata))
        self._keep_alive(task)
        try:
            while not task.done() or not queue.empty():
                try:
                    kind, payload = await asyncio.wait_for(queue.get(), 0.05)
                except asyncio.TimeoutError:
                    continue
                yield self._event(kind, payload)
            result = await task
            if result.get("replayed"):
                # Transport acknowledgement, not a new durable/UI event.
                yield agent_pb2.AgentEvent(type="task.accepted", code="MESSAGE_REPLAY",
                    task_id=result["task_id"], conversation_id=result["conversation_id"],
                    payload_json=json.dumps(result))
            if error := result.get("error"):
                yield agent_pb2.AgentEvent(
                    type="error",
                    task_id=result.get("task_id", ""),
                    conversation_id=result.get("conversation_id", ""),
                    code=result.get("error_code", "AGENT_ERROR"),
                    message=error,
                    retryable=bool(result.get("retryable")),
                    payload_json=json.dumps(result),
                )
        except MessageConflictError as exc:
            await context.abort(grpc.StatusCode.ALREADY_EXISTS, str(exc))
        except ConversationBusyError as exc:
            await context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(exc))
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "conversation not found")
        except ValueError as exc:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        finally:
            self._event_bus.unsubscribe("*", receive)
            # Client disconnect is not task cancellation. The durable task keeps
            # running and its events remain available through ListTaskEvents.

    async def CreateConversation(self, request, context):
        try:
            item = await self._core.create_conversation(
                request.workspace_id or "personal",
                request.title,
                request.model_id,
                request.permission_mode or None,
                request.response_mode or "balanced",
                request.folder_id,
                max_subagent_calls=request.max_subagent_calls if request.HasField("max_subagent_calls") else 0,
                subagent_model_ids=list(request.subagent_model_ids),
                max_concurrent_subagents=(request.max_concurrent_subagents
                    if request.HasField("max_concurrent_subagents") else 1),
            )
        except (KeyError, ValueError) as exc:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        return self._conversation(item)

    async def GetConversation(self, request, context):
        try:
            return self._conversation(
                await self._core.get_conversation(request.workspace_id or "personal", request.conversation_id)
            )
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "conversation not found")

    async def ListConversations(self, request, context):
        return agent_pb2.ConversationList(
            conversations=[
                self._conversation(i) for i in await self._core.list_conversations(request.workspace_id or "personal")
            ]
        )

    async def GetConversationSnapshot(self, request, context):
        try:
            item = await self._core.repository.conversation_snapshot(
                request.workspace_id or "personal", request.conversation_id,
            )
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "conversation not found")
        return agent_pb2.ConversationSnapshot(
            messages=[agent_pb2.Message(**row) for row in item["messages"]],
            tasks=[self._task(row) for row in item["tasks"]],
            approvals=[self._approval(row) for row in item["approvals"]],
            questions=[agent_pb2.Question(**{key: row[key] for key in
                ("id", "workspace_id", "conversation_id", "task_id", "tool_call_id", "title", "status",
                 "version", "answer", "options_json", "created_at")}) for row in item["questions"]],
            last_sequence=item["last_sequence"], truncated=item["truncated"],
        )

    async def DeleteConversation(self, request, context):
        try:
            await self._core.delete_conversation(request.workspace_id or "personal", request.conversation_id)
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "conversation not found")
        except ConversationBusyError as exc:
            await context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(exc))
        return agent_pb2.Empty()

    async def UpdateConversationPermission(self, request, context):
        try:
            item = await self._core.update_conversation_permission(
                request.workspace_id or "personal", request.conversation_id, request.permission_mode
            )
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "conversation not found")
        except ValueError as exc:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        return self._conversation(item)

    async def UpdateConversationSettings(self, request, context):
        try:
            item = await self._core.update_conversation_settings(
                request.workspace_id or "personal",
                request.conversation_id,
                model_id=request.model_id if request.HasField("model_id") else None,
                response_mode=request.response_mode if request.HasField("response_mode") else None,
                permission_mode=request.permission_mode if request.HasField("permission_mode") else None,
                title=request.title if request.HasField("title") else None,
                folder_id=request.folder_id if request.HasField("folder_id") else None,
                archived=request.archived if request.HasField("archived") else None,
                max_subagent_calls=request.max_subagent_calls if request.HasField("max_subagent_calls") else None,
                subagent_model_ids=list(request.subagent_models.model_ids) if request.HasField("subagent_models") else None,
                max_concurrent_subagents=(request.max_concurrent_subagents
                    if request.HasField("max_concurrent_subagents") else None),
            )
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "conversation or model not found")
        except ConversationBusyError as exc:
            await context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(exc))
        except ValueError as exc:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        return self._conversation(item)

    async def ListWorkspaceFolders(self, request, context):
        folders = await self._core.list_workspace_folders(request.workspace_id or "personal")
        return agent_pb2.WorkspaceFolderList(folders=[agent_pb2.WorkspaceFolder(**item) for item in folders])

    async def GetWorkspaceFolder(self, request, context):
        try:
            item = await self._core.get_workspace_folder(request.workspace_id or "personal", request.folder_id)
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "工作区不存在。")
        except (ValueError, OSError) as exc:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        return agent_pb2.WorkspaceFolder(**item)

    async def CreateWorkspaceFolder(self, request, context):
        try:
            item = await self._core.create_workspace_folder(
                request.workspace_id or "personal", request.root_path, request.name,
            )
        except (ValueError, OSError) as exc:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        return agent_pb2.WorkspaceFolder(**item)

    async def ListMessages(self, request, context):
        try:
            items = await self._core.list_messages(request.conversation_id, request.workspace_id or "personal")
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "conversation not found")
        return agent_pb2.MessageList(messages=[self._message(i) for i in items])

    async def GetTask(self, request, context):
        try:
            item = await self._core.get_task(request.workspace_id or "personal", request.task_id)
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "task not found")
        return self._task(item)

    async def ListTasks(self, request, context):
        items = await self._core.list_tasks(
            request.workspace_id or "personal", request.conversation_id, int(request.limit or 100)
        )
        return agent_pb2.TaskList(tasks=[self._task(item) for item in items])

    async def CancelTask(self, request, context):
        try:
            item = await self._core.cancel_task(request.workspace_id or "personal", request.task_id)
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "task not found")
        return self._task(item)

    async def ListTaskEvents(self, request, context):
        try:
            items = await self._core.list_task_events(
                request.workspace_id or "personal",
                request.conversation_id,
                int(request.after_sequence),
                int(request.limit or 500),
            )
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "conversation not found")
        return agent_pb2.TaskEventList(
            events=[
                agent_pb2.TaskEvent(
                    id=item["id"],
                    workspace_id=item["workspace_id"],
                    conversation_id=item["conversation_id"],
                    task_id=item["task_id"],
                    sequence=int(item["sequence"]),
                    event_type=item["event_type"],
                    payload_json=json.dumps(item.get("payload", {}), ensure_ascii=False, default=str),
                    occurred_at=item["occurred_at"],
                )
                for item in items
            ]
        )

    async def ListApprovals(self, request, context):
        items = await self._core.repository.list_approvals(
            request.workspace_id or "personal", request.conversation_id or None
        )
        return agent_pb2.ApprovalList(approvals=[self._approval(item) for item in items])

    async def GetApproval(self, request, context):
        try:
            item = await self._core.repository.get_approval(
                request.workspace_id or "personal", request.approval_id,
            )
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "approval not found")
        return self._approval(item)

    async def GetTaskInspection(self, request, context):
        try:
            item = await self._core.repository.inspect_task(
                request.workspace_id or "personal", request.task_id,
            )
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "task not found")
        return agent_pb2.TaskInspection(
            task=self._task(item["task"]),
            tool_calls=[agent_pb2.ToolCall(**{key: value if value is not None else ""
                                            for key, value in row.items()})
                        for row in item["tool_calls"]],
            approvals=[self._approval(row) for row in item["approvals"]],
            projection_json=json.dumps(item["projection"], ensure_ascii=False),
            last_sequence=item["last_sequence"],
        )

    async def ListApprovalAuthorizations(self, request, context):
        if await self._core.repository.check_workspace_access(request.workspace_id, request.principal_id) != "owner":
            await context.abort(grpc.StatusCode.PERMISSION_DENIED, "workspace owner required")
            return
        if not request.conversation_id:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "conversation_id is required")
            return
        items = await self._core.repository.list_authorizations(
            request.workspace_id, request.conversation_id, request.principal_id,
        )
        return agent_pb2.ApprovalAuthorizationList(json=json.dumps(items, ensure_ascii=False))

    async def RevokeApprovalAuthorization(self, request, context):
        if await self._core.repository.check_workspace_access(request.workspace_id, request.principal_id) != "owner":
            await context.abort(grpc.StatusCode.PERMISSION_DENIED, "workspace owner required")
            return
        try:
            await self._core.repository.revoke_authorization(request.workspace_id, request.approval_id, request.principal_id)
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "authorization not found")
        except PermissionError as exc:
            await context.abort(grpc.StatusCode.PERMISSION_DENIED, str(exc))
        except ValueError as exc:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        return agent_pb2.Empty()

    async def ListQuestions(self, request, context):
        items = await self._core.repository.list_questions(
            request.workspace_id or "personal", request.conversation_id,
        )
        return agent_pb2.QuestionList(questions=[agent_pb2.Question(**{
            key: value for key, value in item.items() if key != "principal_id"
        }) for item in items])

    async def ListJobs(self, request, context):
        items = await self._core.list_jobs(request.workspace_id or "personal", request.conversation_id)
        return agent_pb2.JobList(jobs=[agent_pb2.Job(**item) for item in items])

    async def StopJob(self, request, context):
        try:
            await self._core.stop_job(request.workspace_id or "personal", request.job_id,
                                      request.principal_id or "local-user")
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "process not found")
        except ValueError as exc:
            await context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(exc))
        return agent_pb2.Empty()

    async def WriteJobInput(self, request, context):
        try:
            await self._core.write_job_input(request.workspace_id or "personal", request.job_id,
                                             request.principal_id or "local-user", request.text, request.eof)
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "process not found")
        except ValueError as exc:
            await context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(exc))
        return agent_pb2.Empty()

    @staticmethod
    def _task_input(item):
        return agent_pb2.TaskInput(**{key: item[key] for key in ("id", "task_id", "content", "status", "created_at")})

    async def ListTaskInputs(self, request, context):
        try:
            items = await self._core.repository.task_inputs(request.workspace_id or "personal", request.task_id)
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "task not found")
        return agent_pb2.TaskInputList(inputs=[self._task_input(item) for item in items])

    async def SubmitTaskInput(self, request, context):
        runtime = self._core._langgraph_runtime
        if runtime is None:
            await context.abort(grpc.StatusCode.UNAVAILABLE, "Agent Core runtime is not ready")
        try:
            item = await runtime.submit_input(request.workspace_id or "personal", request.task_id,
                                              request.content, request.idempotency_key)
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "task not found")
        except ValueError as exc:
            await context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(exc))
        return self._task_input(item)

    async def AnswerQuestion(self, request, context):
        workspace_id = request.workspace_id or "personal"
        try:
            question = await self._core.repository.get_question(workspace_id, request.question_id)
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "question not found")
            return
        operation = self._core.answer_question(
            workspace_id, request.question_id, request.principal_id or "local-user", request.answer, request.version,
        )
        async for event in self._stream_interaction(question, operation, context):
            yield event

    async def DecideApproval(self, request, context) -> AsyncIterator[agent_pb2.AgentEvent]:
        workspace_id = request.workspace_id or "personal"
        try:
            pending = await self._core.repository.get_approval(workspace_id, request.approval_id)
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "approval not found")
            return
        operation = self._core.decide_approval(
            workspace_id, request.approval_id, request.principal_id or "local-user",
            request.decision, int(request.version), request.note, request.scope or "once",
        )
        async for event in self._stream_interaction(pending, operation, context):
            yield event

    async def ResumeTask(self, request, context) -> AsyncIterator[agent_pb2.AgentEvent]:
        workspace_id = request.workspace_id or "personal"
        if await self._core.repository.check_workspace_access(workspace_id, request.principal_id) != "owner":
            await context.abort(grpc.StatusCode.PERMISSION_DENIED, "workspace owner required")
            return
        if request.version < 1:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "a positive task version is required")
            return
        try:
            task = await self._core.get_task(workspace_id, request.task_id)
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "task not found")
            return
        trace_id = f"resume_{uuid.uuid4().hex}"
        operation = self._core.resume_task(
            workspace_id, request.task_id, request.principal_id, request.version, trace_id,
        )
        async for event in self._stream_interaction(
            {"conversation_id": task["conversation_id"], "task_id": request.task_id},
            operation, context, resume_trace_id=trace_id,
        ):
            yield event

    async def _stream_interaction(self, pending, operation, context, *, resume_trace_id: str = ""):
        """HTTP/gRPC subscription glue; the Core owns execution and persistence."""
        queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()
        admitted = not resume_trace_id

        async def receive(kind: str, payload: dict[str, Any]) -> None:
            nonlocal admitted
            if (
                str(payload.get("conversation_id", "")) == pending["conversation_id"]
                and str(payload.get("task_id", "")) == pending["task_id"]
            ):
                # A rejected duplicate resume must not stream someone else's
                # active run and be mistaken for an accepted HTTP request.
                if not admitted:
                    if kind != "task.resumed" or payload.get("trace_id") != resume_trace_id:
                        return
                    admitted = True
                await queue.put((kind, payload))

        self._event_bus.subscribe("*", receive)
        task = asyncio.create_task(operation)
        self._keep_alive(task)
        try:
            while not task.done() or not queue.empty():
                try:
                    kind, payload = await asyncio.wait_for(queue.get(), 0.05)
                except asyncio.TimeoutError:
                    continue
                yield self._event(kind, payload)
            try:
                await task
            except (ValueError, PermissionError) as exc:
                await context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(exc))
            except NotImplementedError as exc:
                await context.abort(grpc.StatusCode.UNIMPLEMENTED, str(exc))
            except KeyError:
                await context.abort(grpc.StatusCode.NOT_FOUND, "interaction not found")
            except Exception as exc:
                yield agent_pb2.AgentEvent(
                    type="error",
                    conversation_id=pending["conversation_id"],
                    task_id=pending["task_id"],
                    code="AGENT_ERROR",
                    message=str(exc),
                    payload_json=json.dumps({"message": str(exc)}),
                )
        finally:
            self._event_bus.unsubscribe("*", receive)
            # Execution outlives the caller's stream; Core shutdown owns cleanup.

    async def Health(self, request, context):
        native = self._core._initialized and self._core._langgraph_runtime is not None
        return agent_pb2.HealthResponse(status="serving" if native else "not_serving", version="0.1.0", capabilities={
            "approval_note": True, "approval_detail": True, "task_inspection": True,
            "structured_questions": native, "task_input": native, "structured_plan": native,
            "task_resume": native,
            "subagents": native,
            "subagent_model_selection": native,
            "file_change_events": True, "context_estimate": native,
            "model_context_percentage": False, "session_approval": native, "task_approval": native,
            "approval_authorization_revocation": native,
            "permission_boundary_v2": native, "auto_review": False,
            "turn_rollback": False, "automatic_memory_events": False,
            "process_list": True, "process_stop": True, "process_input": True, "live_process_logs": hasattr(os, "pread"),
        })

    async def CheckWorkspaceAccess(self, request, context):
        role = await self._core.repository.check_workspace_access(request.workspace_id, request.principal_id)
        return agent_pb2.WorkspaceAccessResponse(allowed=role is not None, role=role or "")

    async def ListAuditEvents(self, request, context):
        items = await self._core.repository.list_audit_events(request.workspace_id or "personal")
        return agent_pb2.AuditEventList(events=[agent_pb2.AuditEvent(**item) for item in items])

    async def RecordAuditEvent(self, request, context):
        await self._core.repository.record_audit(
            request.workspace_id, request.actor, request.action, request.resource, request.result, {}
        )
        return agent_pb2.Empty()

    @staticmethod
    def _chat_model_settings(item: ChatModelSettings) -> agent_pb2.ChatModelSettings:
        return agent_pb2.ChatModelSettings(
            id=item.id,
            name=item.name,
            provider=item.provider,
            model=item.model,
            base_url=item.base_url,
            temperature=item.temperature,
            max_tokens=item.max_tokens,
            timeout_seconds=item.timeout_seconds,
            is_default=item.is_default,
        )

    @staticmethod
    def _chat_model_settings_value(item) -> ChatModelSettings:
        return ChatModelSettings(
            id=item.id,
            name=item.name,
            provider=item.provider,
            model=item.model,
            base_url=item.base_url,
            temperature=item.temperature,
            max_tokens=item.max_tokens,
            timeout_seconds=item.timeout_seconds,
            is_default=item.is_default,
        )

    async def GetChatModelSettings(self, request, context):
        return self._chat_model_settings(await self._core.get_chat_model_settings(request.workspace_id or "personal"))

    async def UpdateChatModelSettings(self, request, context):
        try:
            item = await self._core.update_chat_model_settings(
                request.workspace_id or "personal", self._chat_model_settings_value(request.settings)
            )
        except ValueError as exc:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        return self._chat_model_settings(item)

    async def ListChatModels(self, request, context):
        items, default_id = await self._core.list_chat_models(request.workspace_id or "personal")
        return agent_pb2.ChatModelList(
            models=[self._chat_model_settings(item) for item in items], default_model_id=default_id
        )

    async def UpsertChatModel(self, request, context):
        try:
            item = await self._core.upsert_chat_model(
                request.workspace_id or "personal", self._chat_model_settings_value(request.settings)
            )
        except ValueError as exc:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        return self._chat_model_settings(item)

    async def DeleteChatModel(self, request, context):
        try:
            await self._core.delete_chat_model(request.workspace_id or "personal", request.model_id)
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "model profile not found")
        return agent_pb2.Empty()

    async def SetDefaultChatModel(self, request, context):
        try:
            items, default_id = await self._core.set_default_chat_model(
                request.workspace_id or "personal", request.model_id
            )
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "model profile not found")
        return agent_pb2.ChatModelList(
            models=[self._chat_model_settings(item) for item in items], default_model_id=default_id
        )

    async def ValidateChatModel(self, request, context):
        try:
            await self._core.validate_chat_model(self._chat_model_settings_value(request.settings), request.api_key)
            return agent_pb2.ModelValidationResponse(
                ok=True, message="connection successful", model=request.settings.model
            )
        except Exception as exc:
            return agent_pb2.ModelValidationResponse(ok=False, message=str(exc), model=request.settings.model)

    async def SetChatModelCredential(self, request, context):
        await self._core.set_chat_model_credential(
            request.workspace_id or "personal", request.provider, request.api_key, request.model_id
        )
        return agent_pb2.Empty()

    async def SetToolCredential(self, request, context):
        try:
            await self._core.set_tool_credential(request.workspace_id or "personal", request.service, request.api_key)
        except ValueError as exc:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        return agent_pb2.Empty()

    async def GetUserPreferences(self, request, context):
        item = await self._core.get_user_preferences(
            request.workspace_id or "personal", request.subject_user_id or "local-user"
        )
        return agent_pb2.UserPreferences(**item)

    async def UpdateUserPreferences(self, request, context):
        try:
            item = await self._core.update_user_preferences(
                request.workspace_id or "personal",
                request.subject_user_id or "local-user",
                request.preferences.assistant_name,
            )
        except ValueError as exc:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        return agent_pb2.UserPreferences(**item)

    async def GetPermissionSettings(self, request, context):
        item = await self._core.get_permission_settings(request.workspace_id or "personal")
        return agent_pb2.PermissionSettings(default_mode=item["default_mode"])

    async def UpdatePermissionSettings(self, request, context):
        try:
            item = await self._core.update_permission_settings(
                request.workspace_id or "personal", request.settings.default_mode
            )
        except ValueError as exc:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        return agent_pb2.PermissionSettings(default_mode=item["default_mode"])

    async def GetToolSettings(self, request, context):
        item = await self._core.get_tool_settings(request.workspace_id or "personal")
        return agent_pb2.ToolSettings(tools=[agent_pb2.ToolSetting(**tool) for tool in item["tools"]])

    async def UpdateToolSettings(self, request, context):
        workspace_id = request.workspace_id or "personal"
        try:
            item = await self._core.update_tool_settings(workspace_id, dict(request.enabled))
        except ValueError as exc:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        await self._core.repository.record_audit(
            workspace_id, "local-user", "tools.selection.updated", workspace_id, "success",
            {"enabled": dict(request.enabled)},
        )
        return agent_pb2.ToolSettings(tools=[agent_pb2.ToolSetting(**tool) for tool in item["tools"]])

    @staticmethod
    def _memory(item: dict[str, Any]) -> agent_pb2.Memory:
        return agent_pb2.Memory(
            id=item["id"],
            workspace_id=item["workspace_id"],
            subject_user_id=item["subject_user_id"],
            category=item["category"],
            content=item["content"],
            source_type=item["source_type"],
            source_id=item["source_id"],
            confidence=float(item["confidence"]),
            created_at=item["created_at"],
            updated_at=item["updated_at"],
        )

    async def ListMemories(self, request, context):
        try:
            items = await self._core.list_memories(
                request.workspace_id or "personal",
                request.subject_user_id or "local-user",
                request.query,
                int(request.limit or 100),
            )
        except ValueError as exc:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        return agent_pb2.MemoryList(memories=[self._memory(item) for item in items])

    async def UpsertMemory(self, request, context):
        try:
            item = await self._core.upsert_memory(
                request.workspace_id or "personal",
                request.subject_user_id or "local-user",
                memory_id=request.memory.id,
                category=request.memory.category,
                content=request.memory.content,
                confidence=float(request.memory.confidence),
            )
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "memory not found")
        except ValueError as exc:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        return self._memory(item)

    async def DeleteMemory(self, request, context):
        try:
            await self._core.delete_memory(
                request.workspace_id or "personal",
                request.subject_user_id or "local-user",
                request.memory_id,
            )
        except KeyError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "memory not found")
        return agent_pb2.Empty()

    async def GetWorkspaceDataSummary(self, request, context):
        return agent_pb2.WorkspaceDataSummary(
            **await self._core.get_workspace_data_summary(request.workspace_id or "personal")
        )

    async def ListMCPServers(self, request, context):
        items = await self._core.list_mcp_servers()
        return agent_pb2.MCPServerList(servers=[agent_pb2.MCPServer(**item) for item in items])

    async def _extension_response(self, operation, context):
        try:
            return agent_pb2.ExtensionSettings(json=json.dumps(await operation, ensure_ascii=False))
        except PermissionError as exc:
            await context.abort(grpc.StatusCode.PERMISSION_DENIED, str(exc))
        except ConversationBusyError as exc:
            await context.abort(grpc.StatusCode.ABORTED, str(exc))
        except ValidationError as exc:
            # Pydantic's default rendering includes submitted input (possibly
            # secrets misplaced in config). Expose field locations/messages only.
            detail = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}"
                               for e in exc.errors(include_input=False, include_url=False))
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, detail)
        except ValueError as exc:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        except Exception:
            await context.abort(grpc.StatusCode.UNAVAILABLE, "扩展应用失败，请查看当前状态后重新连接。")

    async def GetExtensions(self, request, context):
        return await self._extension_response(self._core.get_extensions(request.workspace_id), context)

    async def UpdateExtensions(self, request, context):
        async def update():
            if len(request.config_json.encode()) > 2 * 1024 * 1024:
                raise ValueError("Extension configuration exceeds 2 MiB")
            return await self._core.update_extensions(request.workspace_id, json.loads(request.config_json))
        return await self._extension_response(update(), context)

    async def ReloadExtensions(self, request, context):
        async def reload():
            if len(request.credentials_json.encode()) > 1024 * 1024:
                raise ValueError("Extension credentials exceed request limit")
            credentials = json.loads(request.credentials_json or "{}")
            if not isinstance(credentials, dict):
                raise ValueError("Invalid extension credentials")
            return await self._core.reload_extensions(
                request.workspace_id, request.revision, credentials, restore_only=request.restore_only,
            )
        return await self._extension_response(reload(), context)

    async def ListSkills(self, request, context):
        items = await self._core.list_skills()
        return agent_pb2.SkillList(
            skills=[
                agent_pb2.Skill(
                    name=item["name"],
                    version=item["version"],
                    description=item["description"],
                    kind=item["kind"],
                    source_path=item["source_path"],
                    parameters_schema_json=json.dumps(item.get("parameters_schema", {}), ensure_ascii=False),
                )
                for item in items
            ]
        )
