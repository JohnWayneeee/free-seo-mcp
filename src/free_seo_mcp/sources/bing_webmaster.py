"""Bing Webmaster API keyword research (free; needs an API key from a verified Bing account).

Endpoints are WCF JSON GETs; DateTime query params accept ISO 8601 dates and responses are
wrapped in {"d": ...}. Dates inside responses use the WCF "/Date(ms)/" form.
"""

import re
from datetime import UTC, date, datetime, timedelta
from typing import Any

from ..http import PoliteClient

BASE = "https://ssl.bing.com/webmaster/api.svc/json/"

MISSING_KEY = (
    "Bing Webmaster API key is not configured. Get a free key: sign in at "
    "https://www.bing.com/webmasters, add and verify any site you own, then open "
    "Settings -> API access -> API Key. Set it as the FREE_SEO_BING_API_KEY environment "
    "variable and restart the MCP server."
)


class BingError(RuntimeError):
    pass


def period(days: int, today: date | None = None) -> tuple[str, str]:
    end = today or datetime.now(UTC).date()
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()


_WCF_DATE = re.compile(r"/Date\((-?\d+)")


def parse_date(value: Any) -> str:
    if isinstance(value, str):
        m = _WCF_DATE.search(value)
        if m:
            return datetime.fromtimestamp(int(m.group(1)) / 1000, UTC).date().isoformat()
        return value[:10]
    return str(value)


def _int(v: Any) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


async def _call(http: PoliteClient, api_key: str | None, method: str, **params: str) -> Any:
    if not api_key:
        raise BingError(MISSING_KEY)
    resp = await http.get(BASE + method, params={"apikey": api_key, **params})
    if resp.status_code in (400, 401, 403):
        raise BingError(
            f"Bing Webmaster API rejected the request (HTTP {resp.status_code}). Check that "
            "FREE_SEO_BING_API_KEY is valid and your account has at least one verified site."
        )
    if resp.status_code >= 400:
        raise BingError(f"Bing Webmaster API error: HTTP {resp.status_code}")
    try:
        body = resp.json()
    except ValueError as e:
        raise BingError("Bing Webmaster API returned a non-JSON response.") from e
    return body.get("d") if isinstance(body, dict) and "d" in body else body


def _keyword(item: dict) -> dict:
    return {
        "query": item.get("Query", ""),
        "impressions": _int(item.get("Impressions")),
        "broad_impressions": _int(item.get("BroadImpressions")),
    }


async def get_keyword(
    http, api_key, q: str, country: str, language: str, start: str, end: str
) -> dict:
    data = await _call(
        http,
        api_key,
        "GetKeyword",
        q=q,
        country=country,
        language=language,
        startDate=start,
        endDate=end,
    )
    return _keyword(data or {"Query": q})


async def get_related_keywords(
    http, api_key, q: str, country: str, language: str, start: str, end: str
) -> list[dict]:
    data = await _call(
        http,
        api_key,
        "GetRelatedKeywords",
        q=q,
        country=country,
        language=language,
        startDate=start,
        endDate=end,
    )
    return [_keyword(i) for i in data or []]


async def get_keyword_stats(http, api_key, q: str, country: str, language: str) -> list[dict]:
    data = await _call(http, api_key, "GetKeywordStats", q=q, country=country, language=language)
    return [
        {
            "date": parse_date(i.get("Date")),
            "impressions": _int(i.get("Impressions")),
            "broad_impressions": _int(i.get("BroadImpressions")),
        }
        for i in data or []
    ]
