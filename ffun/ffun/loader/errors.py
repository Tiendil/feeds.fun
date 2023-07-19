from ffun.core import errors
from ffun.feeds import entities as f_entities


class Error(errors.Error):
    pass


class LoadError(Error):
    feed_error_code: f_entities.FeedError
