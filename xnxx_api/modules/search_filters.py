from enum import StrEnum

class Length(StrEnum):
    X_0_10min = "/0-10min"
    X_10min_plus = "/10min+"
    X_10_20min = "/10-20min"
    X_20min_plus = "/20min+"


class UploadTime(StrEnum):
    year = "/year"
    month = "/month"


class SearchingQuality(StrEnum):
    X_720p = "/hd-only"
    X_1080p_plus = "/fullhd"


class Mode(StrEnum):
    default = ""
    hits = "/hits"
    random = "/random"
