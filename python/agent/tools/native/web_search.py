"""WebSearchTool - Perform web searches via Tavily, Google, or DuckDuckGo."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from agent.tools.base import BaseTool, ExecutionContext, ToolResult

logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):
    """Performs web searches and returns results."""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search the web for information using a search engine. "
            "Supports Tavily, Google Custom Search, and DuckDuckGo. "
            "Returns a list of search results with titles, URLs, and snippets."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 500,
                    "description": "The search query string.",
                },
                "engine": {
                    "type": "string",
                    "enum": ["tavily", "google", "duckduckgo"],
                    "description": "Search engine to use. Defaults to tavily if configured, duckduckgo as fallback.",
                },
                "max_results": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Maximum number of results to return. Default: 5.",
                },
            },
            "required": ["query"],
        }

    async def execute(
        self, context: ExecutionContext, arguments: dict[str, Any]
    ) -> ToolResult:
        query = arguments.get("query", "")
        engine = arguments.get("engine", "tavily")
        max_results = arguments.get("max_results", 5)

        # Load API key from credential store (via config_manager injected at runtime)
        api_key = context.metadata.get("api_keys", {}).get(engine, "")

        try:
            if engine == "tavily" and api_key:
                results = await self._tavily_search(query, api_key, max_results)
            elif engine == "google" and api_key:
                results = await self._google_search(query, api_key, max_results)
            else:
                # DuckDuckGo doesn't require an API key
                engine = "duckduckgo"
                results = await self._duckduckgo_search(query, max_results)

            return ToolResult(
                data={"results": results, "engine": engine},
                summary=f"Found {len(results)} results using {engine} for '{query}'.",
                raw=self._format_results(results),
            )
        except Exception as e:
            logger.error("Web search failed (%s)", type(e).__name__)
            return ToolResult(
                data={"results": [], "error": "search provider request failed"},
                summary="Web search provider request failed.",
            )

    async def _tavily_search(
        self, query: str, api_key: str, max_results: int
    ) -> list[dict[str, Any]]:
        """Search via Tavily API."""
        import httpx

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": api_key,
            "query": query,
            "max_results": max_results,
            "include_answer": True,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=15.0)
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", ""),
            }
            for r in data.get("results", [])
        ]

    async def _google_search(
        self, query: str, api_key: str, max_results: int
    ) -> list[dict[str, Any]]:
        """Search via Google Custom Search API."""
        import httpx

        cx = api_key.split(":")[1] if ":" in api_key else ""
        key = api_key.split(":")[0] if ":" in api_key else api_key
        url = "https://www.googleapis.com/customsearch/v1"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params={"key": key, "cx": cx, "q": query, "num": max_results}, timeout=15.0)
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("link", ""),
                "snippet": r.get("snippet", ""),
            }
            for r in data.get("items", [])
        ]

    async def _duckduckgo_search(
        self, query: str, max_results: int
    ) -> list[dict[str, Any]]:
        """Search via DuckDuckGo (free, no API key)."""
        from duckduckgo_search import DDGS

        def search() -> list[dict[str, Any]]:
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    })
            return results

        return await asyncio.to_thread(search)

    @staticmethod
    def _format_results(results: list[dict[str, Any]]) -> str:
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r.get('title', 'Untitled')}")
            lines.append(f"   {r.get('url', '')}")
            lines.append(f"   {r.get('snippet', '')}")
            lines.append("")
        return "\n".join(lines)
