"""Tools: reddit_search."""

from typing import Annotated, Literal

from mcp.server.mcpserver import Context, MCPServer
from mcp_types import ToolAnnotations
from pydantic import Field

from ..models_research import RedditPost, RedditSearchResult
from ..sources import reddit
from ..state import AppState

READ_ONLY = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=True)


def register(mcp: MCPServer) -> None:
    @mcp.tool(annotations=READ_ONLY)
    async def reddit_search(
        query: str,
        ctx: Context,
        subreddit: Annotated[
            str | None, Field(description="Limit to one subreddit, without the r/ prefix")
        ] = None,
        sort: Literal["relevance", "hot", "top", "new", "comments"] = "relevance",
        time: Literal["hour", "day", "week", "month", "year", "all"] = "all",
        limit: Annotated[int, Field(ge=1, le=100)] = 25,
    ) -> RedditSearchResult:
        """Search Reddit threads to hear how real buyers phrase questions and problems.

        Returns title, subreddit, score, comment count, URL and a short body snippet per thread.
        """
        state: AppState = ctx.request_context.lifespan_context
        sub = subreddit.removeprefix("r/").strip("/") if subreddit else None
        key = state.cache.key("reddit", q=query, sub=sub, sort=sort, t=time, limit=limit)
        cached = state.cache.get(key)
        if cached is not None:
            posts = [RedditPost(**p) for p in cached]
        else:
            posts = await reddit.search(state.http, query, sub, sort, time, limit)
            state.cache.set(key, [p.model_dump() for p in posts])
        return RedditSearchResult(query=query, subreddit=sub, posts=posts)
