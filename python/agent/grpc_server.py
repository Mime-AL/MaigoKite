"""gRPC Server implementation for AgentService.

This module provides the gRPC server that listens for incoming requests
from the Go API Gateway and delegates to AgentCore for business logic.

Architecture:
    Go Gateway (AgentClient) --[gRPC]--> Python Agent Core (AgentServiceServicer)
                                              |
                                              v
                                         AgentCore.run()
                                              |
                                              v
                                         EventBus --> stream responses back
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator

import grpc

# Import generated stubs (run `python -m scripts.generate_proto` first)
from agent.grpc_generated import agent_pb2
from agent.grpc_generated import agent_pb2_grpc


class AgentServiceServicer(agent_pb2_grpc.AgentServiceServicer):
    """Implements the AgentService gRPC service.

    Delegates to AgentCore for agent execution, TaskManager for session handling,
    MemorySystem for memory operations, and Observability for monitoring.
    """

    def __init__(self, agent_core, event_bus, observability):
        """
        Args:
            agent_core: AgentCore instance for executing agent loops.
            event_bus: EventBus instance for subscribing to agent events.
            observability: Observability instance for logging/tracing.
        """
        self._core = agent_core
        self._event_bus = event_bus
        self._obs = observability
        # Track active session states
        self._sessions: dict[str, dict] = {}
        # Track active ProcessMessage streams for cancellation
        self._active_streams: dict[str, asyncio.Event] = {}

    # ------------------------------------------------------------------
    # Helper methods: proto <-> domain conversions
    # ------------------------------------------------------------------

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _to_session_response(
        self, sid: str, title: str, mode: str, msg_count: int
    ) -> agent_pb2.SessionResponse:
        return agent_pb2.SessionResponse(
            id=sid,
            title=title,
            created_at=self._now_iso(),
            updated_at=self._now_iso(),
            permission_mode=mode,
            message_count=msg_count,
        )

    def _to_error_info(
        self, level: str, code: str, message: str, suggestion: str = "", retryable: bool = False
    ) -> agent_pb2.ErrorInfo:
        return agent_pb2.ErrorInfo(
            level=level,
            code=code,
            message=message,
            suggestion=suggestion,
            retryable=retryable,
        )

    def _to_agent_response_error(
        self,
        level: str,
        code: str,
        message: str,
        suggestion: str = "",
        retryable: bool = False,
    ) -> agent_pb2.AgentResponse:
        return agent_pb2.AgentResponse(
            type="error",
            error=self._to_error_info(level, code, message, suggestion, retryable),
        )

    # ------------------------------------------------------------------
    # ProcessMessage — streaming RPC (main agent loop)
    # ------------------------------------------------------------------

    async def ProcessMessage(
        self,
        request: agent_pb2.ProcessRequest,
        context: grpc.ServicerContext,
    ) -> AsyncIterator[agent_pb2.AgentResponse]:
        """Handle a user message and stream agent responses.

        This is the core RPC that triggers the agent execution loop.
        It subscribes to EventBus events and yields AgentResponse messages.
        """
        session_id = request.session_id or str(uuid.uuid4())[:8]
        trace_id = str(uuid.uuid4())

        # Register active stream for cancellation tracking
        cancel_event = asyncio.Event()
        self._active_streams[trace_id] = cancel_event

        try:
            # Signal step_start
            yield agent_pb2.AgentResponse(
                type="step_start",
                step=agent_pb2.StepData(step_name="session.init", status="running"),
            )

            # Subscribe to event bus for this trace
            received_events: list[dict] = []

            async def on_event(event_type: str, payload: dict):
                received_events.append({"type": event_type, "payload": payload})
                # Yield response based on event type
                if event_type == "tool_call":
                    tool_name = payload.get("tool_name", "unknown")
                    yield agent_pb2.AgentResponse(
                        type="tool_call",
                        tool_call=agent_pb2.ToolCallData(
                            tool_name=tool_name,
                            status="running",
                        ),
                    )
                elif event_type == "tool_result":
                    tool_name = payload.get("tool_name", "unknown")
                    summary = payload.get("summary", "")
                    yield agent_pb2.AgentResponse(
                        type="tool_call",
                        tool_call=agent_pb2.ToolCallData(
                            tool_name=tool_name,
                            result_summary=summary,
                            status="completed",
                        ),
                    )
                elif event_type == "llm_stream":
                    content = payload.get("content", "")
                    yield agent_pb2.AgentResponse(
                        type="message_chunk",
                        chunk=agent_pb2.MessageChunk(content=content),
                    )
                elif event_type == "step_complete":
                    step_name = payload.get("step_name", "unknown")
                    status = payload.get("status", "completed")
                    yield agent_pb2.AgentResponse(
                        type="step_complete",
                        step=agent_pb2.StepData(
                            step_name=step_name,
                            status=status,
                        ),
                    )

            # NOTE: Since EventBus.subscribe expects async callbacks,
            # we use a simpler approach: poll the event bus or use
            # the agent core's built-in streaming capability.

            # For Phase 1, we invoke the agent core directly and
            # yield responses based on its return structure.

            # Run the agent core in a background task
            async def run_agent():
                try:
                    result = await self._core.run(
                        prompt=request.content,
                        metadata={
                            "session_id": session_id,
                            "trace_id": trace_id,
                            "attachments": [
                                agent_pb2.Attachment(
                                    type=a.type,
                                    path=a.path,
                                    url=a.url,
                                ).__dict__
                                for a in request.attachments
                            ],
                        },
                    )
                    return result
                except Exception as e:
                    return {"error": str(e), "type": "exception"}

            # Execute agent and yield results
            agent_task = asyncio.create_task(run_agent())

            # Stream progress via event bus subscription
            async def listen_events():
                """Listen to EventBus and yield responses."""
                event_queue: asyncio.Queue[dict] = asyncio.Queue()

                async def on_publish(event_type: str, payload: dict):
                    await event_queue.put({"type": event_type, "payload": payload})

                self._event_bus.subscribe("*", on_publish)
                try:
                    while not agent_task.done():
                        try:
                            event = await asyncio.wait_for(
                                event_queue.get(), timeout=0.1
                            )
                            yield event
                        except asyncio.TimeoutError:
                            continue

                finally:
                    self._event_bus.unsubscribe("*", on_publish)

            # Run event listener and agent concurrently
            async def collect_and_yield():
                """Collect events from both agent execution and event bus."""
                # First, yield session init
                yield agent_pb2.AgentResponse(
                    type="step_start",
                    step=agent_pb2.StepData(step_name="session.init", status="running"),
                )

                # Run agent in background, collect events
                event_task = asyncio.create_task(
                    listen_events().__anext__()
                    if hasattr(listen_events(), "__anext__")
                    else asyncio.sleep(0)
                )

                try:
                    result = await agent_task
                except Exception as e:
                    yield self._to_agent_response_error(
                        level="P1",
                        code="AGENT_ERROR",
                        message=str(e),
                        retryable=True,
                    )
                    return

                # Yield completion
                if "error" in result:
                    yield self._to_agent_response_error(
                        level="P1",
                        code=result.get("error_code", "RUNTIME_ERROR"),
                        message=result["error"],
                        retryable=result.get("retryable", True),
                    )
                else:
                    yield agent_pb2.AgentResponse(
                        type="step_complete",
                        step=agent_pb2.StepData(
                            step_name="agent.complete", status="completed",
                        ),
                    )
                    # Yield final response
                    if "response" in result:
                        yield agent_pb2.AgentResponse(
                            type="message_chunk",
                            chunk=agent_pb2.MessageChunk(content=result["response"]),
                        )

            async for response in collect_and_yield():
                if context.is_cancelled():
                    break
                yield response

        finally:
            # Clean up
            self._active_streams.pop(trace_id, None)

    # ------------------------------------------------------------------
    # Session management RPCs
    # ------------------------------------------------------------------

    async def CreateSession(
        self,
        request: agent_pb2.SessionRequest,
        context: grpc.ServicerContext,
    ) -> agent_pb2.SessionResponse:
        """Create a new conversation session."""
        session_id = request.id or str(uuid.uuid4())[:8]
        title = request.title or "Untitled"
        model_id = request.model_id or ""
        perm_mode = request.permission_mode or "auto"

        self._sessions[session_id] = {
            "id": session_id,
            "title": title,
            "model_id": model_id,
            "permission_mode": perm_mode,
            "created_at": self._now_iso(),
            "updated_at": self._now_iso(),
            "messages": [],
        }

        await self._obs.log("info", f"Session created: {session_id}")
        return self._to_session_response(session_id, title, perm_mode, 0)

    async def SwitchSession(
        self,
        request: agent_pb2.SessionRequest,
        context: grpc.ServicerContext,
    ) -> agent_pb2.SessionResponse:
        """Switch to an existing session."""
        session_id = request.id
        if session_id not in self._sessions:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Session {session_id} not found")
            return agent_pb2.SessionResponse()

        session = self._sessions[session_id]
        session["updated_at"] = self._now_iso()
        return self._to_session_response(
            session["id"],
            session["title"],
            session["permission_mode"],
            len(session.get("messages", [])),
        )

    async def ListSessions(
        self,
        request: agent_pb2.Empty,
        context: grpc.ServicerContext,
    ) -> agent_pb2.SessionListResponse:
        """List all sessions."""
        sessions = []
        for sid, sdata in self._sessions.items():
            sessions.append(
                self._to_session_response(
                    sdata["id"],
                    sdata["title"],
                    sdata["permission_mode"],
                    len(sdata.get("messages", [])),
                )
            )
        return agent_pb2.SessionListResponse(sessions=sessions)

    async def DeleteSession(
        self,
        request: agent_pb2.SessionRequest,
        context: grpc.ServicerContext,
    ) -> agent_pb2.SessionResponse:
        """Delete a session."""
        session_id = request.id
        if session_id not in self._sessions:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Session {session_id} not found")
            return agent_pb2.SessionResponse()

        deleted = self._sessions.pop(session_id)
        await self._obs.log("info", f"Session deleted: {session_id}")
        return self._to_session_response(
            deleted["id"], deleted["title"], deleted["permission_mode"], 0
        )

    # ------------------------------------------------------------------
    # Memory management RPCs
    # ------------------------------------------------------------------

    async def SearchMemories(
        self,
        request: agent_pb2.MemorySearchRequest,
        context: grpc.ServicerContext,
    ) -> agent_pb2.MemorySearchResponse:
        """Search memories using vector or keyword matching."""
        # Delegate to AgentCore's memory system
        # For Phase 1, return placeholder results
        results = []
        if request.use_vector_search:
            # Would call MemorySystem.vector_search() here
            pass

        return agent_pb2.MemorySearchResponse(results=results)

    async def UpdateMemory(
        self,
        request: agent_pb2.MemoryUpdateRequest,
        context: grpc.ServicerContext,
    ) -> agent_pb2.MemoryUpdateResponse:
        """Update or create a memory entry."""
        # Delegate to MemorySystem.update()
        return agent_pb2.MemoryUpdateResponse(
            id=request.id or str(uuid.uuid4())[:8],
            updated_at=self._now_iso(),
        )

    # ------------------------------------------------------------------
    # Model routing RPC
    # ------------------------------------------------------------------

    async def RouteModel(
        self,
        request: agent_pb2.ModelRouteRequest,
        context: grpc.ServicerContext,
    ) -> agent_pb2.ModelRouteResponse:
        """Route a task to the best available model."""
        # Delegate to ModelProvider routing logic
        task_type = request.task_type or "general"
        complexity = request.complexity or "medium"
        prefer_local = request.prefer_local

        # Simple routing logic for Phase 1
        if prefer_local:
            model = "qwen2.5:latest"
            provider = "ollama"
        elif complexity == "high":
            model = "gpt-4o"
            provider = "openai"
        else:
            model = "claude-sonnet-4-0"
            provider = "anthropic"

        return agent_pb2.ModelRouteResponse(
            selected_model=model,
            provider=provider,
            reason=f"Selected based on task_type={task_type}, complexity={complexity}, prefer_local={prefer_local}",
            fallback_models=["qwen2.5:14b", "gemma:7b"],
            fallback_providers=["ollama", "ollama"],
        )

    # ------------------------------------------------------------------
    # Permission check RPC
    # ------------------------------------------------------------------

    async def CheckPermission(
        self,
        request: agent_pb2.PermissionCheckRequest,
        context: grpc.ServicerContext,
    ) -> agent_pb2.PermissionCheckResponse:
        """Check if an operation is allowed under current permission mode."""
        # Delegate to PermissionManager
        operation = request.operation
        resource = request.resource

        # Simple permission matrix for Phase 1
        permission_map = {
            "file_read": "L1",
            "file_write": "L4",
            "file_edit": "L4",
            "bash": "L3",
            "web_search": "L3",
            "web_fetch": "L3",
            "glob": "L1",
            "grep": "L1",
            "image_generate": "L4",
        }

        required_level = permission_map.get(operation, "L5")

        # In Phase 1, auto mode allows all; manual mode requires confirmation
        allowed = True  # Simplified; would check current permission mode

        return agent_pb2.PermissionCheckResponse(
            allowed=allowed,
            reason=f"Operation '{operation}' requires level {required_level}",
            required_level=required_level,
        )
