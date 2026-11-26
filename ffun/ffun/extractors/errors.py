from ffun.core import errors


class Error(errors.Error):
    pass


class InvalidHtml(Error):
    pass


class InvalidLoadedUrl(Error):
    pass


class InvalidPieceLimit(Error):
    pass


class PieceLimitExceeded(Error):
    pass
