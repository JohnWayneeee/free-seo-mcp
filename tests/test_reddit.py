import httpx
import pytest
import respx

PAYLOAD = {
    "data": {
        "children": [
            {
                "data": {
                    "title": "Best running shoes for flat feet?",
                    "subreddit": "running",
                    "score": 120,
                    "num_comments": 45,
                    "permalink": "/r/running/comments/abc/best/",
                    "created_utc": 1700000000.0,
                    "selftext": "Looking   for\nadvice " + "x" * 400,
                }
            }
        ]
    }
}


@pytest.mark.anyio
async def test_reddit_search_global(client):
    with respx.mock:
        route = respx.get("https://www.reddit.com/search.json").mock(
            return_value=httpx.Response(200, json=PAYLOAD)
        )
        res = await client.call_tool("reddit_search", {"query": "running shoes", "limit": 5})
        # second call is served from cache
        await client.call_tool("reddit_search", {"query": "running shoes", "limit": 5})
    assert route.call_count == 1
    assert route.calls[0].request.url.params["q"] == "running shoes"
    post = res.structured_content["posts"][0]
    assert post["url"] == "https://www.reddit.com/r/running/comments/abc/best/"
    assert post["snippet"].startswith("Looking for advice")
    assert len(post["snippet"]) == 300


@pytest.mark.anyio
async def test_reddit_search_subreddit(client):
    with respx.mock:
        route = respx.get("https://www.reddit.com/r/running/search.json").mock(
            return_value=httpx.Response(200, json={"data": {"children": []}})
        )
        res = await client.call_tool("reddit_search", {"query": "shoes", "subreddit": "r/running"})
    assert route.calls[0].request.url.params["restrict_sr"] == "1"
    assert res.structured_content["subreddit"] == "running"
    assert res.structured_content["posts"] == []


@pytest.mark.anyio
async def test_reddit_blocked_gives_clear_error(client):
    with respx.mock:
        respx.get("https://www.reddit.com/search.json").mock(return_value=httpx.Response(403))
        res = await client.call_tool("reddit_search", {"query": "x"})
    assert res.is_error
    assert "Reddit refused" in res.content[0].text


@pytest.mark.live
@pytest.mark.anyio
async def test_reddit_live(client):
    res = await client.call_tool("reddit_search", {"query": "running shoes", "limit": 3})
    if res.is_error and "Reddit refused" in res.content[0].text:
        pytest.skip("Reddit blocks unauthenticated access from this network")
    assert res.structured_content["posts"]
