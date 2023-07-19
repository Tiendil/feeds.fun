import datetime


def now():
    return datetime.datetime.now(tz=datetime.timezone.utc)
