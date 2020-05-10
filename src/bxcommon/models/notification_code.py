from enum import IntEnum


class NotificationCodeRange(IntEnum):
    DEBUG = 2000  # <2000
    INFO = 4000  # <4000
    WARNING = 6000  # <6000
    ERROR = 8000  # <8000


class NotificationCode(IntEnum):
    QUOTA_FILL_STATUS = 4000
