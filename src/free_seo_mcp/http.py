"""Polite shared HTTP client: per-host spacing, backoff on 429/5xx, one honest UA."""

import time
from urllib.parse import urlparse

import anyio
import httpx

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 free-seo-mcp"
)


class PoliteClient:
    def __init__(self, min_delay: float = 0.4, proxy: str | None = None, retries: int = 3) -> None:
        self._client = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            timeout=15,
            follow_redirects=True,
            proxy=proxy,
        )
        self._min_delay = min_delay
        self._retries = retries
        self._last: dict[str, float] = {}
        self._lock = anyio.Lock()

    async def _space(self, host: str) -> None:
        async with self._lock:
            wait = self._last.get(host, 0) + self._min_delay - time.monotonic()
            if wait > 0:
                await anyio.sleep(wait)
            self._last[host] = time.monotonic()

    async def get(self, url: str, **kwargs) -> httpx.Response:
        host = urlparse(url).netloc
        delay = 1.0
        for attempt in range(self._retries + 1):
            await self._space(host)
            resp = await self._client.get(url, **kwargs)
            if resp.status_code != 429 and resp.status_code < 500:
                return resp
            if attempt < self._retries:
                await anyio.sleep(delay)
                delay *= 2
        return resp

    async def aclose(self) -> None:
        await self._client.aclose()
