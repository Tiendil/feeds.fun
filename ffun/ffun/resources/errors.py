from ffun.core import errors


class Error(errors.Error):
    pass


class DuplicateReservationUserIds(Error):
    pass


class DuplicateReservationSpecifications(Error):
    pass


class ReservationOptionsAndLimitsMismatch(Error):
    pass


class CanNotConvertReservedToUsed(Error):
    pass
