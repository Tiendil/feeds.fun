from typing import Any


class Error(Exception):
    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

        # TODO: send to Sentry
        if "fingerprint" not in kwargs:
            self.fingerprint = None

    def __str__(self) -> str:
        attributes = ", ".join(f"{key}={value}" for key, value in self.__dict__.items())

        return f"{self.__class__.__name__}: {attributes}"


class CoreError(Error):
    pass


class APIError(CoreError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code=code, message=message)


class EntityAlreadyRegistered(CoreError):
    pass


class ReservedLogArguments(CoreError):
    pass


class DuplicatedMeasureLabels(CoreError):
    pass


class DuplicatedLogArguments(CoreError):
    pass
