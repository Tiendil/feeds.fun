from ffun.core import errors


class Error(errors.Error):
    pass


class UrlIsNotAbsolute(Error):
    pass


class ExpectedFUrlError(Error):
    pass
