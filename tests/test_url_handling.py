"""Offline regressions for URL identity, pagination and listing contracts."""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from xnxx_api import api as api


class EmptyStream:
    async def aclose(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration


class UrlHandlingTests(unittest.IsolatedAsyncioTestCase):
    async def test_filtered_profile_fetches_two_distinct_pages(self):
        media = api.User(
            url="https://www.xnxx.com/profile/Example/videos/best/7?quality=hd&page=9#videos", core=object()
        )
        capture = Mock(return_value=EmptyStream())
        from contextlib import ExitStack

        with ExitStack() as stack:
            for name in ("scrape_stream", "_scrape_stream"):
                if hasattr(api, name):
                    stack.enter_context(patch.object(api, name, capture))
            if hasattr(api, "Helper"):
                stack.enter_context(patch.object(api, "Helper", lambda **kwargs: SimpleNamespace(iterator=capture)))
            stack.enter_context(patch.object(api.User, "get_field", AsyncMock(return_value=2)))
            async for _ in media.videos(pages=2):
                pass
        urls = capture.call_args.kwargs["target_page_urls"]
        self.assertEqual(
            urls,
            [
                "https://www.xnxx.com/profile/Example/videos/best/0?quality=hd",
                "https://www.xnxx.com/profile/Example/videos/best/1?quality=hd",
            ],
        )

    def test_json_profile_entries_become_canonical_video_urls(self):
        body = json.dumps(
            {
                "videos": [
                    {
                        "id": 123,
                        "eid": "different",
                        "u": "/prof-video-click/upload/name/AbC123/title",
                        "tf": "Example",
                        "d": "10 min",
                        "n": "1.2M",
                    }
                ]
            }
        )
        rows = api.extractor_profile_json(body, base_url="https://de.xnxx.com")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["url"], "https://de.xnxx.com/video-different/title")
        self.assertEqual(rows[0]["title"], "Example")


if __name__ == "__main__":
    unittest.main()
