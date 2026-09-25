"""free-seo-mcp entry point: builds the server and registers every tool module."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.mcpserver import MCPServer

from .cache import DiskCache
from .config import Settings
from .http import PoliteClient
from .state import AppState
from .tools import autocomplete, bing, reddit, site, storage, trends


@asynccontextmanager
async def lifespan(_server: MCPServer) -> AsyncIterator[AppState]:
    settings = Settings.from_env()
    http = PoliteClient(settings.min_delay, settings.proxy)
    cache = DiskCache(settings.data_dir / ".cache" / "cache.sqlite", settings.cache_ttl_days)
    try:
        yield AppState(settings=settings, http=http, cache=cache)
    finally:
        await http.aclose()
        cache.close()


def build_server() -> MCPServer:
    mcp = MCPServer("free-seo", lifespan=lifespan)
    for module in (autocomplete, trends, bing, reddit, site, storage):
        module.register(mcp)
    return mcp


mcp = build_server()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
