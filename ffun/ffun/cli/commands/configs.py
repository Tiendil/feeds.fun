import asyncio
import pprint
from typing import Protocol, runtime_checkable

from ffun.cli.application import app
from ffun.core.utils import discover_submodules


@runtime_checkable
class HasDict(Protocol):
    def dict(self) -> dict[str, object]:
        pass


async def run() -> None:  # noqa: CCR001
    settings: list[tuple[str, HasDict]] = []

    for component in discover_submodules("ffun"):
        for module in discover_submodules(component.__name__):
            if module.__name__.endswith(".settings") and hasattr(module, "settings"):
                settings_object: object = module.settings
                assert isinstance(settings_object, HasDict)
                settings.append((module.__name__, settings_object))

    for module_name, settings_object in settings:
        print("*" * 40)  # noqa: T201
        print(f"* {module_name}")  # noqa: T201
        print("*" * 40)  # noqa: T201
        pprint.pprint(settings_object.dict())  # noqa: T203
        print()  # noqa: T201


@app.command()  # type: ignore
def print_configs() -> None:
    asyncio.run(run())
