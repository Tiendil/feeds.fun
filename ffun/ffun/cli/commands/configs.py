import asyncio
import pprint

from ffun.cli.application import app
from ffun.core.utils import discover_submodules


async def run() -> None:  # noqa: CCR001
    settings = []

    for component in discover_submodules("ffun"):
        for module in discover_submodules(component.__name__):
            if module.__name__.endswith(".settings") and hasattr(module, "settings"):
                settings.append(module)

    for module in settings:
        print("*" * 40)  # noqa: T201
        print(f"* {module.__name__}")  # noqa: T201
        print("*" * 40)  # noqa: T201
        pprint.pprint(module.settings.dict())  # noqa: T203
        print()  # noqa: T201


@app.command()
def print_configs() -> None:
    asyncio.run(run())
