# free-seo-mcp: free keyword research MCP server

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![MCP](https://img.shields.io/badge/MCP-server-purple.svg)](https://modelcontextprotocol.io)

Keyword research for Claude, Cursor and any MCP client, with a $0 budget. You get search
suggestions, Google Trends, real Bing search volume, Reddit threads and competitor sitemaps in
one server. No Ahrefs, Semrush or DataForSEO subscription.

[Русская версия](README.ru.md)

## What you can ask your agent

> Expand "running shoes" in English and Spanish, estimate volumes against "trail running shoes",
> split them into high/mid/low and save to project `shoes`.

> Pull every URL from the competitor's sitemap and outline their top 10 pages.

> Find Reddit threads where people complain about running shoes and list their exact words.

## Why it exists

Google shows exact search volume only to advertisers who spend money. Paid SEO tools resell
estimates of that number. free-seo-mcp builds its own estimate from free sources:

| Source | What you get |
|---|---|
| Google, YouTube, Bing, DuckDuckGo autocomplete | Phrases people type, scored by position and repeat count |
| Google Trends | Relative demand, rising queries, demand by country |
| Bing Webmaster API | Real weekly impressions (free API key) |
| Reddit | Buyer language, questions, objections |
| Competitor sites | Sitemap URLs, title, description, h1 to h3 |

`estimate_volumes` compares each keyword with one anchor in Google Trends. It gives the anchor an
absolute number: your own figure, or Bing impressions times a multiplier. Each keyword comes back
with an estimated monthly volume, a high/mid/low tier, a confidence level and the method used.

## Tools

| Tool | Purpose |
|---|---|
| `suggest` | Autocomplete from one engine, with positions |
| `expand_alphabet` | Seed plus each letter of the alphabet, scored |
| `expand_questions` | Question prefixes per language (how, why, what is...) |
| `expand_multilingual` | One seed across several `hl:gl` locales |
| `trends_compare` | Up to 5 keywords on one 0 to 100 scale |
| `trends_related` | Top and rising related queries |
| `trends_by_region` | Demand by country or region |
| `bing_keyword` | Bing impressions for a period |
| `bing_related_keywords` | Related keywords with impressions |
| `bing_keyword_history` | Weekly impression series |
| `estimate_volumes` | Volume estimate and tier for a keyword list |
| `reddit_search` | Threads with score, comment count and snippet |
| `sitemap_urls` | Every URL from a site's sitemaps |
| `page_outline` | Title, meta description, headings, word count |
| `keywords_save`, `keywords_load` | CSV keyword store per project and language |

The `keyword_research_workflow` prompt walks the agent through seeds, expansion, estimates,
clusters and saving.

Languages with built-in alphabets and question prefixes: English, Russian, Spanish, Portuguese,
German, French, Italian. Any other `hl:gl` pair works for autocomplete and Trends.

## Quick start

Install [uv](https://docs.astral.sh/uv/), then:

```bash
git clone https://github.com/JohnWayneeee/free-seo-mcp.git
cd free-seo-mcp
uv sync
```

**Claude Code**

```bash
claude mcp add free-seo -- uv run --directory /path/to/free-seo-mcp free-seo-mcp
```

**Claude Desktop, Cursor, Windsurf**

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
| `FREE_SEO_BING_API_KEY` | none | Turns on Bing tools and Bing-based estimates |
| `FREE_SEO_DATA_DIR` | `./seo-data` | Keyword CSVs and cache |
| `FREE_SEO_MIN_DELAY` | `0.4` | Seconds between requests to one host |
| `FREE_SEO_PROXY` | none | HTTP(S) proxy for every request |
| `FREE_SEO_CACHE_TTL_DAYS` | `7` | Cache lifetime |

Get a Bing key: sign in to Bing Webmaster Tools, add and verify your site, open Settings, then
API access, and generate a key.

## Limits

- Trust the tiers more than the exact numbers.
- Google Trends rounds rare keywords to 0. The server reports them as "below 1% of the anchor".
- Autocomplete, Trends and Reddit use unofficial endpoints with rate limits. The server waits
  between requests, backs off on HTTP 429 and caches results on disk. It does not solve CAPTCHAs.
- Reddit returns 403 to some networks. Set `FREE_SEO_PROXY` if you hit it.

## Development

```bash
uv run ruff check && uv run ruff format --check
uv run pytest -q          # offline, mocked
uv run pytest -m live     # real endpoints
```

Pull requests welcome. New autocomplete engines and language packs are the easiest place to start.

## License

MIT

---

☕ Saved you a keyword tool subscription? [Buy me a coffee](https://buymeacoffee.com/JohnWayne) or star the repo.
