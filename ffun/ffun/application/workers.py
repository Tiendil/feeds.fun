import asyncio
import contextlib
from typing import AsyncGenerator

from ffun.core import logging
from ffun.librarian.background_processors import create_background_processors
from ffun.loader.background_loader import FeedsLoader

logger = logging.get_module_logger()


@contextlib.asynccontextmanager
async def use_loader() -> AsyncGenerator[None, None]:
    logger.info("feeds_loader_enabled")

    feeds_loader = FeedsLoader(name="ffun_feeds_loader", delay_between_runs=1)

    feeds_loader.start()

    logger.info("feeds_loader_initialized")

    try:
        yield
    finally:
        logger.info("deinitialize_feeds_loader")
        await feeds_loader.stop()
        logger.info("feeds_loader_deinitialized")


@contextlib.asynccontextmanager
async def use_librarian() -> AsyncGenerator[None, None]:
    logger.info("librarian_enabled")

    entries_processors = create_background_processors()

    for processor in entries_processors:
        processor.start()

    logger.info("librarian_initialized")

    try:
        yield
    finally:
        logger.info("deinitialize_librarian")
        await asyncio.gather(*[processor.stop() for processor in entries_processors], return_exceptions=True)
        logger.info("librarian_deinitialized")
