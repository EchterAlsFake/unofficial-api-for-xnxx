import pytest
from base_api import DownloadConfigHLS

from ..api import Client
url = "https://www.xnxx.com/video-1b9bufc9/die_zierliche_stieftochter_passt_kaum_in_den_mund_ihres_stiefvaters"
# This will be the URL for all tests

@pytest.mark.asyncio
async def test_all():
    client = Client()
    video = await client.get_video(url, load_html=True)

    assert isinstance(video.title, str) and len(video.title) > 0
    assert isinstance(video.thumbnail, str) and len(video.thumbnail) > 0
    assert isinstance(video.m3u8_base_url, str) and len(video.m3u8_base_url) > 0

    config = DownloadConfigHLS(quality="worst", remux=True, return_report=True)
    config_2 = DownloadConfigHLS(quality="worst", remux=False, return_report=True)
    fortnite_1 = await video.download(config)
    fortnite_2 = await video.download(config_2)

    assert fortnite_1.status == "completed"
    assert fortnite_2.status == "completed"

