
from ffun.auth.idps.plugin import Plugin as PluginBase


class Plugin(PluginBase):
    __slots__ = ()

    async def remove_user(self, external_user_id: str) -> None:
        pass

    async def revoke_all_user_sessions(self, external_user_id: str) -> None:
        pass


def construct(**kwargs: object) -> Plugin:
    return Plugin()
