import pytest


@pytest.mark.anyio
async def test_server_starts_and_lists_tools(client):
    result = await client.list_tools()
    assert isinstance(result.tools, list)
