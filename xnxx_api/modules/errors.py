from base_api.modules.errors import (
    NotFound,
    NetworkError,
    BotDetection,
    ProxyError,
    UnknownNetworkError,
    DownloadFailed,
)


class RegionBlocked(Exception):
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