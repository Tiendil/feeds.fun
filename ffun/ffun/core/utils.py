import datetime


def now() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone.utc)
