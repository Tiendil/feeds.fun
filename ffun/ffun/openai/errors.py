from ffun.core import errors


class Error(errors.Error):
    pass


class TemporaryError(Error):
    pass


class NoKeyFoundForFeed(Error):
    pass
