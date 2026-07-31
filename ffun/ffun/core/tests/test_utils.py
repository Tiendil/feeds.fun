import datetime
import pathlib
import sys
import types
from typing import cast
from unittest.mock import MagicMock

from pytest_mock import MockerFixture

from ffun.core import utils


def prepare_discoverable_modules(tmp_path: pathlib.Path, mocker: MockerFixture) -> dict[str, types.ModuleType]:
    package = types.ModuleType("test_package")
    package_path: list[str] = [str(tmp_path)]
    setattr(package, "__path__", package_path)

    modules = {
        module_name: types.ModuleType(f"test_package.{module_name}")
        for module_name in ("runtime", "conftest", "pytest_plugin")
    }

    for module_name in modules:
        (tmp_path / f"{module_name}.py").touch()

    mocker.patch.dict(
        sys.modules,
        {
            "test_package": package,
            **{module.__name__: module for module in modules.values()},
        },
    )

    return modules


class TestDiscoverSubmodules:
    def test_skips_dev_dependencies_by_default(self, tmp_path: pathlib.Path, mocker: MockerFixture) -> None:
        prepare_discoverable_modules(tmp_path, mocker)

        discovered = utils.discover_submodules("test_package")

        assert {module.__name__ for module in discovered} == {"test_package.runtime"}

    def test_includes_dev_dependencies_when_requested(self, tmp_path: pathlib.Path, mocker: MockerFixture) -> None:
        prepare_discoverable_modules(tmp_path, mocker)

        discovered = utils.discover_submodules("test_package", skip_dev_dependencies=False)

        assert {module.__name__ for module in discovered} == {
            "test_package.conftest",
            "test_package.pytest_plugin",
            "test_package.runtime",
        }


class TestHasTimezone:
    def test_timestamp_with_timezone(self) -> None:
        timestamp = datetime.datetime.now(tz=datetime.UTC)

        assert utils.has_timezone(timestamp)

    def test_timestamp_without_timezone(self) -> None:
        timestamp = datetime.datetime.now()

        assert not utils.has_timezone(timestamp)

    def test_timezone_without_offset(self) -> None:
        timestamp = MagicMock(spec=datetime.datetime)
        timestamp.tzinfo = MagicMock(spec=datetime.tzinfo)
        cast(MagicMock, timestamp.utcoffset).return_value = None

        assert not utils.has_timezone(timestamp)
