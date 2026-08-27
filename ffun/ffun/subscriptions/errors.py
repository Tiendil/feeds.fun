from ffun.core import errors


class Error(errors.Error):
    pass


class SubscriptionConflict(Error):
    pass


class InvalidStoredSubscription(Error):
    pass
