"""Tools: suggest, expand_alphabet, expand_questions, expand_multilingual."""

from mcp.server.mcpserver import Context, MCPServer
from mcp.types import ToolAnnotations

from ..analysis.scoring import score_suggestions
from ..locales import alphabet, parse_locale, question_prefixes
from ..models_autocomplete import (
    ExpansionResult,
    LocaleResult,
    MultilingualResult,
    ScoredSuggestion,
    Suggestion,
    SuggestResult,
)
from ..sources.autocomplete import AutocompleteError, Source, fetch_suggestions
from ..state import AppState

READ_ONLY = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=True)
DEFAULT_LOCALES = ["en:us", "es:es", "pt:br", "ru:ru"]


def _state(ctx: Context) -> AppState:
    return ctx.request_context.lifespan_context


def _ranked(items: list[str]) -> list[Suggestion]:
    return [Suggestion(phrase=s, position=i) for i, s in enumerate(items)]


async def _expand(
    ctx: Context, keyword: str, queries: list[str], hl: str, gl: str, sources: list[str]
) -> ExpansionResult:
    state = _state(ctx)
    total = len(queries) * len(sources)
    lists: list[tuple[str, list[str]]] = []
    errors: list[str] = []
    done = 0
    for source in sources:
        for q in queries:
            try:
                items = await fetch_suggestions(state.http, state.cache, source, q, hl, gl)
                lists.append((source, items))
            except AutocompleteError as exc:
                errors.append(f"{q!r}: {exc}")
            done += 1
            await ctx.report_progress(done, total, f"{source}: {q}")
    phrases = [
        ScoredSuggestion(
            phrase=p.phrase,
            score=round(p.score, 3),
            occurrences=p.occurrences,
            best_position=p.best_position,
            sources=sorted(p.sources),
        )
        for p in score_suggestions(lists)
    ]
    return ExpansionResult(
        keyword=keyword,
        hl=hl,
        gl=gl,
        sources=list(sources),
        queries=len(queries),
        phrases=phrases,
        errors=errors,
    )


def register(mcp: MCPServer) -> None:
    @mcp.tool(annotations=READ_ONLY)
    async def suggest(
        keyword: str, ctx: Context, source: Source = "google", hl: str = "en", gl: str = "us"
    ) -> SuggestResult:
        """Autocomplete suggestions for one query from a single engine, in rank order.

        source: google | youtube | bing | duckduckgo. hl: interface language (en, es, de...),
        gl: country (us, mx, de...). Position 0 is the most popular completion.
        """
        state = _state(ctx)
        items = await fetch_suggestions(state.http, state.cache, source, keyword, hl, gl)
        return SuggestResult(
            keyword=keyword, source=source, hl=hl, gl=gl, suggestions=_ranked(items)
        )

    @mcp.tool(annotations=READ_ONLY)
    async def expand_alphabet(
        keyword: str,
        ctx: Context,
        hl: str = "en",
        gl: str = "us",
        sources: list[Source] | None = None,
    ) -> ExpansionResult:
        """Expand a seed in breadth: the seed itself plus "seed a", "seed b"... per alphabet.

        Returns unique phrases ranked by a popularity score (appearances weighted by list
        position) with occurrence counts. sources defaults to ["google"]. Reports progress.
        """
        queries = [keyword] + [f"{keyword} {ch}" for ch in alphabet(hl)]
        return await _expand(ctx, keyword, queries, hl, gl, list(sources or ["google"]))

    @mcp.tool(annotations=READ_ONLY)
    async def expand_questions(
        keyword: str,
        ctx: Context,
        hl: str = "en",
        gl: str = "us",
        sources: list[Source] | None = None,
    ) -> ExpansionResult:
        """Expand a seed with question prefixes for the language (how to, why, best...).

        Surfaces informational intent similar to "People also ask". Phrases are scored like
        expand_alphabet. sources defaults to ["google"]. Reports progress.
        """
        queries = [f"{prefix} {keyword}" for prefix in question_prefixes(hl)]
        return await _expand(ctx, keyword, queries, hl, gl, list(sources or ["google"]))

    @mcp.tool(annotations=READ_ONLY)
    async def expand_multilingual(
        keyword: str,
        ctx: Context,
        locales: list[str] | None = None,
        source: Source = "google",
    ) -> MultilingualResult:
        """Run one seed through autocomplete in several locales at once.

        locales: "hl:gl" pairs such as ["en:us", "es:es", "pt:br"]; default en:us, es:es,
        pt:br, ru:ru. A failing locale reports its error field and does not break the others.
        """
        state = _state(ctx)
        chosen = locales or DEFAULT_LOCALES
        out: list[LocaleResult] = []
        for i, loc in enumerate(chosen, 1):
            hl, gl = parse_locale(loc)
            try:
                items = await fetch_suggestions(state.http, state.cache, source, keyword, hl, gl)
                out.append(LocaleResult(locale=loc, hl=hl, gl=gl, suggestions=_ranked(items)))
            except AutocompleteError as exc:
                out.append(LocaleResult(locale=loc, hl=hl, gl=gl, suggestions=[], error=str(exc)))
            await ctx.report_progress(i, len(chosen), loc)
        return MultilingualResult(keyword=keyword, source=source, locales=out)
