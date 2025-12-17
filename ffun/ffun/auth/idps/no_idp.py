from ffun.auth.idps.plugin import Plugin as PluginBase


class Plugin(PluginBase):
    __slots__ = ()


def construct(**kwargs: object) -> Plugin:
    return Plugin()
