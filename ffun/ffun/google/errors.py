from ffun.core import errors


class Error(errors.Error):
    pass


class ClientError(Error):
    pass


class AuthError(ClientError):
    pass


class QuotaError(ClientError):
    pass


class UnknownError(ClientError):
    pass


class ProhibitedContentError(ClientError):
    pass


class MalformedFunctionCallError(ClientError):
    pass


class UnknownFinishReasonError(ClientError):
    pass


class PromptBlocked(ClientError):
    pass
