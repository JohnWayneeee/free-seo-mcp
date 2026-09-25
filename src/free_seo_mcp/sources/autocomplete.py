"""Autocomplete sources: Google, YouTube, Bing and DuckDuckGo suggestion endpoints.

All endpoints are unofficial. A failing source raises AutocompleteError so a caller can skip it
without losing results from the others.
"""

from typing import Literal

import httpx

from ..cache import DiskCache
from ..http import PoliteClient

Source = Literal["google", "youtube", "bing", "duckduckgo"]
SOURCES: tuple[str, ...] = ("google", "youtube", "bing", "duckduckgo")

GOOGLE_URL = "https://suggestqueries.google.com/complete/search"
BING_URL = "https://api.bing.com/osjson.aspx"
DDG_URL = "https://duckduckgo.com/ac/"


class AutocompleteError(Exception):
    pass


def _request(source: str, query: str, hl: str, gl: str) -> tuple[str, dict[str, str]]:
    if source in ("google", "youtube"):
        # client=firefox returns a bare JSON array: [query, [suggestions...]]
        params = {"client": "firefox", "q": query, "hl": hl, "gl": gl}
        if source == "youtube":
            params["ds"] = "yt"
        return GOOGLE_URL, params
    if source == "bing":
        return BING_URL, {"query": query, "market": f"{hl}-{gl.upper()}"}
    if source == "duckduckgo":
        return DDG_URL, {"q": query, "type": "list", "kl": f"{gl}-{hl}"}
    raise AutocompleteError(f"unknown source: {source}")


def _parse(data: object) -> list[str]:
    if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list):
        return [s for s in data[1] if isinstance(s, str) and s.strip()]
    raise AutocompleteError("unexpected response shape")


async def fetch_suggestions(
    http: PoliteClient,
    cache: DiskCache | None,
    source: str,
    query: str,
    hl: str = "en",
    gl: str = "us",
) -> list[str]:
    """Ordered suggestions for one query. Only successful answers are cached."""
    key = DiskCache.key(f"autocomplete:{source}", q=query, hl=hl, gl=gl)
    if cache is not None:
        hit = cache.get(key)
        if hit is not None:
            return hit
    url, params = _request(source, query, hl, gl)
    try:
        resp = await http.get(url, params=params)
        resp.raise_for_status()
        suggestions = _parse(resp.json())
    except (httpx.HTTPError, ValueError) as exc:
        raise AutocompleteError(f"{source}: {type(exc).__name__}") from exc
    if cache is not None:
        cache.set(key, suggestions)
    return suggestions
