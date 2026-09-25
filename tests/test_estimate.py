import pytest

from free_seo_mcp.analysis import estimate as est


def test_batch_keywords_prepends_anchor_and_dedupes():
    kws = ["a", "b", "A", "anchor", "c", "d", "e", " ", "f"]
    assert est.batch_keywords(kws, "anchor") == [
        ["anchor", "a", "b", "c", "d"],
        ["anchor", "e", "f"],
    ]


def test_batch_keywords_empty():
    assert est.batch_keywords([], "anchor") == []


def test_ratios_from_batches_normalises_each_batch_to_its_anchor():
    batches = [{"x": 50, "a": 25, "y": 10}, {"x": 10, "z": 40}, {"x": 0, "w": 5}]
    r = est.ratios_from_batches(batches, "x")
    assert r == {"a": 0.5, "y": 0.2, "z": 4.0, "w": None}


@pytest.mark.parametrize(
    ("volume", "tier"), [(10_000, "high"), (9_999, "mid"), (1_000, "mid"), (999, "low")]
)
def test_tier_defaults(volume, tier):
    assert est.tier_for(volume) == tier


def test_tier_custom_thresholds():
    assert est.tier_for(500, high=400, mid=100) == "high"


def test_resolve_base_prefers_user_then_bing():
    assert est.resolve_base(1000, 50, 8) == (1000.0, "user")
    assert est.resolve_base(None, 50, 8) == (400.0, "bing")
    assert est.resolve_base(None, 0, 8) == (None, "none")
    assert est.resolve_base(None, None, 8) == (None, "none")


def test_estimate_with_user_anchor_volume():
    res = est.estimate_volumes(
        ["running shoes", "trail shoes"],
        "sneakers",
        {"running shoes": 2.0, "trail shoes": 0.25},
        geo="US",
        anchor_volume=10_000,
        anchor_mean=40,
    )
    by = {e.keyword: e for e in res.estimates}
    assert res.base_source == "user"
    assert by["running shoes"].est_volume == 20_000
    assert by["running shoes"].tier == "high"
    assert by["running shoes"].confidence == "medium"
    assert by["trail shoes"].est_volume == 2_500
    assert by["trail shoes"].tier == "mid"
    assert "user anchor_volume" in by["trail shoes"].method


def test_estimate_with_bing_base_is_low_confidence():
    res = est.estimate_volumes(["k"], "a", {"k": 0.5}, bing_impressions=100, engine_multiplier=10)
    e = res.estimates[0]
    assert res.base_source == "bing"
    assert res.anchor_volume == 1000
    assert e.est_volume == 500
    assert e.confidence == "low"
    assert "Bing" in e.method


def test_zero_ratio_is_upper_bound_not_zero():
    res = est.estimate_volumes(["rare"], "a", {"rare": 0.0}, anchor_volume=5000)
    e = res.estimates[0]
    assert e.below_threshold is True
    assert e.est_volume == 50
    assert e.tier == "low"
    assert e.confidence == "low"
    assert "under 1%" in e.method


def test_no_base_returns_ratios_only():
    res = est.estimate_volumes(["k"], "a", {"k": 1.5})
    e = res.estimates[0]
    assert res.base_source == "none"
    assert e.trends_ratio == 1.5
    assert e.est_volume is None and e.tier is None
    assert res.notes


def test_missing_ratio_and_weak_anchor():
    res = est.estimate_volumes(
        ["k", "m"], "a", {"k": None, "m": 1.0}, anchor_volume=100, anchor_mean=2
    )
    by = {e.keyword: e for e in res.estimates}
    assert by["k"].est_volume is None and by["k"].confidence == "low"
    assert by["m"].confidence == "low"
    assert any("low Trends interest" in n for n in res.notes)
