"""Tools: Google Trends comparisons, related queries, regional interest and volume estimates."""

from typing import Annotated

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from ..analysis import estimate as est
from ..models_data import (
    EstimateVolumesResult,
    RegionInterest,
    RelatedQuery,
    TrendsByRegionResult,
    TrendsCompareResult,
    TrendSeries,
    TrendsRelatedResult,
)
from ..sources import bing_webmaster as bing
from ..sources import trends as src
from ..state import AppState

READ_ONLY = {"read_only_hint": True, "idempotent_hint": True, "open_world_hint": True}

Geo = Annotated[str, Field(description="Country/region code like 'US', 'DE', 'US-CA'; '' = world.")]
Timeframe = Annotated[
    str,
    Field(
        description="'today 12-m', 'today 3-m', 'today 5-y', 'now 7-d' or 'YYYY-MM-DD YYYY-MM-DD'."
    ),
]


def _state(ctx: Context) -> AppState:
    return ctx.request_context.lifespan_context


async def cached(state: AppState, namespace: str, fetch, **params):
    """Serve from the disk cache or call fetch(); source errors become clean tool errors."""
    key = state.cache.key(namespace, **params)
    hit = state.cache.get(key)
    if hit is not None:
        return hit
    try:
        value = await fetch()
    except (src.TrendsError, bing.BingError) as e:
        raise ToolError(str(e)) from e
    state.cache.set(key, value)
    return value


async def fetch_interest(state: AppState, keywords: list[str], geo: str, timeframe: str) -> dict:
    return await cached(
        state,
        "trends.iot",
        lambda: src.interest_over_time(keywords, geo, timeframe, state.settings.proxy),
        keywords=keywords,
        geo=geo,
        timeframe=timeframe,
    )


def _mean(points: list[int]) -> float:
    return sum(points) / len(points) if points else 0.0


def register(mcp: MCPServer) -> None:
    @mcp.tool(
        description=(
            "Compare up to 5 keywords on one Google Trends 0-100 scale. Returns each keyword's "
            "time series, mean and peak. Relative interest only, not absolute volume."
        ),
        annotations=ToolAnnotations(title="Google Trends: compare", **READ_ONLY),
    )
    async def trends_compare(
        keywords: Annotated[list[str], Field(min_length=1, max_length=5)],
        ctx: Context,
        geo: Geo = "",
        timeframe: Timeframe = "today 12-m",
    ) -> TrendsCompareResult:
        data = await fetch_interest(_state(ctx), keywords, geo, timeframe)
        series = [
            TrendSeries(keyword=k, mean=round(_mean(p), 2), peak=max(p, default=0), points=p)
            for k, p in data["series"].items()
        ]
        return TrendsCompareResult(geo=geo, timeframe=timeframe, dates=data["dates"], series=series)

    @mcp.tool(
        description=(
            "Google Trends related queries for one keyword: 'top' (relative score 0-100) and "
            "'rising' (growth in percent). Good for finding new keyword ideas."
        ),
        annotations=ToolAnnotations(title="Google Trends: related", **READ_ONLY),
    )
    async def trends_related(
        keyword: str,
        ctx: Context,
        geo: Geo = "",
        timeframe: Timeframe = "today 12-m",
        limit: Annotated[int, Field(ge=1, le=100)] = 25,
    ) -> TrendsRelatedResult:
        state = _state(ctx)
        data = await cached(
            state,
            "trends.related",
            lambda: src.related_queries(keyword, geo, timeframe, limit, state.settings.proxy),
            keyword=keyword,
            geo=geo,
            timeframe=timeframe,
            limit=limit,
        )
        return TrendsRelatedResult(
            keyword=keyword,
            geo=geo,
            timeframe=timeframe,
            top=[RelatedQuery(**r) for r in data["top"]],
            rising=[RelatedQuery(**r) for r in data["rising"]],
        )

    @mcp.tool(
        description=(
            "Where a keyword is searched most, per Google Trends (0-100, sorted). With geo='' "
            "returns countries; with a country code returns its regions."
        ),
        annotations=ToolAnnotations(title="Google Trends: by region", **READ_ONLY),
    )
    async def trends_by_region(
        keyword: str,
        ctx: Context,
        geo: Geo = "",
        resolution: Annotated[
            str | None, Field(description="COUNTRY, REGION, CITY or DMA; default depends on geo.")
        ] = None,
        limit: Annotated[int, Field(ge=1, le=250)] = 50,
    ) -> TrendsByRegionResult:
        state = _state(ctx)
        data = await cached(
            state,
            "trends.region",
            lambda: src.interest_by_region(keyword, geo, resolution, limit, state.settings.proxy),
            keyword=keyword,
            geo=geo,
            resolution=resolution,
            limit=limit,
        )
        return TrendsByRegionResult(
            keyword=keyword,
            geo=geo,
            resolution=data["resolution"],
            regions=[RegionInterest(**r) for r in data["regions"]],
        )

    @mcp.tool(
        description=(
            "Estimate monthly search volume for many keywords. Each batch of 4 keywords is "
            "compared with the same anchor keyword in Google Trends; the ratio to the anchor is "
            "multiplied by an absolute base: anchor_volume if given, else the anchor's Bing "
            "Webmaster impressions (last 30 days) x engine_multiplier. Returns volume, "
            "high/mid/low tier, confidence and method per keyword. These are rough estimates, "
            "not exact counts. Pick an anchor of similar popularity whose volume you know."
        ),
        annotations=ToolAnnotations(title="Estimate search volumes", **READ_ONLY),
    )
    async def estimate_volumes(
        keywords: Annotated[list[str], Field(min_length=1, max_length=200)],
        anchor: Annotated[str, Field(description="Reference keyword included in every batch.")],
        ctx: Context,
        geo: Geo = "",
        timeframe: Timeframe = "today 12-m",
        anchor_volume: Annotated[
            float | None, Field(description="Known monthly searches for the anchor.", gt=0)
        ] = None,
        engine_multiplier: Annotated[
            float, Field(description="Google:Bing traffic ratio applied to Bing impressions.", gt=0)
        ] = est.DEFAULT_ENGINE_MULTIPLIER,
        bing_country: str = "us",
        bing_language: str = "en-US",
        high_threshold: float = est.DEFAULT_HIGH,
        mid_threshold: float = est.DEFAULT_MID,
    ) -> EstimateVolumesResult:
        state = _state(ctx)
        batches = est.batch_keywords(keywords, anchor)
        total = len(batches) + 1
        means: list[dict[str, float]] = []
        for i, batch in enumerate(batches):
            await ctx.report_progress(i, total, f"Trends batch {i + 1}/{len(batches)}")
            data = await fetch_interest(state, batch, geo, timeframe)
            means.append({k: _mean(p) for k, p in data["series"].items()})
        ratios = est.ratios_from_batches(means, anchor)
        anchor_means = [m.get(anchor, 0.0) for m in means]

        bing_impressions = None
        notes: list[str] = []
        if anchor_volume is None:
            await ctx.report_progress(len(batches), total, "Bing anchor impressions")
            key = state.settings.bing_api_key
            if key:
                start, end = bing.period(30)
                try:
                    kw = await cached(
                        state,
                        "bing.keyword",
                        lambda: bing.get_keyword(
                            state.http, key, anchor, bing_country, bing_language, start, end
                        ),
                        q=anchor,
                        country=bing_country,
                        language=bing_language,
                        start=start,
                        end=end,
                    )
                    bing_impressions = kw["impressions"]
                except ToolError as e:
                    notes.append(f"Bing lookup failed: {e}")
            else:
                notes.append("No Bing key configured (FREE_SEO_BING_API_KEY); see bing_keyword.")
        await ctx.report_progress(total, total, "done")

        result = est.estimate_volumes(
            keywords,
            anchor,
            ratios,
            geo=geo,
            anchor_volume=anchor_volume,
            bing_impressions=bing_impressions,
            engine_multiplier=engine_multiplier,
            anchor_mean=min(anchor_means) if anchor_means else None,
            high=high_threshold,
            mid=mid_threshold,
        )
        result.notes = notes + result.notes
        return result
