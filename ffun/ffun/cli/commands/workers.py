import asyncio
import contextlib

from ffun.application import utils as app_utils
from ffun.application import workers as app_workers
from ffun.application.application import with_app
from ffun.cli.application import app
from ffun.loader import domain as l_domain


async def run(loader: bool, librarian: bool) -> None:
    async with with_app():
        async with contextlib.AsyncExitStack() as stack:
            if loader:
                l_domain.initialize(user_agent=app_utils.user_agent())
                await stack.enter_async_context(app_workers.use_loader())

            if librarian:
                await stack.enter_async_context(app_workers.use_librarian())

            while True:
                await asyncio.sleep(0.1)


@app.command()
def workers(loader: bool = False, librarian: bool = False) -> None:
    asyncio.run(run(loader=loader, librarian=librarian))
