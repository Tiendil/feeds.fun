from ffun.core import errors


class Error(errors.Error):
    pass


class UnknownEntitlementKind(Error):
    pass


class InvalidSourceEntitlement(Error):
    pass


class InvalidActorId(Error):
    pass


class InvalidMergeValues(Error):
    pass


class InvalidStoredEntitlement(Error):
    pass
