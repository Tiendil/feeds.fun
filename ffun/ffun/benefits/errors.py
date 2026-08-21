from ffun.core import errors


class Error(errors.Error):
    pass


class UnknownBenefit(Error):
    pass


class MissingBenefitParameter(Error):
    pass


class UnknownBenefitParameter(Error):
    pass


class InvalidBenefitParameter(Error):
    pass


class InvalidBenefitEntitlement(Error):
    pass


class ConcurrentBenefitTransaction(Error):
    pass


class StaleBenefitTransaction(Error):
    pass


class InvalidBenefitSubscription(Error):
    pass


class InvalidStoredBenefitTransaction(Error):
    pass
