"""WebFetchTool - Fetch and parse web page content."""

from __future__ import annotations

import logging
from typing import Any

from agent.tools.base import BaseTool, ExecutionContext, ToolResult

logger = logging.getLogger(__name__)


class WebFetchTool(BaseTool):
    """Fetches a URL and converts the page to readable content."""

    @property
    def name(self) -> str:
        return "web_fetch"

    @property
    def description(self) -> str:
        return (
            "Fetch the content of a given URL and return it as readable text. "
            "Automatically extracts the main content, ignoring navigation and ads. "
            "Supports HTTP and HTTPS URLs."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Request timeout in seconds. Default: 15.",
                },
            },
            "required": ["url"],
        }

    async def execute(
        self, context: ExecutionContext, arguments: dict[str, Any]
    ) -> ToolResult:
        url = arguments.get("url", "")
        timeout = arguments.get("timeout", 15)

        if not url.startswith(("http://", "https://")):
            return ToolResult(
                data={},
                summary="",
                raw="Error: URL must start with http:// or https://",
            )

        try:
            import httpx
            from markdownify import markdownify

            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, follow_redirects=True)
                resp.raise_for_status()

                # Try to detect charset
                content_type = resp.headers.get("content-type", "")
                if "charset=" in content_type:
                    encoding = content_type.split("charset=")[-1].strip()
                else:
                    encoding = "utf-8"

                html_text = resp.content.decode(encoding, errors="replace")

            # Convert HTML to markdown
            md_content = markdownify(html_text, heading_style="ATX").strip()

            # Extract title from HTML
            title = ""
            try:
                from html.parser import HTMLParser

                class TitleExtractor(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.title = ""
                        self._in_title = False

                    def handle_starttag(self, tag, attrs):
                        if tag == "title":
                            self._in_title = True

                    def handle_endtag(self, tag):
                        nonlocal self
                        if tag == "title":
                            self._in_title = False

                    def handle_data(self, data):
                        if self._in_title:
                            self.title += data

                extractor = TitleExtractor()
                extractor.feed(html_text)
                title = extractor.title.strip()
            except Exception:
                title = ""

            return ToolResult(
                data={
                    "url": url,
                    "title": title,
                    "content_length": len(md_content),
                },
                summary=f"Fetched '{title or url}' ({len(md_content)} characters).",
                raw=md_content[:10000],  # Cap raw output
            )
        except Exception as e:
            logger.error(f"Web fetch failed: {e}")
            return ToolResult(
                data={"url": url, "error": str(e)},
                summary=f"Failed to fetch {url}: {e}",
            )
