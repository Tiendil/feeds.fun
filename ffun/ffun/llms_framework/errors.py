from ffun.core import errors


class Error(errors.Error):
    pass


class ModelDoesNotFound(Error):
    pass


class TextPartsMustBePositive(Error):
    pass
