"""Search-volume estimation from a Trends anchor. Pure functions: no I/O, fully unit-tested.

Google Trends only gives relative interest (0-100, max 5 terms per request). Putting the same
anchor term into every batch of 4 keywords lets all keywords be expressed as a ratio of the
anchor; one absolute number for the anchor then turns every ratio into an estimated volume.
"""

from collections.abc import Mapping, Sequence

from ..models_data import EstimateVolumesResult, KeywordEstimate, Tier

TRENDS_BATCH = 4  # 4 keywords + the anchor = the 5-term Trends limit
DEFAULT_ENGINE_MULTIPLIER = 8.0  # rough Google:Bing traffic ratio, deliberately conservative
DEFAULT_HIGH = 10_000
DEFAULT_MID = 1_000
# Below this mean the anchor's Trends curve is mostly rounding noise.
WEAK_SIGNAL = 5.0


def batch_keywords(
    keywords: Sequence[str], anchor: str, size: int = TRENDS_BATCH
) -> list[list[str]]:
    """Split keywords into Trends requests, each starting with the anchor. Dedupes, keeps order."""
    seen: set[str] = {anchor.casefold()}
    unique: list[str] = []
    for kw in keywords:
        k = kw.strip()
        if k and k.casefold() not in seen:
            seen.add(k.casefold())
            unique.append(k)
    return [[anchor, *unique[i : i + size]] for i in range(0, len(unique), size)]


def ratios_from_batches(
    batches: Sequence[Mapping[str, float]], anchor: str
) -> dict[str, float | None]:
    """Mean interest per term in each batch -> keyword/anchor ratio. None if the anchor is 0."""
    ratios: dict[str, float | None] = {}
    for means in batches:
        anchor_mean = means.get(anchor, 0.0)
        for kw, mean in means.items():
            if kw == anchor:
                continue
            ratios[kw] = mean / anchor_mean if anchor_mean > 0 else None
    return ratios


def tier_for(volume: float, high: float = DEFAULT_HIGH, mid: float = DEFAULT_MID) -> Tier:
    if volume >= high:
        return "high"
    if volume >= mid:
        return "mid"
    return "low"


def resolve_base(
    anchor_volume: float | None, bing_impressions: float | None, engine_multiplier: float
) -> tuple[float | None, str]:
    if anchor_volume is not None and anchor_volume > 0:
        return float(anchor_volume), "user"
    if bing_impressions is not None and bing_impressions > 0:
        return float(bing_impressions) * engine_multiplier, "bing"
    return None, "none"


def estimate_volumes(
    keywords: Sequence[str],
    anchor: str,
    ratios: Mapping[str, float | None],
    *,
    geo: str = "",
    anchor_volume: float | None = None,
    bing_impressions: float | None = None,
    engine_multiplier: float = DEFAULT_ENGINE_MULTIPLIER,
    anchor_mean: float | None = None,
    high: float = DEFAULT_HIGH,
    mid: float = DEFAULT_MID,
) -> EstimateVolumesResult:
    base, base_source = resolve_base(anchor_volume, bing_impressions, engine_multiplier)
    weak_anchor = anchor_mean is not None and anchor_mean < WEAK_SIGNAL
    notes: list[str] = []
    if base is None:
        notes.append(
            "No absolute base: pass anchor_volume or configure a Bing key. Only ratios returned."
        )
    if weak_anchor:
        notes.append("Anchor has very low Trends interest; ratios are noisy. Pick a bigger anchor.")

    estimates: list[KeywordEstimate] = []
    for kw in (k for batch in batch_keywords(keywords, anchor) for k in batch[1:]):
        ratio = ratios.get(kw)
        if ratio is None:
            estimates.append(
                KeywordEstimate(
                    keyword=kw,
                    trends_ratio=None,
                    est_volume=None,
                    confidence="low",
                    method="no Trends data for this keyword or anchor",
                )
            )
            continue
        below = ratio == 0
        # Trends rounds to integers, so 0 means "under ~1% of the anchor", not "no searches".
        effective = 0.01 if below else ratio
        volume = round(effective * base) if base is not None else None
        if base_source == "user":
            method = "trends ratio x user anchor_volume"
            confidence = "medium"
        elif base_source == "bing":
            method = f"trends ratio x Bing anchor impressions x {engine_multiplier:g}"
            confidence = "low"
        else:
            method = "trends ratio only"
            confidence = "low"
        if below:
            method += " (upper bound: under 1% of anchor)"
        if below or weak_anchor:
            confidence = "low"
        estimates.append(
            KeywordEstimate(
                keyword=kw,
                trends_ratio=round(ratio, 4),
                est_volume=volume,
                below_threshold=below,
                tier=tier_for(volume, high, mid) if volume is not None else None,
                confidence=confidence,
                method=method,
            )
        )
    return EstimateVolumesResult(
        anchor=anchor,
        geo=geo,
        anchor_volume=base,
        base_source=base_source,
        estimates=estimates,
        notes=notes,
    )
