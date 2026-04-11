from collections.abc import Mapping
from typing import Protocol, TypeVar, cast

from ffun.core import utils

PluginT = TypeVar("PluginT")
PluginT_co = TypeVar("PluginT_co", covariant=True)


class PluginConstructor(Protocol[PluginT_co]):
    def __call__(self, **kwargs: str) -> PluginT_co:
        pass


def build_plugin(plugin_type: type[PluginT], path: str, extras: Mapping[str, str]) -> PluginT:
    try:
        constructor = cast(PluginConstructor[PluginT], utils.import_from_string(path))
    except Exception as e:
        raise ValueError(f"Cannot import '{path}': {e}") from e

    try:
        plugin = constructor(**extras)
    except Exception as e:
        raise ValueError(f"Cannot construct plugin from '{path}': {e}") from e

    if not isinstance(plugin, plugin_type):
        raise ValueError(
            f"Cannot construct plugin from '{path}': "
            f"expected instance of {plugin_type.__module__}.{plugin_type.__qualname__}, "
            f"got {type(plugin).__module__}.{type(plugin).__qualname__}"
        )

    assert isinstance(plugin, plugin_type)
    return plugin
