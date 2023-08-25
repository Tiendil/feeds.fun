import uuid

from ffun.core import errors


class Error(errors.Error):
    pass


class NoFeedFound(Error):
    feed_id: uuid.UUID
