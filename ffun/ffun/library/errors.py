import uuid

from ffun.core import errors


class Error(errors.Error):
    pass


class CanNotMoveEntryAlreadyInFeed(Error):
    entry_id: uuid.UUID
