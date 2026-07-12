import asyncio
import os
import re
import html
import json
import logging
import argparse
import threading
import math

from typing import AsyncGenerator
from functools import cached_property
from dataclasses import dataclass, fields
from curl_cffi import Response, AsyncSession
from base_api.modules.static_functions import str_to_bool
from base_api import BaseCore, Helper, BaseMedia, ScrapeResult
from base_api.modules.errors import NetworkRequestError, InvalidProxy, BotProtectionDetected, UnknownError, ResourceGone
from selectolax.lexbor import LexborHTMLParser

from xnxx_api.modules.errors import (NetworkError, ProxyError, UnknownNetworkError, NotFound, BotDetection,
                                     InvalidResponse, RegionBlocked)
from xnxx_api.modules.consts import headers
from xnxx_api.modules.type_hints import on_error_hint
from xnxx_api.modules.search_filters import SearchingQuality, Mode, Length, UploadTime


async def on_error(url: str, error: Exception, attempt: int) -> bool:
    print(f"URL: {url}, ERROR: {error}, Attempt: {attempt}")

    if isinstance(error, ResourceGone):
        return False

    return True


async def get_html_content(core: BaseCore, url: str) -> str | None | dict:
    # What should I do here?
    try:
        content = await core.fetch(url)
        if isinstance(content, str):
            return content

        if isinstance(content, Response):
            raise RegionBlocked(f"The Video: {url} is not available in your country!")

    except NetworkRequestError as e:
        raise NetworkError(str(e)) from e

    except InvalidProxy as e:
        raise ProxyError(str(e)) from e

    except BotProtectionDetected as e:
        raise BotDetection(str(e)) from e

    except UnknownError as e:
        raise UnknownNetworkError(str(e)) from e



@dataclass(kw_only=True, slots=True)
class Video(BaseMedia):
    url: str
    core: BaseCore

    async def _perform_load(self, api: bool, html: bool, anything_else: bool):
        if html:
            await asyncio.gather(self._fetch_html())

    async def _fetch_html(self):
        html_content = await get_html_content(core=self.core, url=self.url)
        assert isinstance(html_content, str)
        data: dict = await asyncio.to_thread(self._extract_html, html_content)
        allowed_fields = [field.name for field in fields(self)]
        for key, value in data.items():
            if key in allowed_fields:
                setattr(self, key, value)

    @staticmethod
    def _extract_html(html_content: str) -> dict:
        parser = LexborHTMLParser(html_content)

        _script = parser.css_first('script[type="application/ld+json"]')
        script: dict = json.loads(_script.text())

        title = html.unescape(script.get("title"))
        description = html.unescape(script.get("description"))
        thumbnail_url = html.unescape(script.get("thumbnailUrl").get("thumbnail_url"))
        publish_date = html.unescape(script.get("uploadDate"))
        length = html.unescape(script.get("duration"))
        m3u8_base_url = script.get("contentUrl")
        views = script.get("interactionStatistic").get("userInteractionCount")

        return {
            "title": title,
            "description": description,
            "thumbnail_url": thumbnail_url,
            "publish_date": publish_date,
            "length": length,
            "m3u8_base_url": m3u8_base_url,
            "views": views
        }



class Search(Helper):
    def __init__(self, query: str, core: BaseCore, upload_time: str | UploadTime, length: str | Length, searching_quality:
                                                str | SearchingQuality, mode: str | Mode):
        super().__init__(core, video_constructor=Video)

        self.core = core
        self.query = self.validate_query(query)
        self.upload_time = upload_time
        self.length = length
        self.searching_quality = searching_quality
        self.mode = mode
        self.html_content: str | None | dict = None
        self.logger = setup_logger(name="XNXX API - [Search]", log_file=None, level=logging.CRITICAL)

    def enable_logging(self, log_file, level, log_ip: str | None = None, log_port: int | None = None):
        self.logger = setup_logger(name="XNXX API - [Search]", log_file=log_file, level=level, http_ip=log_ip, http_port=log_port)

    @classmethod
    def validate_query(cls, query):
        return query.replace(" ", "+")

    async def init(self):
        if not self.html_content:
            self.html_content = await get_html_content(core=self.core, url=f"https://www.xnxx.com/search{self.mode}{self.upload_time}{self.length}{self.searching_quality}/{self.query}")

        assert isinstance(self.html_content, str)
        return self

    @cached_property
    def total_pages(self) -> str:
        return REGEX_SEARCH_TOTAL_PAGES.search(self.html_content).group(1)

    async def videos(self, pages_concurrency: int | None = None, videos_concurrency: int | None = None,  pages: int = 0,
                     on_video_error: on_error_hint = on_error,
                     on_page_error: on_error_hint = None
                     ) -> AsyncGenerator[Video, None]:
        self.url = f"https://www.xnxx.com/search{self.mode}{self.upload_time}{self.length}{self.searching_quality}/{self.query}"

        if pages >= int(self.total_pages):
            self.logger.warning(f"You want to fetch: {pages}, but only: {self.total_pages} are available. Reducing!")
            pages = int(self.total_pages)

        page_urls = [self.url]
        page_urls.extend([f"{self.url}/{page}" for page in range(1, int(pages))])
        videos_concurrency = (videos_concurrency or self.core.configuration.videos_concurrency)
        pages_concurrency = pages_concurrency or self.core.configuration.pages_concurrency
        assert videos_concurrency and pages_concurrency
        async for video in self.iterator(target_page_urls=page_urls, max_video_concurrency=videos_concurrency,
                                 max_page_concurrency=pages_concurrency, video_link_extractor=extractor_html,
                                         on_video_error=on_video_error, on_page_error=on_page_error):
            if isinstance(video, Video):
                yield video

class User(Helper):
    def __init__(self, url: str, core: BaseCore):
        super().__init__(core, video_constructor=Video)
        self.url = url
        self.core = core
        self.content: str | None | dict = None
        self._base_json: None | dict = None
        self.logger = setup_logger(name="XNXX API - [User]", log_file=None, level=logging.CRITICAL)

    def enable_logging(self, file, level, log_ip: str | None = None, log_port: int | None = None):
        self.logger = setup_logger(name="XNXX API - [User]", log_file=file, level=level, http_ip=log_ip, http_port=log_port)

    async def init(self):
        if not self.content:
            self.content = await get_html_content(core=self.core, url=self.url)

        assert isinstance(self.content, str)

        url = f"{self.url}/videos/best/0"
        content = await get_html_content(core=self.core, url=url)
        assert isinstance(content, str)
        self._base_json = json.loads(html.unescape(content))

        return self

    @cached_property
    def base_json(self):
        if not self._base_json:
            raise ValueError("You probably forgot to call init")

        return self._base_json

    async def videos(self, videos_concurrency: int | None = None, pages_concurrency: int | None = None,
               pages: int = 0, on_video_error: on_error_hint = on_error, on_page_error: on_error_hint = None
                     ) -> AsyncGenerator[Video, None]:

        if pages >= self.total_pages:
            self.logger.warning(f"You are trying to fetch more pages than there are... Reducing to: {self.total_pages}")
            pages = int(self.total_pages)

        page_urls = [f"{self.url}/videos/best/{page}" for page in range(pages)]
        videos_concurrency = videos_concurrency or self.core.configuration.videos_concurrency
        pages_concurrency = pages_concurrency or self.core.configuration.pages_concurrency
        assert videos_concurrency and pages_concurrency
        async for video in self.iterator(target_page_urls=page_urls, max_video_concurrency=videos_concurrency,
                                 max_page_concurrency=pages_concurrency, video_link_extractor=extractor_html,
                                         on_video_error=on_video_error, on_page_error=on_page_error):
            if isinstance(video, Video):
                yield video


    @cached_property
    def total_videos(self) -> int:
        return int(self.base_json["nb_videos"])

    @cached_property
    def total_pages(self) -> int:
        return int(math.ceil(self.total_videos / int(self.base_json["nb_per_page"])))

    @cached_property
    def total_video_views(self) -> str:
        return REGEX_MODEL_TOTAL_VIDEO_VIEWS.search(self.content).group(1)


class Client:
    def __init__(self, core: BaseCore = BaseCore()):
        self.core = core
        self.core.initialize_session()
        assert isinstance(self.core.session, AsyncSession)
        self.core.session.headers.update({"Referer": "https://www.xnxx.com/"})

    async def get_video(self, url) -> Video:
        """
        :param url: (str) The URL of the video
        :return: (Video) The video object
        """
        video = Video(url, core=self.core)
        return await video.init()

    async def search(self, query: str, upload_time: str | UploadTime = "", length: str | Length = "",
               searching_quality: str | SearchingQuality = "", mode: str | Mode = "") -> Search:
        """
        :param query:
        :param upload_time:
        :param length:
        :param searching_quality:
        :param mode:
        :return: (Search) the search object
        """
        search = Search(query=query, core=self.core, upload_time=upload_time, length=length,
        searching_quality=searching_quality, mode=mode)
        return await search.init()

    async def get_user(self, url: str) -> User:
        """
        :param url: (str) The user URL
        :return: (User) The User object
        """
        user = User(url, core=self.core)
        return await user.init()


async def main():
    parser = argparse.ArgumentParser(description="API Command Line Interface")
    parser.add_argument("--download", metavar="URL (str)", type=str, help="URL to download from")
    parser.add_argument("--quality", metavar="best,half,worst", type=str, help="The video quality (best,half,worst)", required=True)
    parser.add_argument("--file", metavar="Source to .txt file", type=str, help="(Optional) Specify a file with URLs (separated with new lines)")
    parser.add_argument("--output", metavar="Output directory", type=str, help="The output path (with filename)", required=True)
    parser.add_argument("--no-title", metavar="True,False", type=str, help="Whether to apply video title automatically to output path or not", required=True)

    args = parser.parse_args()
    no_title = str_to_bool(args.no_title)

    if args.download:
        client = Client()
        video = await client.get_video(args.download)
        await video.download(quality=args.quality, path=args.output, no_title=no_title)

    if args.file:
        videos = []
        client = Client()

        with open(args.file, "r") as file:
            content = file.read().splitlines()

        for url in content:
            videos.append(await client.get_video(url))

        for video in videos:
            await video.download(quality=args.quality, path=args.output, downloader=args.downloader, no_title=no_title)


if __name__ == "__main__":
    main()
