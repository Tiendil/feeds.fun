from ffun.core import errors


class Error(errors.Error):
    pass


class SubscriptionConflict(Error):
    pass


class ProviderSubscriptionReferenceConflict(Error):
    pass


class InvalidStoredSubscription(Error):
    pass
