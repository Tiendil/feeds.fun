from ffun.core import errors


class Error(errors.Error):
    pass


class ModelDoesNotFound(Error):
    pass


class TextPartsMustBePositive(Error):
    pass


class TemporaryError(Error):
    pass


class NoKeyFoundForFeed(Error):
    pass


class UsedTokensHasNotSpecified(Error):
    pass