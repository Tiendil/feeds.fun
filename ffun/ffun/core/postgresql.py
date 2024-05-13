import asyncio
import contextlib
import functools
from typing import Any, AsyncGenerator, Callable, Protocol

import psycopg
import psycopg_pool
from psycopg.pq import ExecStatus
from psycopg.rows import dict_row

from ffun.core import logging

logger = logging.get_module_logger()

MAX_INTEGER = 2147483647

POOL: psycopg_pool.AsyncConnectionPool | None = None


DB_RESULT = list[dict[str, Any]]
SQL_ARGUMENTS = dict[str, Any] | tuple[list[Any]]


class ExecuteType(Protocol):
    async def __call__(self, command: str, arguments: SQL_ARGUMENTS | None = None) -> DB_RESULT:
        pass


class PGAsyncCursor(psycopg.AsyncCursor):  # type: ignore
    async def execute_and_extract(self, command: str, arguments: SQL_ARGUMENTS | None = None) -> DB_RESULT:
        await self.execute(command, arguments)

        if self.pgresult is None:
            raise NotImplementedError("We expect cursor.pgresult has already settled here")

        # see for details
        # https://github.com/psycopg/psycopg/blob/ea76ab81ba1d797eee2baf2a1464be51e608b8bd/psycopg/psycopg/pq/_enums.py
        if self.pgresult.status in (ExecStatus.TUPLES_OK, ExecStatus.SINGLE_TUPLE):
            return await self.fetchall()

        return []


class PGPAsyncConnection(psycopg.AsyncConnection):  # type: ignore
    def __init__(self, *argv, row_factory=dict_row, cursor_factory=PGAsyncCursor, **kwargs):  # type: ignore
        super().__init__(*argv, row_factory=row_factory, **kwargs)  # type: ignore
        self.cursor_factory = cursor_factory

        # set prepare_threshold to None because we can use connection pool (pgbouncer/RDSPRoxy)
        # details: https://www.psycopg.org/psycopg3/docs/advanced/prepare.html
        self.prepare_threshold = None


async def pool_refresher(delay: int) -> None:
    logger.info("start pool refresher")

    try:
        while True:
            await asyncio.sleep(delay)

            if POOL is None:
                continue

            logger.info("refresh pool")

            await POOL.check()
    except asyncio.CancelledError:
        logger.info("Pool refresher is stopped")
        return


async def prepare_pool(  # noqa: CFQ002
    name: str, dsn: str, min_size: int, max_size: int | None, timeout: float, num_workers: int, max_lifetime: int
) -> None:
    global POOL

    if POOL is not None:
        raise RuntimeError("Secondary db pool initialization is not allowed")

    POOL = psycopg_pool.AsyncConnectionPool(
        dsn,
        min_size=min_size,
        max_size=max_size,
        max_lifetime=max_lifetime,
        timeout=timeout,
        connection_class=PGPAsyncConnection,
        num_workers=num_workers,
        name=name,
        open=False,
        kwargs={"autocommit": True},
    )

    await POOL.open(wait=False)


async def destroy_pool() -> None:
    global POOL

    if POOL is None:
        return

    try:
        await POOL.close()
    except asyncio.CancelledError:
        # TODO: is this a correct solution?
        pass

    POOL = None


@contextlib.asynccontextmanager
async def transaction(autocommit: bool = False) -> AsyncGenerator[ExecuteType, None]:
    if POOL is None:
        raise RuntimeError("POOL MUST be initialized before any operations with database")

    async with POOL.connection() as connection:
        if connection.autocommit != autocommit:
            await connection.set_autocommit(autocommit)

        async with connection.cursor() as cursor:
            assert isinstance(cursor, PGAsyncCursor)
            yield cursor.execute_and_extract


async def execute(command: str, arguments: SQL_ARGUMENTS | None = None) -> DB_RESULT:
    async with transaction(autocommit=True) as execute:
        return await execute(command, arguments)


def run_in_transaction(func: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(func)
    async def wrapper(*argv: Any, **kwargs: Any) -> Any:
        async with transaction() as execute:
            return await func(execute, *argv, **kwargs)

    return wrapper
