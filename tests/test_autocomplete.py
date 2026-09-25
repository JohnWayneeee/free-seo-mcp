import httpx
import pytest
import respx

from free_seo_mcp.analysis.scoring import position_weight, score_suggestions
from free_seo_mcp.http import PoliteClient
from free_seo_mcp.sources.autocomplete import (
    BING_URL,
    DDG_URL,
    GOOGLE_URL,
    AutocompleteError,
    fetch_suggestions,
)


def test_scoring_ranks_by_occurrence_and_position():
    ranked = score_suggestions(
        [
            ("google", ["running shoes men", "Running Shoes Women"]),
            ("google", ["running shoes women", "trail running shoes"]),
            ("bing", ["trail running shoes"]),
        ]
    )
    phrases = [p.phrase for p in ranked]
    assert phrases[0] in ("running shoes women", "trail running shoes")
    women = next(p for p in ranked if p.phrase == "running shoes women")
    assert women.occurrences == 2
    assert women.best_position == 0
    assert women.score == pytest.approx(position_weight(1) + position_weight(0))
    trail = next(p for p in ranked if p.phrase == "trail running shoes")
    assert trail.sources == {"google", "bing"}


def test_scoring_ignores_duplicates_within_one_list():
    (item,) = score_suggestions([("google", ["a b", "A  B"])])
    assert item.occurrences == 1


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("source", "url", "param"),
    [
        ("google", GOOGLE_URL, "q"),
        ("youtube", GOOGLE_URL, "q"),
        ("bing", BING_URL, "query"),
        ("duckduckgo", DDG_URL, "q"),
    ],
)
async def test_each_source_parses(source, url, param):
    http = PoliteClient(min_delay=0)
    with respx.mock:
        route = respx.get(url).mock(
            return_value=httpx.Response(200, json=["shoes", ["shoes a", "shoes b"]])
        )
        assert await fetch_suggestions(http, None, source, "shoes", "en", "us") == [
            "shoes a",
            "shoes b",
        ]
        sent = route.calls.last.request.url.params
        assert sent[param] == "shoes"
        if source == "youtube":
            assert sent["ds"] == "yt"
    await http.aclose()


@pytest.mark.anyio
async def test_bad_response_raises():
    http = PoliteClient(min_delay=0)
    with respx.mock:
        respx.get(DDG_URL).mock(return_value=httpx.Response(200, json={"oops": 1}))
        with pytest.raises(AutocompleteError):
            await fetch_suggestions(http, None, "duckduckgo", "x")
    await http.aclose()


@pytest.mark.anyio
async def test_tools_listed_with_annotations(client):
    tools = {t.name: t for t in (await client.list_tools()).tools}
    for name in ("suggest", "expand_alphabet", "expand_questions", "expand_multilingual"):
        assert tools[name].annotations.read_only_hint is True
        assert tools[name].annotations.idempotent_hint is True


@pytest.mark.anyio
async def test_suggest_tool_uses_cache(client):
    with respx.mock:
        route = respx.get(GOOGLE_URL).mock(
            return_value=httpx.Response(200, json=["shoes", ["shoes sale", "shoes red"]])
        )
        first = await client.call_tool("suggest", {"keyword": "shoes"})
        second = await client.call_tool("suggest", {"keyword": "shoes"})
        assert route.call_count == 1
    data = first.structured_content
    assert data["suggestions"][0] == {"phrase": "shoes sale", "position": 0}
    assert second.structured_content == data


@pytest.mark.anyio
async def test_expand_alphabet_scores_and_reports_progress(client):
    def reply(request):
        q = request.url.params["q"]
        return httpx.Response(200, json=[q, [f"{q} x", "shoes common"]])

    progress = []

    async def on_progress(p, total, message):
        progress.append((p, total))

    with respx.mock:
        respx.get(GOOGLE_URL).mock(side_effect=reply)
        result = await client.call_tool(
            "expand_alphabet",
            {"keyword": "shoes", "hl": "en", "gl": "us"},
            progress_callback=on_progress,
        )
    data = result.structured_content
    assert data["queries"] == 27
    top = data["phrases"][0]
    assert top["phrase"] == "shoes common"
    assert top["occurrences"] == 27
    assert progress and progress[-1] == (27, 27)


@pytest.mark.anyio
async def test_expand_questions_survives_source_failure(client):
    with respx.mock:
        respx.get(GOOGLE_URL).mock(
            return_value=httpx.Response(200, json=["q", ["how to lace shoes"]])
        )
        respx.get(BING_URL).mock(return_value=httpx.Response(404))
        result = await client.call_tool(
            "expand_questions", {"keyword": "shoes", "sources": ["google", "bing"]}
        )
    data = result.structured_content
    assert data["phrases"][0]["phrase"] == "how to lace shoes"
    assert data["phrases"][0]["sources"] == ["google"]
    assert len(data["errors"]) == data["queries"]


@pytest.mark.anyio
async def test_expand_multilingual_per_locale_errors(client):
    def reply(request):
        if request.url.params["hl"] == "es":
            return httpx.Response(400)
        return httpx.Response(200, json=["q", [f"shoes {request.url.params['gl']}"]])

    with respx.mock:
        respx.get(GOOGLE_URL).mock(side_effect=reply)
        result = await client.call_tool(
            "expand_multilingual", {"keyword": "shoes", "locales": ["en:us", "es:mx", "de"]}
        )
    locs = {r["locale"]: r for r in result.structured_content["locales"]}
    assert locs["en:us"]["suggestions"][0]["phrase"] == "shoes us"
    assert locs["es:mx"]["error"]
    assert locs["de"]["gl"] == "de"


@pytest.mark.live
@pytest.mark.anyio
async def test_live_google_suggest(client):
    result = await client.call_tool("suggest", {"keyword": "running shoes"})
    assert result.structured_content["suggestions"]
