# free-seo-mcp

Zero-budget keyword research for AI agents. An [MCP](https://modelcontextprotocol.io) server that
combines free data sources into a usable keyword map — no paid SEO subscription required.

[Русская версия](README.ru.md)

## Why

Real Google search volume is only available through paid tools or an Ads account with spend.
This server triangulates it from free sources instead:

- **Autocomplete** (Google, YouTube, Bing, DuckDuckGo) — what people actually type, scored by
  position and how often a phrase recurs across expansions.
- **Google Trends** — relative demand between keywords, rising queries, demand by region.
- **Bing Webmaster API** — real weekly impression counts (free API key).
- **Reddit** — the words buyers use, their questions and objections.
- **Competitor sites** — sitemap URLs and page outlines (title, description, h1–h3).

`estimate_volumes` ties them together: every keyword is compared to one anchor in Google Trends,
and the anchor gets an absolute number (yours, or Bing impressions × a multiplier). The result is
an estimated monthly volume with a high/mid/low tier, a `confidence` and the `method` used.

## Tools

| Tool | What it does |
|---|---|
| `suggest` | Autocomplete from one engine, with positions |
| `expand_alphabet` | seed + every letter of the language's alphabet, scored |
| `expand_questions` | question prefixes (how/why/what…) per language, scored |
| `expand_multilingual` | one seed across several `hl:gl` locales |
| `trends_compare` | up to 5 keywords on one 0–100 scale |
| `trends_related` | top and rising related queries |
| `trends_by_region` | demand by country/region |
| `bing_keyword` | Bing impressions for a period |
| `bing_related_keywords` | related keywords **with impressions** |
| `bing_keyword_history` | weekly impression series |
| `estimate_volumes` | anchor-based volume estimate + tier |
| `reddit_search` | threads: title, score, comments, snippet |
| `sitemap_urls` | URLs from a site's sitemap(s) |
| `page_outline` | title, meta description, h1–h3, word count |
| `keywords_save` / `keywords_load` | persistent CSV keyword store per project and language |

Prompt: `keyword_research_workflow` — a step-by-step recipe for the agent.

## Install

Requires [uv](https://docs.astral.sh/uv/).

```bash
git clone <this repo> free-seo-mcp
cd free-seo-mcp && uv sync
```

### Claude Code

```bash
claude mcp add free-seo -- uv run --directory /path/to/free-seo-mcp free-seo-mcp
```

### Claude Desktop / Cursor

```json
{
  "mcpServers": {
    "free-seo": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/free-seo-mcp", "free-seo-mcp"],
      "env": { "FREE_SEO_DATA_DIR": "/path/to/seo-data" }
    }
  }
}
```

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `FREE_SEO_BING_API_KEY` | — | Enables the Bing tools and Bing-based estimates |
| `FREE_SEO_DATA_DIR` | `./seo-data` | CSV keyword store and cache |
| `FREE_SEO_MIN_DELAY` | `0.4` | Seconds between requests to one host |
| `FREE_SEO_PROXY` | — | HTTP(S) proxy for all requests |
| `FREE_SEO_CACHE_TTL_DAYS` | `7` | Disk cache lifetime |

**Bing API key:** sign in to Bing Webmaster Tools, add and verify a site you own,
then Settings → API access → generate a key.

## Limits and fair use

- Estimates are estimates. Treat tiers as reliable and exact numbers as rough.
- Google Trends rounds small keywords to 0; these are reported as "below 1% of the anchor".
- Autocomplete, Trends and Reddit endpoints are unofficial and rate-limited. The server spaces
  requests, backs off on 429, and caches everything on disk. There is no CAPTCHA solving and
  there never will be. Some networks get 403 from Reddit — use `FREE_SEO_PROXY`.

## Development

```bash
uv run ruff check && uv run ruff format --check
uv run pytest -q          # offline, mocked
uv run pytest -m live     # hits real endpoints
```

## License

MIT
