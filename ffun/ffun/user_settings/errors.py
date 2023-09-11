from typing import Any

from ffun.core import errors


class Error(errors.Error):
    pass


class WrongValueType(Error):
    value: Any
