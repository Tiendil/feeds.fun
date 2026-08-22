from ffun.core import errors


class Error(errors.Error):
    pass


class PurchaseConflict(Error):
    pass


class ProviderPurchaseReferenceConflict(Error):
    pass


class InvalidStoredPurchase(Error):
    pass
