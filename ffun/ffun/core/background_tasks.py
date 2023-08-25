import asyncio
from typing import Any

from ffun.core import logging

logger = logging.get_module_logger()


class InfiniteTask:
    __slots__ = ("_stop_requested", "_runner_task", "_run_requested", "_delay_between_runs", "_scheduler", "_name")

    def __init__(self, name: str, delay_between_runs: float) -> None:
        self._name = name
        self._stop_requested: bool = False
        self._run_requested = asyncio.Event()
        self._delay_between_runs = delay_between_runs
        self._runner_task: asyncio.Task[Any] | None = None
        self._scheduler: asyncio.Task[Any] | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def running(self) -> bool:
        return self._runner_task is not None

    @property
    def stop_requested(self) -> bool:
        return self._stop_requested

    @property
    def delay_between_runs(self) -> float:
        return self._delay_between_runs

    def request_run(self) -> None:
        self._run_requested.set()

    async def single_run(self) -> None:
        raise NotImplementedError('You must implement "single_run" method in child class')

    def start(self, from_start: bool = False) -> None:
        if self._runner_task is not None:
            raise NotImplementedError("You can not start task twice")

        self._stop_requested = False
        self._runner_task = asyncio.create_task(self._run(), name=f"{self._name}_runner")

        if from_start:
            self._run_requested.set()

        self._scheduler = asyncio.create_task(self._scheduler_loop(), name=f"{self._name}_scheduler")

    async def _scheduler_loop(self) -> None:
        while not self._stop_requested:
            await asyncio.sleep(self._delay_between_runs)
            self._run_requested.set()

    def request_stop(self) -> None:
        if not self.running:
            return

        self._stop_requested = True
        self._run_requested.set()

    async def stop(self) -> None:
        self.request_stop()

        if self._runner_task:
            await self._runner_task
            self._runner_task = None

        if self._scheduler:
            await self._scheduler
            self._scheduler = None

        self._stop_requested = False

    async def _run(self) -> None:
        logger.info("start_background_task", task_name=self._name)

        while not self._stop_requested:
            try:
                await self._run_requested.wait()

                self._run_requested.clear()

                logger.debug("running_background_task", task_name=self._name)

                await self.single_run()

                if self._stop_requested:
                    logger.info("stop_background_task", task_name=self._name)
                    break

            except Exception:
                logger.exception("error_in_background_task", task_name=self._name)

                # something bad happened with the infrastructure
                # there are now points in continue working
                # but we can not wait here for stop, because stop is waiting for this method
                self.request_stop()
