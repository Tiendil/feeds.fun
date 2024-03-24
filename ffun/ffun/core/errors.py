from typing import Any


class Error(Exception):
    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

        # TODO: send to Sentry
        if "fingerprint" not in kwargs:
            self.fingerprint = None

    def __repr__(self) -> str:
        attributes = ", ".join(f"{key}={value}" for key, value in self.__dict__.items())

        return f"{self.__class__.__name__}: {attributes}"


class CoreError(Error):
    pass


class EntityAlreadyRegistered(CoreError):
    pass
