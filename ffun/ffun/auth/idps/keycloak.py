
from ffun.auth.idps.plugin import Plugin


class Keycloak(Plugin):
    __slots__ = ()


def construct(**kwargs: object) -> Keycloak:
    return Keycloak()
