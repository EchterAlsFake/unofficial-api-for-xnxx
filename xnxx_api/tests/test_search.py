import pytest
from ..api import Client

@pytest.mark.asyncio
async def test_all():
    client = Client()
    idx = 0
    async for video in client.search_videos("test"):
        idx += 1
        assert isinstance(video.video.title, str)

        if idx == 3:
            break