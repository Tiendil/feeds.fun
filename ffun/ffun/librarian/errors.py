from ffun.core import errors


class Error(errors.Error):
    pass


class SkipAndContinueLater(Error):
    pass


class CanNotSaveUnexistingPointer(Error):
    pass


class UnexpectedErrorInProcessor(Error):
    pass
