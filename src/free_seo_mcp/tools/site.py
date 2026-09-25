"""Tools: sitemap_urls, page_outline."""

from typing import Annotated

from mcp.server.mcpserver import Context, MCPServer
from mcp_types import ToolAnnotations
from pydantic import Field

from ..models_research import PageOutline, SitemapResult
from ..sources import site as site_src
from ..state import AppState

READ_ONLY = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=True)


def register(mcp: MCPServer) -> None:
    @mcp.tool(annotations=READ_ONLY)
    async def sitemap_urls(
        site: Annotated[str, Field(description="Domain or URL, e.g. example.com")],
        ctx: Context,
        limit: Annotated[int, Field(ge=1, le=10000)] = 500,
        contains: Annotated[
            str | None, Field(description="Keep only URLs containing this substring")
        ] = None,
    ) -> SitemapResult:
        """List page URLs from a competitor's sitemaps to map its content structure.

        Discovers sitemaps via robots.txt (falls back to /sitemap.xml), follows sitemap
        indexes recursively and reads gzipped sitemaps.
        """
        state: AppState = ctx.request_context.lifespan_context
        base = site_src.normalize_site(site)
        key = state.cache.key("sitemap", site=base)
        cached = state.cache.get(key)
        if cached is not None:
            read, urls = cached
        else:
            read, urls = await site_src.collect_urls(state.http, base)
            state.cache.set(key, [read, urls])
        if contains:
            urls = [u for u in urls if contains.lower() in u.lower()]
        return SitemapResult(site=base, sitemaps=read, total_found=len(urls), urls=urls[:limit])

    @mcp.tool(annotations=READ_ONLY)
    async def page_outline(url: str, ctx: Context) -> PageOutline:
        """Fetch one page and return its title, meta description, h1-h3 headings and word count."""
        state: AppState = ctx.request_context.lifespan_context
        key = state.cache.key("outline", url=url)
        cached = state.cache.get(key)
        if cached is not None:
            return PageOutline(**cached)
        result = await site_src.page_outline(state.http, url)
        if result.status == 200:
            state.cache.set(key, result.model_dump())
        return result
