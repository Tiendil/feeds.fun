from ffun.core import errors


class Error(errors.Error):
    pass


class IdPNoUserIdHeader(Error):
    pass


class IdPNoIdentityProviderIdHeader(Error):
    pass


class IdPNoIdentityProviderInSettings(Error):
    pass


class NoIdPFound(Error):
    pass


class InternalUserDoesNotExistForImportedUser(Error):
    pass
