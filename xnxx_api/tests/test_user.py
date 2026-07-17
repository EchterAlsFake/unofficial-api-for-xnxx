from ..api import Client
import pytest

@pytest.mark.asyncio
async def test_all():
    client = Client()

    user = await client.get_user("https://www.xnxx.com/pornstar/cory-chase")

    assert isinstance(user.total_videos_views, str)
    assert isinstance(user.total_videos_count, int)
    assert isinstance(user.total_pages_count, int)

    idx = 0
    async for video in user.videos():
        idx += 1
        assert isinstance(video.video.title, str)
        if idx == 3:
            break

