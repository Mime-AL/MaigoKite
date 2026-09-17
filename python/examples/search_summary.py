"""Search-result summarization example with injected provider boundaries."""
from __future__ import annotations

import argparse
import asyncio
from typing import Any, Awaitable, Callable

from agent.models.chat_adapter import ChatAdapter
from agent.models.chat_provider import ChatMessage, IChatProvider

Search = Callable[[str], Awaitable[list[dict[str, Any]]]]


async def search_and_summarize(query: str, search: Search, provider: IChatProvider) -> str:
    results = await search(query)
    evidence = "\n".join(f"- {item.get('title', '')}: {item.get('snippet', '')}" for item in results[:5])
    prompt = f"Summarize these search results for the query {query!r}. Cite result titles.\n{evidence}"
    return (await provider.chat([ChatMessage("user", prompt)])).content


async def duckduckgo_search(query: str) -> list[dict[str, Any]]:
    def search() -> list[dict[str, Any]]:
        from duckduckgo_search import DDGS

        with DDGS() as client:
            return [
                {"title": item.get("title", ""), "snippet": item.get("body", ""), "url": item.get("href", "")}
                for item in client.text(query, max_results=5)
            ]

    return await asyncio.to_thread(search)


async def run_example(args: argparse.Namespace) -> None:
    provider = ChatAdapter(
        provider=args.provider,
        model=args.model,
        base_url=args.base_url or None,
        api_key=args.api_key or None,
        temperature=0.2,
    )
    try:
        print(await search_and_summarize(args.query, duckduckgo_search, provider))
    finally:
        await provider.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Search the web and summarize five results with a configured model.")
    parser.add_argument("query")
    parser.add_argument("--provider", choices=["openai", "anthropic", "openai_compatible", "ollama"], default="ollama")
    parser.add_argument("--model", default="qwen3.5")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--api-key", default="", help="Prefer the provider environment variable in shared terminals.")
    asyncio.run(run_example(parser.parse_args()))


if __name__ == "__main__":
    main()
