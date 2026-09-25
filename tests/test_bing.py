from datetime import date

import httpx
import pytest
import respx
from mcp import Client

from free_seo_mcp.server import build_server
from free_seo_mcp.sources import bing_webmaster as bing

BASE = bing.BASE


async def error_text(client, name, args):
    r = await client.call_tool(name, args)
    assert r.is_error
    return r.content[0].text


@pytest.fixture
async def keyed_client(data_dir, monkeypatch):
    monkeypatch.setenv("FREE_SEO_BING_API_KEY", "test-key")
    async with Client(build_server(), raise_exceptions=True) as c:
        yield c


def test_period_and_date_parsing():
    assert bing.period(7, date(2026, 3, 10)) == ("2026-03-03", "2026-03-10")
    assert bing.parse_date("/Date(1767225600000)/") == "2026-01-01"
    assert bing.parse_date("2026-01-01T00:00:00") == "2026-01-01"


@pytest.mark.anyio
async def test_missing_key_explains_setup(client):
    assert "FREE_SEO_BING_API_KEY" in await error_text(
        client, "bing_keyword", {"keyword": "running shoes"}
    )


@pytest.mark.anyio
@respx.mock
async def test_bing_keyword(keyed_client):
    route = respx.get(BASE + "GetKeyword").mock(
        return_value=httpx.Response(
            200,
            json={"d": {"Query": "running shoes", "Impressions": 1200, "BroadImpressions": 9000}},
        )
    )
    r = await keyed_client.call_tool("bing_keyword", {"keyword": "running shoes", "days": 30})
    s = r.structured_content
    assert s["impressions"] == 1200 and s["broad_impressions"] == 9000
    params = route.calls.last.request.url.params
    assert params["apikey"] == "test-key"
    assert params["q"] == "running shoes"
    assert params["country"] == "us" and params["language"] == "en-US"
    assert len(params["startDate"]) == 10 and params["startDate"] < params["endDate"]
    await keyed_client.call_tool("bing_keyword", {"keyword": "running shoes", "days": 30})
    assert route.call_count == 1  # second call served from cache


@pytest.mark.anyio
@respx.mock
async def test_bing_related_sorted(keyed_client):
    respx.get(BASE + "GetRelatedKeywords").mock(
        return_value=httpx.Response(
            200,
            json={
                "d": [
                    {"Query": "trail shoes", "Impressions": 10, "BroadImpressions": 30},
                    {"Query": "best running shoes", "Impressions": 500, "BroadImpressions": 900},
                ]
            },
        )
    )
    r = await keyed_client.call_tool("bing_related_keywords", {"keyword": "running shoes"})
    assert [x["query"] for x in r.structured_content["related"]] == [
        "best running shoes",
        "trail shoes",
    ]


@pytest.mark.anyio
@respx.mock
async def test_bing_history(keyed_client):
    respx.get(BASE + "GetKeywordStats").mock(
        return_value=httpx.Response(
            200,
            json={
                "d": [
                    {"Date": "/Date(1767830400000)/", "Impressions": 7, "BroadImpressions": 9},
                    {"Date": "/Date(1767225600000)/", "Impressions": 5, "BroadImpressions": 8},
                ]
            },
        )
    )
    r = await keyed_client.call_tool("bing_keyword_history", {"keyword": "running shoes"})
    assert [w["date"] for w in r.structured_content["weeks"]] == ["2026-01-01", "2026-01-08"]


@pytest.mark.anyio
@respx.mock
async def test_bing_rejected_key(keyed_client):
    respx.get(BASE + "GetKeyword").mock(return_value=httpx.Response(401))
    assert "rejected" in await error_text(keyed_client, "bing_keyword", {"keyword": "x"})


@pytest.mark.anyio
@respx.mock
async def test_estimate_uses_bing_base(keyed_client, monkeypatch):
    from free_seo_mcp.sources import trends as src

    async def fake_iot(keywords, geo, timeframe, proxy):
        return {"dates": ["2026-01-01"], "series": {"sneakers": [50], "trail shoes": [25]}}

    monkeypatch.setattr(src, "interest_over_time", fake_iot)
    respx.get(BASE + "GetKeyword").mock(
        return_value=httpx.Response(200, json={"d": {"Query": "sneakers", "Impressions": 100}})
    )
    r = await keyed_client.call_tool(
        "estimate_volumes",
        {"keywords": ["trail shoes"], "anchor": "sneakers", "engine_multiplier": 10},
    )
    s = r.structured_content
    assert s["base_source"] == "bing" and s["anchor_volume"] == 1000
    assert s["estimates"][0]["est_volume"] == 500
