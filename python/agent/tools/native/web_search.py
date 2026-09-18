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
        requested_engine = arguments.get("engine")
        max_results = arguments.get("max_results", 5)

        # Secrets are injected into execution memory by the Gateway and never enter
        # the conversation, ToolResult, or persisted workspace settings.
        api_keys = context.metadata.get("api_keys", {})
        if not isinstance(api_keys, dict):
            api_keys = {}
        if requested_engine:
            engine = str(requested_engine)
        elif api_keys.get("tavily"):
            engine = "tavily"
        elif api_keys.get("google"):
            engine = "google"
        else:
            engine = "duckduckgo"
        api_key = str(api_keys.get(engine, ""))

        if engine in {"tavily", "google"} and not api_key:
            return ToolResult.failure(
                data={"results": [], "error": "search provider is not configured", "engine": engine},
                summary=f"{engine.title()} search is not configured.",
                error_code="SEARCH_PROVIDER_NOT_CONFIGURED",
                user_hint=f"请在“设置 → 联网工具”中配置 {engine.title()}，或改用 DuckDuckGo。",
                action={"label": "配置联网工具", "to": "/settings?tab=tools"},
            )
        if engine == "google":
            key, separator, cx = api_key.partition(":")
            if not separator or not key.strip() or not cx.strip():
                return ToolResult.failure(
                    data={"results": [], "error": "search provider configuration is invalid", "engine": engine},
                    summary="Google search configuration is invalid.",
                    error_code="SEARCH_PROVIDER_INVALID_CONFIGURATION",
                    user_hint="Google 搜索需要 API Key 和搜索引擎 ID（CX），请在“设置 → 联网工具”中重新配置。",
                    action={"label": "配置联网工具", "to": "/settings?tab=tools"},
                )

        try:
            if engine == "tavily":
                results = await self._tavily_search(query, api_key, max_results)
            elif engine == "google":
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
            return ToolResult.failure(
                data={"results": [], "error": "search provider request failed", "engine": engine},
                summary="Web search provider request failed.",
                error_code="SEARCH_PROVIDER_UNAVAILABLE",
                user_hint="联网搜索暂不可用。请检查网络，或在“设置 → 联网工具”中配置其他搜索服务。",
                action={"label": "配置联网工具", "to": "/settings?tab=tools"},
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

        key, _, cx = api_key.partition(":")
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
