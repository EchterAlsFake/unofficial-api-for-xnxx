from base_api.modules.errors import (
    ScraperException,
    NotFound,
    NetworkError,
    BotDetection,
    ProxyError,
    UnknownNetworkError,
    DownloadFailed,
)


class RegionBlocked(ScraperException):
    def __init__(self, msg):
        super().__init__(msg)
        self.msg = msg


__all__ = [
    "RegionBlocked",
    "NotFound",
    "NetworkError",
    "BotDetection",
    "ProxyError",
    "UnknownNetworkError",
    "DownloadFailed",
]
