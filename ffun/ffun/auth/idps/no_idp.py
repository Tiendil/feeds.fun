
from ffun.auth.idps.plugin import Plugin


class NoIdP(Plugin):
    __slots__ = ()

    async def remove_user(self, external_user_id: str) -> None:
        pass

    async def logout_user_from_all_sessions(self, external_user_id: str) -> None:
        pass


def construct(**kwargs: object) -> NoIdP:
    return NoIdP()
