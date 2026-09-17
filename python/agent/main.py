"""Agent Core command-line entry point."""
from __future__ import annotations

import asyncio
import logging

import click

from agent.config_manager import ConfigManager
from agent.core import AgentCore
from agent.event_bus import EventBus
from agent.grpc_runner import create_and_run_server
from agent.observability import ConsoleObserver, Observability

logger = logging.getLogger("nanami-agent")


@click.group()
def cli() -> None:
    """Run the NanamiGopher Agent Core."""


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
    config = ConfigManager(config_path)
    await config.load()
    event_bus = EventBus()
    observability = Observability()
    observability.add_observer(ConsoleObserver())
    core = AgentCore(config, event_bus, observability)
    await core.initialize()
    runner = await create_and_run_server(core, event_bus, observability, host, port)
    logger.info("Agent Core listening on %s:%d", host, port)
    try:
        if interactive and prompt:
            logger.info("Agent response: %s", (await core.run(prompt))["response"])
            return
        await runner.wait_for_rpcs()
    finally:
        await runner.stop(grace=5)
        await core.shutdown()


if __name__ == "__main__":
    main_cli()
