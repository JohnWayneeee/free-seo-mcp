"""Response models for the data-source tools: Google Trends, Bing Webmaster, volume estimates."""

from typing import Literal

from pydantic import BaseModel, Field


class TrendSeries(BaseModel):
    keyword: str
    mean: float = Field(description="Average interest over the timeframe (0-100 shared scale).")
    peak: int
    points: list[int] = Field(description="Interest values in chronological order.")


class TrendsCompareResult(BaseModel):
    geo: str
    timeframe: str
    dates: list[str] = Field(description="ISO dates matching each series' points.")
    series: list[TrendSeries]


class RelatedQuery(BaseModel):
    query: str
    value: int = Field(description="Top: relative score 0-100. Rising: growth in percent.")


class TrendsRelatedResult(BaseModel):
    keyword: str
    geo: str
    timeframe: str
    top: list[RelatedQuery]
    rising: list[RelatedQuery]


class RegionInterest(BaseModel):
    name: str
    code: str | None = None
    value: int


class TrendsByRegionResult(BaseModel):
    keyword: str
    geo: str
    resolution: str
    regions: list[RegionInterest]


class BingKeywordResult(BaseModel):
    query: str
    country: str
    language: str
    start_date: str
    end_date: str
    impressions: int = Field(description="Exact-match impressions on Bing for the period.")
    broad_impressions: int = Field(description="Impressions of queries containing the phrase.")


class BingRelatedResult(BaseModel):
    keyword: str
    country: str
    language: str
    start_date: str
    end_date: str
    related: list[BingKeywordResult]


class BingWeeklyPoint(BaseModel):
    date: str
    impressions: int
    broad_impressions: int


class BingHistoryResult(BaseModel):
    query: str
    country: str
    language: str
    weeks: list[BingWeeklyPoint]


Tier = Literal["high", "mid", "low"]


class KeywordEstimate(BaseModel):
    keyword: str
    trends_ratio: float | None = Field(description="Keyword mean interest / anchor mean interest.")
    est_volume: float | None = Field(description="Estimated monthly searches; null if no base.")
    below_threshold: bool = Field(
        default=False, description="Trends returned 0: volume is under ~1% of the anchor."
    )
    tier: Tier | None = None
    confidence: Literal["high", "medium", "low"]
    method: str = Field(description="How the number was derived.")


class EstimateVolumesResult(BaseModel):
    anchor: str
    geo: str
    anchor_volume: float | None
    base_source: Literal["user", "bing", "none"]
    estimates: list[KeywordEstimate]
    notes: list[str] = []
