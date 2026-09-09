import os
import re
import html
import json
import math
import copy
import logging
import asyncio
import argparse

from base_api.modules.logger import configure_app_logging

from typing import AsyncGenerator, ClassVar
from dataclasses import dataclass
from curl_cffi import AsyncSession
from selectolax.lexbor import LexborHTMLParser
from base_api.modules.type_hints import DownloadReport
from base_api.modules.config import IteratorConfig
from base_api.modules.static_functions import str_to_bool
from base_api import (
    BaseCore,
    BaseMedia,
    DownloadConfigHLS,
    RetryPolicy,
    ScrapeResult,
    media_field,
    make_iterator_config,
    is_resource_gone,
    default_on_error,
    scrape_stream,
    get_text_safe,
)
from base_api.modules.errors import (
    DownloadCancelled,
    AccessDeniedError,
    BotProtectionDetected,
    HTTPStatusError,
    InvalidProxy,
    NetworkRequestError,
    RequestRetriesExhausted,
    UnknownError,
)

from xnxx_api.modules.errors import (NetworkError, ProxyError, UnknownNetworkError, BotDetection, RegionBlocked,
                                     DownloadFailed, NotFound)
from xnxx_api.modules.consts import headers, REGEX_MODEL_TOTAL_VIDEO_VIEWS, extractor_html, REGEX_EXTRACT_M3U8_URL
from xnxx_api.modules.search_filters import SearchingQuality, Mode, Length, UploadTime


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

SCRAPE_RETRY_POLICY = RetryPolicy(max_attempts=3)

_is_resource_gone = is_resource_gone
on_error = default_on_error


async def get_html_content(core: BaseCore, url: str) -> str:
    try:
        return await core.fetch_text(url)

    except AccessDeniedError as e:
        logger.exception("Request failed for %s: %s", url, e)
        raise RegionBlocked(f"Access denied for {url}: {e}") from e

    except HTTPStatusError as e:
        logger.exception("Request failed for %s (HTTP %s): %s", url, e.status_code, e)
        if e.status_code == 404:
            raise NotFound(f"Server returned 404 for: {url}") from e
        raise NetworkError(f"Request failed for {url}: {e}") from e

    except (NetworkRequestError, RequestRetriesExhausted) as e:
        logger.exception("Request failed for %s: %s", url, e)
        raise NetworkError(f"Request failed for {url}: {e}") from e

    except InvalidProxy as e:
        logger.exception("Request failed for %s: %s", url, e)
        raise ProxyError(f"Request failed for {url}: {e}") from e

    except BotProtectionDetected as e:
        logger.exception("Request failed for %s: %s", url, e)
        raise BotDetection(f"Request failed for {url}: {e}") from e

    except UnknownError as e:
        logger.exception("Request failed for %s: %s", url, e)
        raise UnknownNetworkError(f"Request failed for {url}: {e}") from e

    except Exception:
        logger.exception("Failed to fetch or decode response for %s", url)
        raise



@dataclass(kw_only=True, slots=True)
class Video(BaseMedia):
    url: str
    core: BaseCore
    title: str | None = media_field("html")
    description: str | None = media_field("html")
    thumbnail: str | None = media_field("html")
    publish_date: str | None = media_field("html")
    length: str | None = media_field("html")
    m3u8_base_url: str | None = media_field("html")
    views: str | None = media_field("html")
    author: str | None = media_field("html")
    tags: list[str] | None = media_field("html")

    # Optional
    video_id: str | None = None
    video_eid: str | None = None
    preview_video_url: str | None = None
    rating: str | None = None
    max_quality: str | None = None

    loader_methods: ClassVar[dict[str, str]] = {"html": "_load_html"}

    async def _load_html(self) -> dict[str, object]:
        html_content = await get_html_content(core=self.core, url=self.url)
        return await asyncio.to_thread(self._extract_html, html_content)

    def _extract_html(self, html_content: str | None = None) -> dict[str, object]:
        if isinstance(self, str):
            content = self
            url = "unknown"
        else:
            content = html_content or ""
            url = getattr(self, "url", "unknown")

        logger.debug("Starting data extraction for %s", url)
        parser = LexborHTMLParser(content)

        # Layout anchors: '#video-content' or '#html5video' are expected on all video pages
        if not parser.css_first("#video-content") and not parser.css_first("#html5video"):
            logger.warning(
                "Video container anchor ('#video-content' / '#html5video') not found for %s; page layout may have changed.",
                url,
            )

        script_data: dict = {}
        if script_node := parser.css_first('script[type="application/ld+json"]'):
            try:
                raw_json = script_node.text()
                if raw_json:
                    script_data = json.loads(raw_json)
            except Exception as e:
                logger.warning("Failed to parse application/ld+json for %s: %s", url, e)

        # 1. Title
        title = script_data.get("name")
        if not title:
            if strong_node := (parser.css_first("div.video-title strong") or parser.css_first(".video-title strong")):
                title = strong_node.text(strip=True)
            elif title_node := parser.css_first("div.video-title"):
                title = title_node.text(strip=True).replace("...", "").strip()
            elif m_title := re.search(r"html5player\.setVideoTitle\(['\"]([^'\"]+)['\"]\)", content):
                title = m_title.group(1)
        if title:
            title = html.unescape(title).strip()
        else:
            logger.warning("Title not found for %s", url)

        # 2. Description
        description = script_data.get("description")
        if not description:
            desc_node = parser.css_first("meta[name='description']") or parser.css_first("meta[property='og:description']")
            if desc_node and (c := desc_node.attributes.get("content")):
                description = c.strip()
        if description:
            description = html.unescape(description).strip()
        else:
            logger.warning("Description not found for %s", url)

        # 3. Thumbnail
        thumbnail = None
        raw_thumb = script_data.get("thumbnailUrl")
        if isinstance(raw_thumb, list) and raw_thumb:
            thumbnail = raw_thumb[0]
        elif isinstance(raw_thumb, str):
            thumbnail = raw_thumb
        if not thumbnail:
            if m_thumb := re.search(r"html5player\.setThumbUrl(?:169)?\(['\"]([^'\"]+)['\"]\)", content):
                thumbnail = m_thumb.group(1)
            elif img_node := parser.css_first("div.video-pic img"):
                thumbnail = img_node.attributes.get("src")
        if thumbnail:
            thumbnail = html.unescape(thumbnail).strip()
        else:
            logger.warning("Thumbnail not found for %s", url)

        # 4. Publish Date
        publish_date = script_data.get("uploadDate")
        if not publish_date:
            if m_date := re.search(r"<!--\s*dispo\s*-\s*([^>]+?)\s+Loaded\s*!", content):
                publish_date = m_date.group(1).strip()
        if publish_date:
            publish_date = html.unescape(str(publish_date)).strip()
        else:
            logger.warning("Publish date not found for %s", url)

        # 5. Length
        length = script_data.get("duration")
        if not length:
            meta_node = parser.css_first("div.video-title-container span.metadata") or parser.css_first("span.metadata")
            if meta_node and (m_len := re.search(r"(\d+\s*min)", meta_node.text(separator=" ", strip=True))):
                length = m_len.group(1).replace(" ", "")
            elif prog_node := parser.css_first(".progress-text"):
                if "/" in prog_node.text():
                    length = prog_node.text().split("/")[-1].strip()
        if length:
            length = html.unescape(str(length)).strip()
        else:
            logger.warning("Length not found for %s", url)

        # 6. m3u8 base URL
        m3u8_match = REGEX_EXTRACT_M3U8_URL.search(content)
        m3u8_base_url = m3u8_match.group(1) if m3u8_match else None
        if not m3u8_base_url:
            logger.warning("m3u8 base URL not found for %s", url)

        # 7. Views
        views = None
        stat = script_data.get("interactionStatistic")
        if isinstance(stat, dict):
            views = stat.get("userInteractionCount")
        elif isinstance(stat, list) and stat and isinstance(stat[0], dict):
            views = stat[0].get("userInteractionCount")
        if views is not None:
            views = str(views)
        else:
            logger.warning("Views not found for %s", url)

        # 8. Author
        author = get_text_safe(parser, "div.video-title-container a.gold-plate") or get_text_safe(parser, "div.video-title-container a")
        if not author and (m_auth := re.search(r"html5player\.setUploaderName\(['\"]([^'\"]+)['\"]\)", content)):
            author = m_auth.group(1)
        if author:
            author = html.unescape(author).strip()
        else:
            logger.warning("Author not found for %s", url)

        # 9. Tags
        tags = [tag.text(strip=True) for tag in parser.css("a.is-keyword") if tag.text(strip=True)]
        if not tags:
            if m_cats := re.search(r'window\.wpn_categories\s*=\s*["\']([^"\']+)["\']', content):
                tags = [c.strip() for c in m_cats.group(1).split(",") if c.strip()]
        if not tags:
            logger.warning("Tags not found for %s", url)

        logger.info("Successfully parsed data for %s", url)
        return {
            "title": title,
            "description": description,
            "thumbnail": thumbnail,
            "publish_date": publish_date,
            "length": length,
            "m3u8_base_url": m3u8_base_url,
            "views": views,
            "author": author,
            "tags": tags,
        }

    async def download(self, configuration: DownloadConfigHLS) -> bool | DownloadReport:
        try:
            await self.load_fields("m3u8_base_url", "title")
            config = copy.deepcopy(configuration)
            config.m3u8_base_url = self.m3u8_base_url
            if not config.no_title:
                config.path = os.path.join(config.path, f"{self.title}.mp4")

            return await self.core.download(configuration=config)
        except DownloadCancelled:
            raise
        except Exception as e:
            logger.exception("Download failed for %s: %s", self.url, e)
            raise DownloadFailed(f"Download failed for {self.url}: {e}") from e


@dataclass(kw_only=True, slots=True)
class User(BaseMedia):
    url: str
    core: BaseCore
    total_videos_count: int | None = media_field("html")
    total_pages_count: int | None = media_field("html")
    total_videos_views: str | None = media_field("html")

    loader_methods: ClassVar[dict[str, str]] = {"html": "_load_html"}

    async def _load_html(self) -> dict[str, object]:
        html_content_task = asyncio.create_task(get_html_content(core=self.core, url=self.url))
        base_json_task = asyncio.create_task(get_html_content(core=self.core, url=f"{self.url}/videos/best/0"))
        html_content, base_json = await asyncio.gather(html_content_task, base_json_task)

        return await asyncio.to_thread(self._extract_data, html_content, base_json)

    @staticmethod
    def _extract_data(html_content: str, base_json: str) -> dict:
        logger.debug("Starting data extraction")
        json_data = json.loads(base_json, strict=False)
        total_videos_count = int(json_data["nb_videos"])

        _per_page = int(json_data.get("nb_per_page"))
        total_pages_count = int(math.ceil(total_videos_count / _per_page))
        total_videos_views = REGEX_MODEL_TOTAL_VIDEO_VIEWS.search(html_content).group(1)
        logger.info("Successfully parsed data")
        return {
            "total_videos_count": total_videos_count,
            "total_pages_count": total_pages_count,
            "total_videos_views": total_videos_views,
        }

    async def videos(
        self,
        pages: int = 0,
        iterator_config: IteratorConfig | None = None,
    ) -> AsyncGenerator[ScrapeResult[Video], None]:

        total_pages_count = await self.get_field("total_pages_count")
        if pages >= total_pages_count:
            pages = int(total_pages_count)

        page_urls = [f"{self.url}/videos/best/{page}" for page in range(pages)]
        logger.debug(f"Iterating through pages: {page_urls}")
        if iterator_config is None:
            iterator_config = make_iterator_config()

        stream = scrape_stream(
            core=self.core,
            constructor=Video,
            target_page_urls=page_urls,
            item_extractor=extractor_html,
            iterator_config=iterator_config,
        )
        async for result in stream:
            logger.debug("Received Result: %s", result.succeeded)
            yield result


class Client:
    def __init__(self, core: BaseCore | None = None):
        if core is None:
            core = BaseCore()
        self.core = core
        self.core.initialize_session()
        assert isinstance(self.core.session, AsyncSession)
        self.core.session.headers.update(headers)
        logger.debug(f"Initialized Client with: {headers}")

    async def get_video(self, url, load_html: bool = True) -> Video:
        """
        :param url: (str) The URL of the video
        :param load_html: (bool) Whether to pre-fetch html or not
        :return: (Video) The video object
        """
        logger.info(f"Initializing Video object: {url}, HTML: {load_html}")
        video = Video(url=url, core=self.core)
        if load_html:
            await video.load_sources("html")
        return video

    async def get_user(self, url: str, load_html: bool = True) -> User:
        """
        :param url: (str) The user URL
        :param load_html: (bool) Whether to pre-fetch html or not
        :return: (User) The User object
        """
        logger.info(f"Initializing User object: {url}, HTML: {load_html}")
        user = User(url=url, core=self.core)
        if load_html:
            await user.load_sources("html")
        return user


    def search_videos(self, query: str, pages: int = 0,
                     mode: Mode | str = "",
                     upload_time: UploadTime | str = "",
                     length: Length | str = "",
                     searching_quality: SearchingQuality | str = "",
                     iterator_config: IteratorConfig | None = None,
                     ) -> AsyncGenerator[ScrapeResult[Video], None]:
        url = f"https://www.xnxx.com/search{mode}{upload_time}{length}{searching_quality}/{query}"

        page_urls = [url]
        page_urls.extend([f"{url}/{page}" for page in range(1, int(pages))])
        logger.info(f"Searching for videos using query: {query} and page URLs: {page_urls}")
        if iterator_config is None:
            iterator_config = make_iterator_config()

        return scrape_stream(
            core=self.core,
            constructor=Video,
            target_page_urls=page_urls,
            item_extractor=extractor_html,
            iterator_config=iterator_config,
        )


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="XNXX API Command Line Interface")
    parser.add_argument("--download", metavar="URL", type=str, help="URL to download from")
    parser.add_argument("--quality", metavar="best|half|worst", type=str, default="best", help="The video quality (best, half, worst)")
    parser.add_argument("--file", metavar="FILE", type=str, help="(Optional) Specify a file with URLs (separated with new lines)")
    parser.add_argument("--output", metavar="DIR", type=str, required=True, help="The output path (with filename or directory)")
    parser.add_argument("--no-title", metavar="True,False", type=str, nargs="?", const="True", default="False",
                        help="Whether to apply video title automatically to output path or not")
    return parser


async def run_main(args_list: list[str] | None = None):
    parser = create_parser()
    args = parser.parse_args(args_list)
    no_title = str_to_bool(args.no_title) if isinstance(args.no_title, str) else bool(args.no_title)
    config = DownloadConfigHLS(quality=args.quality, path=args.output, no_title=no_title)

    urls: list[str] = []
    if args.download:
        urls.append(args.download)
    if args.file:
        with open(args.file, "r") as file:
            urls.extend([line.strip() for line in file.readlines() if line.strip()])

    if not urls:
        parser.print_help()
        return

    client = Client()
    for url in urls:
        print(f"Fetching video information for: {url}")
        try:
            video = await client.get_video(url, load_html=True)
            title = getattr(video, "title", None) or url
            print(f"Starting download for: {title}")
            await video.download(config)
            print(f"Download complete: {title}")
        except Exception as e:
            logger.exception("CLI failed while processing %s", url)
            print(f"Error downloading {url}: {e}")


def main():
    configure_app_logging(level=logging.INFO)
    try:
        asyncio.run(run_main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")


if __name__ == "__main__":
    main()
