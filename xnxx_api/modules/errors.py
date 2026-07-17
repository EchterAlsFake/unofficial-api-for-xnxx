class RegionBlocked(Exception):
    def __init__(self, msg):
        super().__init__(msg)
        self.msg = msg


class NetworkError(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)
        self.msg = msg


class BotDetection(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)
        self.msg = msg


class ProxyError(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)
        self.msg = msg


class UnknownNetworkError(Exception):
    def __init__(self, msg):
        super().__init__(msg)
        self.msg = msg


class DownloadFailed(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)
        self.msg = msg