"""Structured outputs of the autocomplete tools."""

from pydantic import BaseModel, Field


class Suggestion(BaseModel):
    phrase: str
    position: int = Field(description="0-based rank in the list; lower means more popular")


class SuggestResult(BaseModel):
    keyword: str
    source: str
    hl: str
    gl: str
    suggestions: list[Suggestion]


class ScoredSuggestion(BaseModel):
    phrase: str
    score: float = Field(description="Sum of position weights over all appearances")
    occurrences: int = Field(description="How many expansion queries returned this phrase")
    best_position: int
    sources: list[str]


class ExpansionResult(BaseModel):
    keyword: str
    hl: str
    gl: str
    sources: list[str]
    queries: int = Field(description="Expansion queries sent per source")
    phrases: list[ScoredSuggestion]
    errors: list[str] = Field(default_factory=list, description="Failed source/query pairs")


class LocaleResult(BaseModel):
    locale: str
    hl: str
    gl: str
    suggestions: list[Suggestion]
    error: str | None = None


class MultilingualResult(BaseModel):
    keyword: str
    source: str
    locales: list[LocaleResult]
