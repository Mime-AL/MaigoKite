"""Agent Core command-line entry point."""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import threading
from types import FrameType

import click

from agent.config_manager import ConfigManager
from agent.core import AgentCore
from agent.event_bus import EventBus
from agent.grpc_runner import create_server
from agent.observability import ConsoleObserver, Observability

logger = logging.getLogger("maigokite-agent")


@click.group()
def cli() -> None:
    """Run the MaigoKite Agent Core."""


def main_cli() -> None:
    cli()


@cli.command()
@click.option("--prompt", "-p", default=None)
@click.option("--config", "-c", default=None, type=click.Path(exists=True, dir_okay=False))
@click.option("--host", "-H", default="127.0.0.1")
@click.option("--port", "-P", default=8081, type=click.IntRange(1, 65535))
@click.option("--interactive", "-i", is_flag=True)
def run(prompt: str | None, config: str | None, host: str, port: int, interactive: bool) -> None:
    """Start the gRPC service."""
    asyncio.run(start_agent(prompt, config, host, port, interactive))


async def start_agent(prompt: str | None, config_path: str | None, host: str, port: int, interactive: bool) -> None:
    config = ConfigManager(config_path or os.getenv("MAIGOKITE_CONFIG"))
    await config.load()
    event_bus = EventBus()
    observability = Observability()
    observability.add_observer(ConsoleObserver())
    core = AgentCore(config, event_bus, observability)
    runner = create_server(core, event_bus, observability, host, port)
    loop = asyncio.get_running_loop()
    main_task = asyncio.current_task()
    assert main_task is not None
    stopping = False

    def request_stop(_signum: int = 0, _frame: FrameType | None = None) -> None:
        nonlocal stopping
        if not stopping:
            stopping = True
            main_task.cancel()

    previous = {sig: signal.signal(sig, request_stop) for sig in (signal.SIGINT, signal.SIGTERM)}

    def watch_owner() -> None:
        # The launcher owns the write end. EOF also covers launcher crashes;
        # no PID polling, PID file, heartbeat or second cancellation framework.
        try:
            while sys.stdin.buffer.read(1):
                pass
        except (OSError, ValueError):
            pass
        try:
            loop.call_soon_threadsafe(request_stop)
        except RuntimeError:
            pass  # The event loop already finished shutting down.

    try:
        if os.getenv("MAIGOKITE_PARENT_PIPE") == "1":
            threading.Thread(target=watch_owner, name="core-owner-pipe", daemon=True).start()
        # Disable shared-port binding before touching persisted task state.
        runner.bind()
        await core.initialize()
        await runner.start()
        logger.info("Agent Core listening on %s:%d", host, port)
        if interactive and prompt:
            logger.info("Agent response: %s", (await core.run(prompt))["response"])
            return
        await runner.wait_for_rpcs()
    except asyncio.CancelledError:
        if not stopping:
            raise
    finally:
        try:
            try:
                await runner.stop(grace=5)
            finally:
                await core.shutdown()
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)


if __name__ == "__main__":
    main_cli()
