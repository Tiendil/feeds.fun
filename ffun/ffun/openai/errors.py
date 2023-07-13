from ffun.core import errors
from ffun.feeds import entities as f_entities


class Error(errors.Error):
    pass


class TemporaryError(Error):
    pass


class NoKeyFoundForFeed(Error):
    pass