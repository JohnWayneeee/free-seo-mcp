# free-seo-mcp

Сбор семантики для AI-агентов без бюджета. [MCP](https://modelcontextprotocol.io)-сервер, который
собирает из бесплатных источников рабочую карту запросов без платных SEO-подписок.

[English version](README.md)

## Зачем

Реальная частота запросов Google доступна только в платных сервисах или в Ads-аккаунте с
расходами. Сервер вместо этого сводит бесплатные источники:

- **Автоподсказки** (Google, YouTube, Bing, DuckDuckGo) — что реально вводят люди. У фразы есть
  балл по позиции и по тому, как часто она повторяется в расширениях.
- **Google Trends** — соотношение спроса между запросами, растущие запросы, спрос по регионам.
- **Bing Webmaster API** — реальные показы по неделям (бесплатный ключ).
- **Reddit** — слова покупателей, их вопросы и возражения.
- **Сайты конкурентов** — URL из sitemap и структура страниц (title, description, h1–h3).

`estimate_volumes` связывает всё вместе. Каждый запрос сравнивается в Google Trends с одним
якорем, а якорю даётся абсолютное число: ваше или показы Bing × множитель. На выходе получается
оценка частоты в месяц, уровень ВЧ/СЧ/НЧ, `confidence` и `method` — откуда взялась цифра.

## Инструменты

| Инструмент | Что делает |
|---|---|
| `suggest` | Подсказки одного движка с позициями |
| `expand_alphabet` | сид + каждая буква алфавита, с баллами |
| `expand_questions` | вопросительные приставки языка, с баллами |
| `expand_multilingual` | один сид на нескольких локалях `hl:gl` |
| `trends_compare` | до 5 запросов на одной шкале 0–100 |
| `trends_related` | топовые и растущие связанные запросы |
| `trends_by_region` | спрос по странам и регионам |
| `bing_keyword` | показы Bing за период |
| `bing_related_keywords` | связанные запросы **с показами** |
| `bing_keyword_history` | показы по неделям |
| `estimate_volumes` | оценка частоты по якорю + уровень |
| `reddit_search` | треды: заголовок, рейтинг, комментарии, фрагмент |
| `sitemap_urls` | URL из sitemap сайта |
| `page_outline` | title, meta description, h1–h3, число слов |
| `keywords_save` / `keywords_load` | CSV-хранилище запросов по проекту и языку |

Prompt `keyword_research_workflow` — пошаговый рецепт для агента.

## Установка

Нужен [uv](https://docs.astral.sh/uv/).

```bash
git clone <этот репозиторий> free-seo-mcp
cd free-seo-mcp && uv sync
```

Claude Code:

```bash
claude mcp add free-seo -- uv run --directory /path/to/free-seo-mcp free-seo-mcp
```

Claude Desktop / Cursor — см. JSON-пример в [README.md](README.md#claude-desktop--cursor).

## Настройки

| Переменная | По умолчанию | Смысл |
|---|---|---|
| `FREE_SEO_BING_API_KEY` | — | Включает инструменты Bing и оценку по Bing |
| `FREE_SEO_DATA_DIR` | `./seo-data` | Хранилище CSV и кэш |
| `FREE_SEO_MIN_DELAY` | `0.4` | Пауза между запросами к одному хосту, сек |
| `FREE_SEO_PROXY` | — | HTTP(S)-прокси для всех запросов |
| `FREE_SEO_CACHE_TTL_DAYS` | `7` | Срок жизни кэша |

**Ключ Bing:** войти в Bing Webmaster Tools, добавить и подтвердить свой сайт, затем
Settings → API access → сгенерировать ключ.

## Ограничения

- Оценка — это оценка: уровни надёжны, точные числа приблизительны.
- Google Trends округляет редкие запросы до 0, они помечаются как «меньше 1% якоря».
- Эндпоинты автоподсказок, Trends и Reddit неофициальные и с лимитами. Сервер держит паузы,
  отступает на 429 и всё кэширует. Обхода капчи нет и не будет. Из некоторых сетей Reddit
  отвечает 403 — используйте `FREE_SEO_PROXY`.

## Лицензия

MIT
