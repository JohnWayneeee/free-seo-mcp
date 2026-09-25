"""Google Trends via trendspy. trendspy is synchronous (requests), so calls run in a worker thread.

Every function returns plain JSON-able dicts so results can go straight into the disk cache.
"""

import math
from typing import Any

import anyio
from trendspy import Trends
from trendspy.client import TrendsQuotaExceededError

MAX_TERMS = 5


class TrendsError(RuntimeError):
    pass


def make_client(proxy: str | None = None) -> Trends:
    return Trends(request_delay=1.0, proxy=proxy)


def _num(v: Any) -> int:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0
    return 0 if math.isnan(f) else int(f)


def _interest_over_time(keywords: list[str], geo: str, timeframe: str, proxy: str | None) -> dict:
    df = make_client(proxy).interest_over_time(keywords, timeframe=timeframe, geo=geo)
    if df is None or len(df) == 0:
        return {"dates": [], "series": {k: [] for k in keywords}}
    dates = [str(ts)[:10] for ts in df.index]
    return {
        "dates": dates,
        "series": {k: [_num(v) for v in df[k]] if k in df.columns else [] for k in keywords},
    }


def _rows(df: Any, limit: int) -> list[dict]:
    if df is None or len(df) == 0 or "query" not in df.columns:
        return []
    return [
        {"query": str(q), "value": _num(v)} for q, v in zip(df["query"], df["value"], strict=False)
    ][:limit]


def _related(keyword: str, geo: str, timeframe: str, limit: int, proxy: str | None) -> dict:
    client = make_client(proxy)
    try:
        data = client.related_queries(keyword, timeframe=timeframe, geo=geo)
    except TrendsQuotaExceededError:
        # trendspy's own suggestion: the explore referer is throttled harder than a plain one.
        try:
            data = client.related_queries(
                keyword,
                timeframe=timeframe,
                geo=geo,
                headers={"referer": "https://www.google.com/"},
            )
        except TrendsQuotaExceededError as e:
            raise TrendsError(
                "Google Trends quota exceeded for related queries. Wait a few minutes or set "
                "FREE_SEO_PROXY."
            ) from e
    return {"top": _rows(data.get("top"), limit), "rising": _rows(data.get("rising"), limit)}


def _by_region(keyword: str, geo: str, resolution: str | None, limit: int, proxy: str | None):
    df = make_client(proxy).interest_by_region(keyword, geo=geo, resolution=resolution)
    res = resolution or ("COUNTRY" if not geo else "REGION")
    if df is None or len(df) == 0 or keyword not in df.columns:
        return {"resolution": res, "regions": []}
    codes = df["geoCode"] if "geoCode" in df.columns else [None] * len(df)
    regions = [
        {"name": str(n), "code": c, "value": _num(v)}
        for n, c, v in zip(df["geoName"], codes, df[keyword], strict=False)
    ]
    regions.sort(key=lambda r: r["value"], reverse=True)
    return {"resolution": res, "regions": regions[:limit]}


async def _run(fn, *args):
    try:
        return await anyio.to_thread.run_sync(fn, *args)
    except TrendsError:
        raise
    except Exception as e:  # trendspy raises bare exceptions on HTTP errors / 429
        raise TrendsError(f"Google Trends request failed: {e}") from e


async def interest_over_time(
    keywords: list[str], geo: str = "", timeframe: str = "today 12-m", proxy: str | None = None
) -> dict:
    if not 1 <= len(keywords) <= MAX_TERMS:
        raise TrendsError(f"Google Trends compares 1 to {MAX_TERMS} keywords per request.")
    return await _run(_interest_over_time, keywords, geo, timeframe, proxy)


async def related_queries(
    keyword: str,
    geo: str = "",
    timeframe: str = "today 12-m",
    limit: int = 25,
    proxy: str | None = None,
) -> dict:
    return await _run(_related, keyword, geo, timeframe, limit, proxy)


async def interest_by_region(
    keyword: str,
    geo: str = "",
    resolution: str | None = None,
    limit: int = 50,
    proxy: str | None = None,
) -> dict:
    return await _run(_by_region, keyword, geo, resolution, limit, proxy)
