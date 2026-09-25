import gzip

import httpx
import pytest
import respx

from free_seo_mcp.sources.site import outline, parse_robots

NS = 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'
INDEX = f"""<?xml version="1.0"?><sitemapindex {NS}>
<sitemap><loc>https://example.com/sitemap-pages.xml</loc></sitemap>
<sitemap><loc>https://example.com/sitemap-blog.xml.gz</loc></sitemap>
</sitemapindex>"""
PAGES = f"""<urlset {NS}><url><loc>https://example.com/</loc></url>
<url><loc>https://example.com/shop/shoes</loc></url></urlset>"""
BLOG = f"""<urlset {NS}><url><loc>https://example.com/blog/how-to-run</loc></url>
<url><loc>https://example.com/shop/shoes</loc></url></urlset>"""


def test_parse_robots():
    text = "User-agent: *\nDisallow: /x\nSitemap: https://example.com/a.xml\nsitemap: /b.xml\n"
    assert parse_robots(text, "https://example.com") == [
        "https://example.com/a.xml",
        "https://example.com/b.xml",
    ]


@pytest.mark.anyio
async def test_sitemap_index_recursion_and_gzip(client):
    with respx.mock:
        respx.get("https://example.com/robots.txt").mock(
            return_value=httpx.Response(200, text="Sitemap: https://example.com/sitemap_index.xml")
        )
        respx.get("https://example.com/sitemap_index.xml").mock(
            return_value=httpx.Response(200, text=INDEX)
        )
        respx.get("https://example.com/sitemap-pages.xml").mock(
            return_value=httpx.Response(200, text=PAGES)
        )
        respx.get("https://example.com/sitemap-blog.xml.gz").mock(
            return_value=httpx.Response(200, content=gzip.compress(BLOG.encode()))
        )
        res = await client.call_tool("sitemap_urls", {"site": "example.com"})
        filtered = await client.call_tool(
            "sitemap_urls", {"site": "https://example.com/", "contains": "BLOG", "limit": 10}
        )
    data = res.structured_content
    assert data["site"] == "https://example.com"
    assert len(data["sitemaps"]) == 3
    assert data["urls"] == [
        "https://example.com/",
        "https://example.com/shop/shoes",
        "https://example.com/blog/how-to-run",
    ]
    assert filtered.structured_content["urls"] == ["https://example.com/blog/how-to-run"]


@pytest.mark.anyio
async def test_sitemap_fallback_without_robots(client):
    with respx.mock:
        respx.get("https://example.org/robots.txt").mock(return_value=httpx.Response(404))
        respx.get("https://example.org/sitemap.xml").mock(
            return_value=httpx.Response(200, text=PAGES)
        )
        res = await client.call_tool("sitemap_urls", {"site": "example.org", "limit": 1})
    assert res.structured_content["total_found"] == 2
    assert len(res.structured_content["urls"]) == 1


HTML = """<html><head><title> Running Shoes Guide </title>
<meta name="Description" content="Pick the right pair.">
<style>.a{color:red}</style><script>var x = "not words here";</script></head>
<body><h1>Running <b>shoes</b></h1><p>One two three.</p>
<h2>Road</h2><h2>Trail</h2><h3>Fit</h3></body></html>"""


def test_outline_parser():
    o = outline(HTML, "https://example.com/g", 200)
    assert o.title == "Running Shoes Guide"
    assert o.description == "Pick the right pair."
    assert o.h1 == ["Running shoes"]
    assert o.h2 == ["Road", "Trail"]
    assert o.h3 == ["Fit"]
    # h1(2) + p(3) + h2(2) + h3(1); title, style and script are excluded
    assert o.word_count == 8


@pytest.mark.anyio
async def test_page_outline_tool(client):
    with respx.mock:
        respx.get("https://example.com/g").mock(return_value=httpx.Response(200, html=HTML))
        res = await client.call_tool("page_outline", {"url": "example.com/g"})
    assert res.structured_content["title"] == "Running Shoes Guide"
    assert res.structured_content["status"] == 200


@pytest.mark.live
@pytest.mark.anyio
async def test_sitemap_live(client):
    res = await client.call_tool("sitemap_urls", {"site": "docs.python.org", "limit": 5})
    assert res.structured_content["urls"]
