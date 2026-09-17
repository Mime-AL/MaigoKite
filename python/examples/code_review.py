"""Runnable phase-one code review workflow."""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from agent.models.chat_adapter import ChatAdapter
from agent.models.chat_provider import ChatMessage, IChatProvider


async def review_file(path: str | Path, provider: IChatProvider) -> str:
    source_path = Path(path).expanduser().resolve()
    source = source_path.read_text(encoding="utf-8")
    prompt = (
        f"Review the Python file {source_path.name}. Prioritize correctness, security, and maintainability. "
        "Give concrete findings with line references; say clearly when no issue is found.\n\n"
        f"```python\n{source}\n```"
    )
    return (await provider.chat([ChatMessage("user", prompt)])).content


async def run(args: argparse.Namespace) -> None:
    provider = ChatAdapter(
        provider=args.provider, model=args.model, base_url=args.base_url or None,
        api_key=args.api_key or None, temperature=0.1,
    )
    try:
        print(await review_file(args.path, provider))
    finally:
        await provider.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Review one Python file with a configured chat model.")
    parser.add_argument("path")
    parser.add_argument("--provider", choices=["openai", "anthropic", "openai_compatible", "ollama"], default="ollama")
    parser.add_argument("--model", default="qwen3.5")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--api-key", default="", help="Prefer provider environment variables in shared terminals.")
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
