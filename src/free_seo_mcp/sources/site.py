"""Competitor site helpers: sitemap discovery/parsing and a stdlib HTML outline."""

import gzip
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

from ..http import PoliteClient
from ..models_research import PageOutline

# Bounds a hostile or huge sitemap tree so one call cannot fan out indefinitely.
MAX_SITEMAPS = 50
MAX_DEPTH = 3


def normalize_site(site: str) -> str:
    if "://" not in site:
        site = f"https://{site}"
    p = urlparse(site)
    return f"{p.scheme}://{p.netloc}"


def parse_robots(text: str, base: str) -> list[str]:
    out = []
    for line in text.splitlines():
        key, _, value = line.partition(":")
        if key.strip().lower() == "sitemap" and value.strip():
            out.append(urljoin(base, value.strip()))
    return out


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_sitemap(content: bytes) -> tuple[list[str], list[str]]:
    """Return (page urls, child sitemap urls) from a urlset or sitemapindex document."""
    if content[:2] == b"\x1f\x8b":
        content = gzip.decompress(content)
    root = ElementTree.fromstring(content)
    locs = [
        (el.text or "").strip()
        for el in root.iter()
        if _local(el.tag) == "loc" and (el.text or "").strip()
    ]
    if _local(root.tag) == "sitemapindex":
        return [], locs
    return locs, []


async def collect_urls(http: PoliteClient, site: str) -> tuple[list[str], list[str]]:
    """Return (sitemaps read, page urls), following robots.txt and sitemap indexes."""
    base = normalize_site(site)
    queue: list[tuple[str, int]] = []
    robots = await http.get(f"{base}/robots.txt")
    if robots.status_code == 200:
        queue = [(u, 0) for u in parse_robots(robots.text, base)]
    if not queue:
        queue = [(f"{base}/sitemap.xml", 0)]

    seen: set[str] = set()
    read: list[str] = []
    urls: list[str] = []
    while queue and len(seen) < MAX_SITEMAPS:
        url, depth = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        resp = await http.get(url)
        if resp.status_code != 200:
            continue
        try:
            pages, children = parse_sitemap(resp.content)
        except (ElementTree.ParseError, OSError, EOFError):
            continue
        read.append(url)
        urls.extend(pages)
        if depth < MAX_DEPTH:
            queue.extend((c, depth + 1) for c in children)
    return read, list(dict.fromkeys(urls))


class _OutlineParser(HTMLParser):
    SKIP = {"script", "style", "noscript", "template", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str | None = None
        self.description: str | None = None
        self.headings: dict[str, list[str]] = {"h1": [], "h2": [], "h3": []}
        self.words = 0
        self._stack: list[str] = []
        self._buf: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag == "meta":
            a = {k.lower(): (v or "") for k, v in attrs}
            if a.get("name", "").lower() == "description" and self.description is None:
                self.description = a.get("content", "").strip()
        elif tag in ("title", "h1", "h2", "h3"):
            self._stack.append(tag)
            self._buf = []

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self._skip = max(0, self._skip - 1)
        elif self._stack and tag == self._stack[-1]:
            self._stack.pop()
            text = " ".join("".join(self._buf).split())
            if tag == "title":
                if self.title is None:
                    self.title = text
            elif text:
                self.headings[tag].append(text)

    def handle_data(self, data):
        if self._skip:
            return
        if self._stack:
            self._buf.append(data)
        if not self._stack or self._stack[-1] != "title":
            self.words += len(re.findall(r"\w+", data))


def outline(html: str, url: str, status: int) -> PageOutline:
    p = _OutlineParser()
    p.feed(html)
    p.close()
    return PageOutline(
        url=url,
        status=status,
        title=p.title,
        description=p.description,
        h1=p.headings["h1"],
        h2=p.headings["h2"],
        h3=p.headings["h3"],
        word_count=p.words,
    )


async def page_outline(http: PoliteClient, url: str) -> PageOutline:
    if "://" not in url:
        url = f"https://{url}"
    resp = await http.get(url)
    return outline(resp.text, str(resp.url), resp.status_code)
