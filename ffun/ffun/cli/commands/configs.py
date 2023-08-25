import asyncio
import pprint

from ffun.core.utils import discover_submodules

from ..application import app


async def run() -> None:
    settings = []

    for component in discover_submodules("ffun"):
        for module in discover_submodules(component.__name__):
            if module.__name__.endswith(".settings") and hasattr(module, "settings"):
                settings.append(module)

    for module in settings:
        print("*" * 40)
        print(f"* {module.__name__}")
        print("*" * 40)
        pprint.pprint(module.settings.dict())
        print()


@app.command()
def print_configs() -> None:
    asyncio.run(run())
