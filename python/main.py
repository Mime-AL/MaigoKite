"""Main entry point for the NanamiGopher agent."""

from __future__ import annotations

import asyncio
import click
import logging

from agent.config_manager import ConfigManager
from agent.core import AgentCore
from agent.event_bus import EventBus
from agent.observability import Observability, ConsoleObserver
from agent.grpc_runner import create_and_run_server


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("nanami-agent")


@click.group()
def cli() -> None:
    """NanamiGopher Agent Core CLI."""
    pass


@cli.command()
@click.option("--prompt", "-p", default=None, help="Initial prompt for the agent.")
@click.option("--config", "-c", default=None, help="Path to configuration file.")
@click.option("--host", "-H", default="127.0.0.1", help="gRPC server bind address.")
@click.option("--port", "-P", default=50051, type=int, help="gRPC server bind port.")
@click.option("--interactive", "-i", is_flag=True, help="Run in interactive mode (CLI prompt).")
def run(prompt: str, config: str, host: str, port: int, interactive: bool) -> None:
    """Start the NanamiGopher agent core with gRPC server."""
    asyncio.run(start_agent(prompt, config, host, port, interactive))


async def start_agent(
    prompt: str | None,
    config_path: str | None,
    host: str,
    port: int,
    interactive: bool,
) -> None:
    """Bootstrap and start the agent core with gRPC server."""
    # Load configuration
    config = ConfigManager(config_path)
    await config.load()

    # Initialize subsystems
    event_bus = EventBus()
    observability = Observability()
    observability.add_observer(ConsoleObserver())
    core = AgentCore(config=config, event_bus=event_bus, observability=observability)
    await core.initialize()

    # Start gRPC server
    runner = await create_and_run_server(
        agent_core=core,
        event_bus=event_bus,
        observability=observability,
        host=host,
        port=port,
    )

    logger.info("Agent core initialized. Press Ctrl+C to stop.")

    if interactive and prompt:
        # Single-shot mode: process prompt and exit
        result = await core.run(prompt=prompt)
        logger.info("Agent response: %s", result.get("response", ""))
        await runner.stop(grace=2)
        return

    # Daemon mode: keep running until interrupted
    try:
        await runner.wait_for_rpcs()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await runner.stop(grace=5)
        await core.shutdown()


if __name__ == "__main__":
    cli()
