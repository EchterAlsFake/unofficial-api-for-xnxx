import re
from selectolax.lexbor import LexborHTMLParser
# ROOT URLs

ROOT_URL = "https://www.xnxx.com/"

# REGEX
REGEX_MODEL_TOTAL_VIDEO_VIEWS = re.compile(r'<span class="icon-f icf-eye"></span> (.*?) video views')
REGEX_EXTRACT_M3U8_URL = re.compile(r"html5player\.setVideoHLS\(['\"]([^'\"]+)['\"]\)")

headers = {
    "Referer": "https://www.xnxx.com/"
}


def extractor_html(content: str) -> list[dict]:
    parser = LexborHTMLParser(content)
    extracted_videos = []

    # Target all divs where the ID attribute starts with 'video_'
    for video_node in parser.css('div[id^="video_"]'):

        # Initialize the dictionary with existing dataclass fields
        # 'core' is omitted here as it requires your specific BaseCore instantiation
        video_data = {
            "url": None,
            "title": None,
            "thumbnail": None,
            "length": None,
            "views": None,
        }

        # Extract URL and Title
        a_tag = video_node.css_first('.thumb-under p a')
        if a_tag:
            video_data["url"] = a_tag.attributes.get("href")
            video_data["title"] = a_tag.attributes.get("title") or a_tag.text(strip=True)

        # Extract Thumbnail and new media URLs
        img_tag = video_node.css_first('.thumb img')
        if img_tag:
            video_data["thumbnail"] = img_tag.attributes.get("src")
            video_data["video_id"] = img_tag.attributes.get("data-videoid")
            video_data["preview_video_url"] = img_tag.attributes.get("data-pvv")

        # Also grab the element ID (e.g., "lgqbz55")
        video_data["video_eid"] = video_node.attributes.get("data-eid")

        # Extract Metadata (Views, Length, Rating, Quality)
        metadata_node = video_node.css_first('.metadata')
        if metadata_node:

            # 1. Rating
            rating_node = metadata_node.css_first('.right .superfluous')
            if rating_node:
                video_data["rating"] = rating_node.text(strip=True)

            # 2. Views (Cleaned by stripping out the rating text)
            right_span = metadata_node.css_first('.right')
            if right_span:
                views_text = right_span.text(strip=True)
                if video_data.get("rating"):
                    views_text = views_text.replace(video_data["rating"], "")
                video_data["views"] = views_text.strip()

            # 3. Quality (e.g., 1080p)
            hd_span = metadata_node.css_first('.video-hd')
            if hd_span:
                # Extract text and remove the decorative " - " string
                quality_text = hd_span.text(strip=True).replace("-", "").strip()
                video_data["max_quality"] = quality_text

            # 4. Length (Using regex to reliably extract the 'Xmin' pattern from the raw block text)
            raw_metadata_text = metadata_node.text(separator=" ", strip=True)
            length_match = re.search(r'(\d+min)', raw_metadata_text)
            if length_match:
                video_data["length"] = length_match.group(1)

        extracted_videos.append(video_data)

    return extracted_videos