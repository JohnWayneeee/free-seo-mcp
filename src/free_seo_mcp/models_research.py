"""Pydantic models for the research tools: Reddit, competitor sites and keyword storage."""

from pydantic import BaseModel, Field


class RedditPost(BaseModel):
    title: str
    subreddit: str
    score: int
    num_comments: int
    url: str
    created_utc: float
    snippet: str = Field(description="First characters of the post body, if any")


class RedditSearchResult(BaseModel):
    query: str
    subreddit: str | None
    posts: list[RedditPost]


class SitemapResult(BaseModel):
    site: str
    sitemaps: list[str] = Field(description="Sitemap files that were read")
    total_found: int = Field(description="Matching URLs found before the limit was applied")
    urls: list[str]


class PageOutline(BaseModel):
    url: str
    status: int
    title: str | None
    description: str | None
    h1: list[str]
    h2: list[str]
    h3: list[str]
    word_count: int


class KeywordRow(BaseModel):
    phrase: str
    geo: str = ""
    sources: list[str] = Field(default_factory=list)
    score: float | None = None
    trends_index: float | None = None
    bing_impressions: int | None = None
    est_volume: float | None = None
    tier: str = ""
    cluster: str = ""
    intent: str = ""
    notes: str = ""


class StoredKeyword(KeywordRow):
    lang: str
    updated_at: str


class SaveResult(BaseModel):
    path: str
    added: int
    updated: int
    total: int


class LoadResult(BaseModel):
    path: str
    total: int
    rows: list[StoredKeyword]
