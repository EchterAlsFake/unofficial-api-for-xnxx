import pytest
from unittest.mock import patch
from urllib.parse import urlsplit
from xnxx_api import api


def test_search_query_is_one_value():
    client = object.__new__(api.Client)
    client.core = object()
    with patch.object(api, "scrape_stream") as stream:
        client.search_videos("a&b/# 日本", pages=2)
    urls = stream.call_args.kwargs["target_page_urls"]
    assert len(urls) == len(set(urls)) == 2
    for url in urls:
        assert urlsplit(url).path.endswith(("a%26b%2F%23%20%E6%97%A5%E6%9C%AC", "/1"))
        assert not urlsplit(url).fragment


@pytest.mark.asyncio
async def test_cli_closes_session_and_reports_false_download(capsys, tmp_path):
    from unittest.mock import AsyncMock, MagicMock
    from base_api import BaseCore
    from base_api.modules.config import RuntimeConfig

    core = BaseCore(RuntimeConfig())
    video = MagicMock(title="Example", length="10", url="https://example.com/video")
    video.load_fields = AsyncMock()
    video.download = AsyncMock(return_value=False)
    client = MagicMock()
    client.get_video = AsyncMock(return_value=video)
    with (
        patch.object(api, "BaseCore", return_value=core),
        patch.object(api, "Client", return_value=client),
    ):
        await api.run_main(
            ["--download", "https://example.com/video", "--output", str(tmp_path)]
        )
    assert core.session is None
    output = capsys.readouterr().out
    assert "Download complete:" not in output
    assert "Done ->" not in output
    assert "Download did not complete" in output


@pytest.mark.parametrize(
    "data",
    [
        '[{"@type":"VideoObject","name":"Example"}]',
        '{"@graph":[{"@type":"VideoObject","name":"Example"}]}',
    ],
)
def test_structured_video_metadata(data):
    video = api.Video(url="https://www.xnxx.com/video-abc/example", core=object())
    assert (
        video._extract_html('<script type="application/ld+json">' + data + "</script>")[
            "title"
        ]
        == "Example"
    )


def test_zero_video_profile():
    data = api.User._extract_data("", '{"nb_videos":0,"nb_per_page":0}')
    assert data["total_videos_count"] == data["total_pages_count"] == 0


@pytest.mark.asyncio
async def test_profile_stream_closes_on_early_stop():
    from types import SimpleNamespace

    closed = []

    async def source():
        try:
            yield SimpleNamespace(succeeded=True)
            yield SimpleNamespace(succeeded=True)
        finally:
            closed.append(True)

    user = api.User(
        url="https://www.xnxx.com/pornstar/example", core=object(), total_pages_count=1
    )
    with patch.object(api, "scrape_stream", side_effect=lambda **kwargs: source()):
        stream = user.videos(pages=1)
        await anext(stream)
        await stream.aclose()
    assert closed == [True]
