"""Reddit search through the public JSON endpoints (no auth, honest UA)."""

from typing import Any

from mcp.server.mcpserver.exceptions import ToolError

from ..http import PoliteClient
from ..models_research import RedditPost

BASE = "https://www.reddit.com"
SNIPPET_LEN = 300


def parse(payload: dict[str, Any]) -> list[RedditPost]:
    posts = []
    for child in payload.get("data", {}).get("children", []):
        d = child.get("data", {})
        permalink = d.get("permalink") or ""
        posts.append(
            RedditPost(
                title=d.get("title", ""),
                subreddit=d.get("subreddit", ""),
                score=int(d.get("score") or 0),
                num_comments=int(d.get("num_comments") or 0),
                url=f"{BASE}{permalink}" if permalink else d.get("url", ""),
                created_utc=float(d.get("created_utc") or 0),
                snippet=" ".join((d.get("selftext") or "").split())[:SNIPPET_LEN],
            )
        )
    return posts


async def search(
    http: PoliteClient,
    query: str,
    subreddit: str | None = None,
    sort: str = "relevance",
    time: str = "all",
    limit: int = 25,
) -> list[RedditPost]:
    params: dict[str, Any] = {"q": query, "sort": sort, "t": time, "limit": limit}
    if subreddit:
        url = f"{BASE}/r/{subreddit}/search.json"
        params["restrict_sr"] = "1"
    else:
        url = f"{BASE}/search.json"
    resp = await http.get(url, params=params)
    if resp.status_code in (401, 403, 429):
        # Reddit blocks unauthenticated JSON access from some networks (datacenters, VPNs).
        raise ToolError(
            f"Reddit refused the request (HTTP {resp.status_code}). Unauthenticated access is "
            "blocked from this network or rate-limited; retry later or set FREE_SEO_PROXY."
        )
    resp.raise_for_status()
    return parse(resp.json())
