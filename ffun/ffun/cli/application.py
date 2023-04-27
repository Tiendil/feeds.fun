import asyncio

import typer
from ffun.application.application import with_app

app = typer.Typer()


# TODO: cleanup
async def run_experiment(url: str) -> None:
    from ffun.feeds_discoverer import domain as fd_domain
    async with with_app():
        feeds = await fd_domain.discover(url=url)
        print(feeds)


@app.command()
def experiment(url: str) -> None:
    asyncio.run(run_experiment(url=url))
