"""Tools: Bing Webmaster keyword research (real impression counts, free API key)."""

from typing import Annotated

from mcp.server.mcpserver import Context, MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from ..models_data import BingHistoryResult, BingKeywordResult, BingRelatedResult, BingWeeklyPoint
from ..sources import bing_webmaster as bing
from ..state import AppState
from .trends import cached

READ_ONLY = {"read_only_hint": True, "idempotent_hint": True, "open_world_hint": True}
KEY_NOTE = " Needs FREE_SEO_BING_API_KEY (free, from Bing Webmaster Tools)."

Country = Annotated[str, Field(description="ISO country code, lowercase, e.g. 'us', 'de'.")]
Language = Annotated[str, Field(description="Language-culture, e.g. 'en-US', 'de-DE'.")]
Days = Annotated[int, Field(ge=1, le=180, description="Period length in days, ending today.")]


def _state(ctx: Context) -> AppState:
    return ctx.request_context.lifespan_context


def register(mcp: MCPServer) -> None:
    @mcp.tool(
        description="Real Bing search impressions for one keyword over the last N days." + KEY_NOTE,
        annotations=ToolAnnotations(title="Bing: keyword impressions", **READ_ONLY),
    )
    async def bing_keyword(
        keyword: str,
        ctx: Context,
        country: Country = "us",
        language: Language = "en-US",
        days: Days = 30,
    ) -> BingKeywordResult:
        state = _state(ctx)
        start, end = bing.period(days)
        data = await cached(
            state,
            "bing.keyword",
            lambda: bing.get_keyword(
                state.http, state.settings.bing_api_key, keyword, country, language, start, end
            ),
            q=keyword,
            country=country,
            language=language,
            start=start,
            end=end,
        )
        return BingKeywordResult(
            **data, country=country, language=language, start_date=start, end_date=end
        )

    @mcp.tool(
        description=(
            "Keywords related to a phrase, each with real Bing impressions for the last N days, "
            "sorted by impressions. A free source of keyword ideas with numbers." + KEY_NOTE
        ),
        annotations=ToolAnnotations(title="Bing: related keywords", **READ_ONLY),
    )
    async def bing_related_keywords(
        keyword: str,
        ctx: Context,
        country: Country = "us",
        language: Language = "en-US",
        days: Days = 30,
    ) -> BingRelatedResult:
        state = _state(ctx)
        start, end = bing.period(days)
        rows = await cached(
            state,
            "bing.related",
            lambda: bing.get_related_keywords(
                state.http, state.settings.bing_api_key, keyword, country, language, start, end
            ),
            q=keyword,
            country=country,
            language=language,
            start=start,
            end=end,
        )
        rows = sorted(rows, key=lambda r: r["impressions"], reverse=True)
        return BingRelatedResult(
            keyword=keyword,
            country=country,
            language=language,
            start_date=start,
            end_date=end,
            related=[
                BingKeywordResult(
                    **r, country=country, language=language, start_date=start, end_date=end
                )
                for r in rows
            ],
        )

    @mcp.tool(
        description="Weekly Bing impression history for one keyword (seasonality)." + KEY_NOTE,
        annotations=ToolAnnotations(title="Bing: keyword history", **READ_ONLY),
    )
    async def bing_keyword_history(
        keyword: str,
        ctx: Context,
        country: Country = "us",
        language: Language = "en-US",
    ) -> BingHistoryResult:
        state = _state(ctx)
        rows = await cached(
            state,
            "bing.stats",
            lambda: bing.get_keyword_stats(
                state.http, state.settings.bing_api_key, keyword, country, language
            ),
            q=keyword,
            country=country,
            language=language,
        )
        return BingHistoryResult(
            query=keyword,
            country=country,
            language=language,
            weeks=[BingWeeklyPoint(**r) for r in sorted(rows, key=lambda r: r["date"])],
        )
