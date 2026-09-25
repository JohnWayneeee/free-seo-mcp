import pandas as pd
import pytest

from free_seo_mcp.sources import trends as src


class FakeTrends:
    calls = 0

    def interest_over_time(self, keywords, timeframe="", geo=""):
        FakeTrends.calls += 1
        base = {"sneakers": [40, 40], "running shoes": [80, 80], "trail shoes": [10, 10]}
        idx = pd.DatetimeIndex(["2026-01-04", "2026-01-11"])
        return pd.DataFrame({k: base.get(k, [0, 0]) for k in keywords}, index=idx)

    def related_queries(self, keyword, timeframe="", geo="", headers=None):
        return {
            "top": pd.DataFrame({"query": ["best running shoes"], "value": [100]}),
            "rising": pd.DataFrame({"query": ["carbon plate shoes"], "value": [250]}),
        }

    def interest_by_region(self, keyword, geo="", resolution=None):
        return pd.DataFrame(
            {"geoName": ["Ohio", "Utah"], "geoCode": ["US-OH", "US-UT"], keyword: [30, 100]}
        )


async def error_text(client, name, args):
    r = await client.call_tool(name, args)
    assert r.is_error
    return r.content[0].text


@pytest.fixture(autouse=True)
def fake(request, monkeypatch):
    if request.node.get_closest_marker("live"):
        return
    FakeTrends.calls = 0
    monkeypatch.setattr(src, "make_client", lambda proxy=None: FakeTrends())


@pytest.mark.anyio
async def test_trends_compare_and_cache(client):
    args = {"keywords": ["running shoes", "trail shoes"], "geo": "US"}
    s = (await client.call_tool("trends_compare", args)).structured_content
    assert s["dates"] == ["2026-01-04", "2026-01-11"]
    assert [x["mean"] for x in s["series"]] == [80, 10]
    await client.call_tool("trends_compare", args)
    assert FakeTrends.calls == 1


@pytest.mark.anyio
async def test_trends_compare_rejects_more_than_five(client):
    assert await error_text(client, "trends_compare", {"keywords": list("abcdef")})


@pytest.mark.anyio
async def test_trends_related(client):
    s = (await client.call_tool("trends_related", {"keyword": "running shoes"})).structured_content
    assert s["top"][0] == {"query": "best running shoes", "value": 100}
    assert s["rising"][0]["value"] == 250


@pytest.mark.anyio
async def test_trends_by_region_sorted(client):
    r = await client.call_tool("trends_by_region", {"keyword": "running shoes", "geo": "US"})
    s = r.structured_content
    assert s["resolution"] == "REGION"
    assert [x["code"] for x in s["regions"]] == ["US-UT", "US-OH"]


@pytest.mark.anyio
async def test_related_quota_error_is_clean(client, monkeypatch):
    from trendspy.client import TrendsQuotaExceededError

    def boom(*a, **k):
        raise TrendsQuotaExceededError()

    monkeypatch.setattr(FakeTrends, "related_queries", boom)
    assert "quota exceeded" in await error_text(client, "trends_related", {"keyword": "x"})


@pytest.mark.anyio
async def test_estimate_volumes_tool(client):
    r = await client.call_tool(
        "estimate_volumes",
        {"keywords": ["running shoes", "trail shoes"], "anchor": "sneakers", "anchor_volume": 1000},
    )
    s = r.structured_content
    by = {e["keyword"]: e for e in s["estimates"]}
    assert by["running shoes"]["est_volume"] == 2000
    assert by["trail shoes"]["est_volume"] == 250
    assert s["base_source"] == "user"


@pytest.mark.anyio
async def test_estimate_volumes_without_bing_key_notes_it(client):
    args = {"keywords": ["trail shoes"], "anchor": "sneakers"}
    s = (await client.call_tool("estimate_volumes", args)).structured_content
    assert s["base_source"] == "none"
    assert any("Bing" in n for n in s["notes"])


@pytest.mark.live
@pytest.mark.anyio
async def test_live_interest_over_time():
    data = await src.interest_over_time(["running shoes", "hiking boots"], "US", "today 3-m")
    assert data["dates"]
    assert any(v > 0 for v in data["series"]["running shoes"])
