from ffun.core import errors


class Error(errors.Error):
    pass


class ModelDoesNotFound(Error):
    pass


class TextPartsMustBePositive(Error):
    pass


class TextIntersectionMustBePositiveOrZero(Error):
    pass


class TextIsEmpty(Error):
    pass


class TextIsTooShort(Error):
    pass


class TemporaryError(Error):
    pass


class UsedTokensHasNotSpecified(Error):
    pass


class TooManyTokensForEntry(Error):
    pass


class FeedsFromCollectionsMustNotBeProcessedWithUserAPIKeys(Error):
    pass
