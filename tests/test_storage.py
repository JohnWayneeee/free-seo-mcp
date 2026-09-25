import csv

import pytest

from free_seo_mcp import storage
from free_seo_mcp.models_research import KeywordRow


def test_save_dedupes_and_merges(tmp_path):
    rows = [
        KeywordRow(phrase="Running  Shoes", sources=["google"], score=3),
        KeywordRow(phrase="running shoes", sources=["bing"], tier="high"),
        KeywordRow(phrase="trail shoes", bing_impressions=120),
    ]
    path, added, updated, total = storage.save(tmp_path, "shoes", "EN", rows)
    assert path == tmp_path / "shoes" / "en.csv"
    assert (added, updated, total) == (2, 1, 2)

    _, added, updated, total = storage.save(
        tmp_path, "shoes", "en", [KeywordRow(phrase="RUNNING shoes", score=7, sources=["google"])]
    )
    assert (added, updated, total) == (0, 1, 2)
    _, loaded = storage.load(tmp_path, "shoes", "en")
    first = loaded[0]
    assert first.phrase == "Running Shoes"
    assert first.sources == ["google", "bing"]
    assert first.score == 7
    assert first.tier == "high"
    assert loaded[1].bing_impressions == 120

    with path.open(encoding="utf-8") as f:
        assert next(csv.reader(f)) == storage.COLUMNS


def test_load_filters_and_missing(tmp_path):
    assert storage.load(tmp_path, "none", "en")[1] == []
    storage.save(
        tmp_path,
        "p",
        "ru",
        [
            KeywordRow(phrase="кроссовки для бега", tier="High", cluster="shoes"),
            KeywordRow(phrase="беговые носки", tier="low", cluster="socks"),
        ],
    )
    assert [r.phrase for r in storage.load(tmp_path, "p", "ru", tier="high")[1]] == [
        "кроссовки для бега"
    ]
    assert len(storage.load(tmp_path, "p", "ru", cluster="socks")[1]) == 1


@pytest.mark.parametrize("bad", ["../x", "a/b", "", ".hidden", "a b", "x" * 65])
def test_unsafe_names_rejected(tmp_path, bad):
    with pytest.raises(ValueError):
        storage.csv_path(tmp_path, bad, "en")
    with pytest.raises(ValueError):
        storage.csv_path(tmp_path, "ok", bad)


@pytest.mark.anyio
async def test_tools_roundtrip(client, data_dir):
    res = await client.call_tool(
        "keywords_save",
        {"project": "demo", "lang": "en", "rows": [{"phrase": "running shoes", "tier": "mid"}]},
    )
    assert res.structured_content["added"] == 1
    assert (data_dir / "demo" / "en.csv").exists()
    loaded = await client.call_tool("keywords_load", {"project": "demo", "lang": "en"})
    assert loaded.structured_content["rows"][0]["phrase"] == "running shoes"


@pytest.mark.anyio
async def test_annotations_and_prompt(client):
    tools = {t.name: t for t in (await client.list_tools()).tools}
    assert tools["keywords_save"].annotations.read_only_hint is False
    for name in ("keywords_load", "reddit_search", "sitemap_urls", "page_outline"):
        assert tools[name].annotations.read_only_hint is True
    prompt = await client.get_prompt(
        "keyword_research_workflow", {"seeds": "running shoes", "project": "demo"}
    )
    text = prompt.messages[0].content.text
    assert "running shoes" in text and 'project="demo"' in text
