import uuid

from ffun.core import errors


class Error(errors.Error):
    pass


class IdPNoUserIdHerader(Error):
    pass


class IdPNoIdentityProviderIdHeader(Error):
    pass


class IdPNoIdentityProviderInSettings(Error):
    pass
