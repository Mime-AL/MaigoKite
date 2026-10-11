"""gRPC server runner for AgentService.

Starts the gRPC server that listens for incoming connections from
the Go API Gateway. Integrates with AgentCore lifecycle.
"""

from __future__ import annotations

import logging
from concurrent import futures
from typing import Optional

import grpc

from agent.grpc_generated import agent_pb2_grpc
from agent.grpc_server import AgentServiceServicer
from agent.observability import Observability

logger = logging.getLogger(__name__)


class GRPCRunner:
    """Manages the gRPC server lifecycle.

    Starts, stops, and monitors the gRPC server process.
    Connects the AgentServiceServicer to AgentCore instances.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 50051,
        max_workers: int = 10,
    ):
        self._host = host
        self._port = port
        self._max_workers = max_workers
        self._server: Optional[grpc.aio.Server] = None
        self._servicer: Optional[AgentServiceServicer] = None
        self._logger = logging.getLogger("grpc_runner")

    def inject_servicer(self, servicer: AgentServiceServicer) -> None:
        """Inject the servicer with references to AgentCore, EventBus, etc."""
        self._servicer = servicer

    def bind(self) -> None:
        """Reserve the endpoint before Core opens or recovers its database."""
        if self._server is not None:
            return
        self._server = grpc.aio.server(
            futures.ThreadPoolExecutor(max_workers=self._max_workers),
            options=[
                ("grpc.so_reuseport", 0),
                ("grpc.max_send_message_length", 50 * 1024 * 1024),  # 50MB
                ("grpc.max_receive_message_length", 50 * 1024 * 1024),  # 50MB
                ("grpc.keepalive_time_ms", 10000),
                ("grpc.keepalive_timeout_ms", 5000),
                ("grpc.keepalive_permit_without_calls", 1),
            ],
        )

        if self._servicer is None:
            raise RuntimeError("AgentServiceServicer not injected. Call inject_servicer() first.")

        agent_pb2_grpc.add_AgentServiceServicer_to_server(self._servicer, self._server)

        address = f"{self._host}:{self._port}"
        if self._server.add_insecure_port(address) == 0:
            raise RuntimeError(f"failed to bind gRPC server to {address}")

    async def start(self) -> None:
        """Start accepting requests only after Core initialization finishes."""
        self.bind()
        assert self._server is not None
        await self._server.start()
        self._logger.info("gRPC server started on %s:%d", self._host, self._port)

    async def stop(self, grace: int = 5) -> None:
        """Stop the gRPC server gracefully."""
        if self._server is None:
            return
        self._logger.info("Stopping gRPC server (grace=%ds)...", grace)
        await self._server.stop(grace=grace)
        if self._servicer is not None:
            await self._servicer.stop_background(grace)
        self._logger.info("gRPC server stopped.")

    async def wait_for_rpcs(self) -> None:
        """Block until the server is shut down."""
        if self._server is None:
            raise RuntimeError("Server not started. Call start() first.")
        await self._server.wait_for_termination()


def create_server(
    agent_core,
    event_bus,
    observability: Observability,
    host: str = "127.0.0.1",
    port: int = 50051,
) -> GRPCRunner:
    """Create an unbound server; the CLI owns binding, initialization and stop.

    Args:
        agent_core: AgentCore instance for business logic.
        event_bus: EventBus instance for event streaming.
        observability: Observability instance for logging.
        host: Bind address.
        port: Bind port.

    Returns:
        Unstarted GRPCRunner instance.
    """
    runner = GRPCRunner(host=host, port=port)

    servicer = AgentServiceServicer(
        agent_core=agent_core,
        event_bus=event_bus,
        observability=observability,
    )
    runner.inject_servicer(servicer)

    return runner
