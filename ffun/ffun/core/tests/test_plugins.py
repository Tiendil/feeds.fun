import pytest

from ffun.core.plugins import build_plugin


class _BasePlugin:
    pass


class _Plugin(_BasePlugin):
    def __init__(self, test_option: str):
        self.test_option = test_option


class _OtherPlugin:
    pass


def _construct_plugin(test_option: str) -> _Plugin:
    return _Plugin(test_option=test_option)


def _construct_wrong_plugin_type() -> _OtherPlugin:
    return _OtherPlugin()


def _construct_plugin_with_error() -> _BasePlugin:
    raise RuntimeError("boom")


class TestBuildPlugin:
    def test_success(self) -> None:
        plugin = build_plugin(
            _BasePlugin,
            "ffun.core.tests.test_plugins:_construct_plugin",
            {"test_option": "value"},
        )

        assert isinstance(plugin, _Plugin)
        assert plugin.test_option == "value"

    def test_import_error(self) -> None:
        with pytest.raises(ValueError, match="Cannot import"):
            build_plugin(
                _BasePlugin,
                "ffun.core.tests.test_plugins:missing_constructor",
                {},
            )

    def test_constructor_error(self) -> None:
        with pytest.raises(ValueError, match="Cannot construct plugin"):
            build_plugin(
                _BasePlugin,
                "ffun.core.tests.test_plugins:_construct_plugin_with_error",
                {},
            )

    def test_wrong_plugin_type(self) -> None:
        with pytest.raises(ValueError, match="expected instance of"):
            build_plugin(
                _BasePlugin,
                "ffun.core.tests.test_plugins:_construct_wrong_plugin_type",
                {},
            )
