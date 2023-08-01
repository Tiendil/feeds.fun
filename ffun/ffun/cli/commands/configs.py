import asyncio
import contextlib
import pprint

from ffun.application import utils as app_utils
from ffun.application import workers as app_workers
from ffun.application.application import with_app
from ffun.core.utils import discover_submodules
from ffun.loader import domain as l_domain

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
