from ffun.core import errors


class Error(errors.Error):
    pass


class UnknownBenefit(Error):
    pass


class BenefitTransactionNotFound(Error):
    pass


class ConcurrentBenefitTransaction(Error):
    pass


class InvalidBenefitRevocation(Error):
    pass


class InvalidBenefitGrant(Error):
    pass


class StaleBenefitGrant(Error):
    pass


class InvalidBenefitSubscription(Error):
    pass


class InvalidStoredBenefitTransaction(Error):
    pass
