from typing import Any


class Error(Exception):
    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

        # TODO: send to Sentry
        if "fingerprint" not in kwargs:
            self.fingerprint = None


class CoreError(Error):
    pass


class EntityAlreadyRegistered(CoreError):
    pass
