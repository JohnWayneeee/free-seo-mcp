import pytest
from mcp import Client

from free_seo_mcp.server import build_server


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("FREE_SEO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("FREE_SEO_MIN_DELAY", "0")
    monkeypatch.delenv("FREE_SEO_BING_API_KEY", raising=False)
    return tmp_path


@pytest.fixture
async def client(data_dir):
    async with Client(build_server(), raise_exceptions=True) as c:
        yield c
