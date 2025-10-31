import uuid

from ffun.core import errors


class Error(errors.Error):
    pass


class OIDCNoUserIdHerader(Error):
    pass


class OIDCNoIdentityProviderIdHeader(Error):
    pass


class OIDCNoIdentityProviderInSettings(Error):
    pass
