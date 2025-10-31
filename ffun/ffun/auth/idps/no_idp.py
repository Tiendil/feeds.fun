
from ffun.auth.idps.plugin import Plugin


class NoIdP(Plugin):
    __slots__ = ()


def construct(**kwargs: object) -> NoIdP:
    return NoIdP()
