"""Tools: keywords_save, keywords_load; prompt: keyword_research_workflow."""

from typing import Annotated

from mcp.server.mcpserver import Context, MCPServer
from mcp_types import ToolAnnotations
from pydantic import Field

from .. import storage
from ..models_research import KeywordRow, LoadResult, SaveResult
from ..state import AppState

NAME_HINT = "1-64 letters, digits, '-' or '_'"

WORKFLOW = """Run a keyword research session for the seed(s): {seeds}
Language: {lang}, geo: {geo}, project: {project}.

1. Expand each seed with expand_alphabet and expand_questions (and suggest on other sources).
   Keep phrases with a high popularity score or many occurrences.
2. Compare demand: trends_compare on up to 5 phrases, trends_related for new ideas.
   If a Bing key is configured, use bing_keyword / bing_related_keywords for real impressions.
3. Estimate volumes with estimate_volumes, using a well-known phrase as the anchor.
   Mark tiers (high / mid / low frequency) and keep the confidence and method fields in mind.
4. Check buyer language with reddit_search and competitor structure with sitemap_urls and
   page_outline.
5. Group phrases into clusters by shared intent (informational, commercial, transactional,
   navigational) and topic.
6. Save everything with keywords_save(project="{project}", lang="{lang}", rows=...), filling
   sources, score, trends_index, bing_impressions, est_volume, tier, cluster and intent.
   Review the result with keywords_load.
"""


def register(mcp: MCPServer) -> None:
    @mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False))
    async def keywords_save(
        project: Annotated[str, Field(description=f"Project folder name ({NAME_HINT})")],
        lang: Annotated[str, Field(description=f"Language code used as file name ({NAME_HINT})")],
        rows: list[KeywordRow],
        ctx: Context,
    ) -> SaveResult:
        """Merge keyword rows into the project's CSV store (<data_dir>/<project>/<lang>.csv).

        Rows are deduplicated by normalized phrase (case and whitespace insensitive): new
        non-empty fields overwrite stored ones and sources are merged.
        """
        state: AppState = ctx.request_context.lifespan_context
        path, added, updated, total = storage.save(state.settings.data_dir, project, lang, rows)
        return SaveResult(path=str(path), added=added, updated=updated, total=total)

    @mcp.tool(annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True))
    async def keywords_load(
        project: str,
        lang: str,
        ctx: Context,
        tier: Annotated[str | None, Field(description="Only rows with this tier")] = None,
        cluster: Annotated[str | None, Field(description="Only rows with this cluster")] = None,
    ) -> LoadResult:
        """Load saved keywords for a project and language, optionally filtered by tier/cluster."""
        state: AppState = ctx.request_context.lifespan_context
        path, rows = storage.load(state.settings.data_dir, project, lang, tier, cluster)
        return LoadResult(path=str(path), total=len(rows), rows=rows)

    @mcp.prompt()
    def keyword_research_workflow(
        seeds: str, lang: str = "en", geo: str = "US", project: str = "default"
    ) -> str:
        """Step-by-step keyword research plan using this server's tools."""
        return WORKFLOW.format(seeds=seeds, lang=lang, geo=geo, project=project)
