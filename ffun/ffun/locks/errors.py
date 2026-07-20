from ffun.core import errors


class Error(errors.Error):
    pass


class InvalidLockKey(Error):
    pass


class LockInvariantViolation(Error):
    pass
