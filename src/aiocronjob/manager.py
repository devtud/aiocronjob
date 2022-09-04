import asyncio
import functools
from collections import deque

from crontab import CronTab
from .exceptions import (
    JobNotFoundException,
    JobAlreadyRunningException,
    JobNotRunningException,
)
from .logger import logger
from .models import (
    JobDefinition,
    RunningJob,
    JobLog,
    JobInfo,
    JobStatus,
    State,
    JobRealTimeInfo,
    EventType,
)
from .typing import Callable, Optional, Coroutine, List, Dict, Deque
from .util import now


class Manager:
    def __init__(self):
        self._definitions: Dict[str, JobDefinition] = {}
        self._real_time: Dict[str, JobRealTimeInfo] = {}
        self._running_jobs: Dict[str, RunningJob] = {}
        self._log_queue: Deque[JobLog] = deque()

        self._is_running: bool = False
        self._is_shutting_down: bool = False

        self._cleanup_tasks: List[asyncio.Task] = []

    async def generate_logs(self):
        last_index = 0
        while True:
            for i in range(last_index, len(self._log_queue)):
                yield self._log_queue[i]
            last_index = len(self._log_queue)
            await asyncio.sleep(1)

    def clear(self):
        """Resets the"""
        if self._is_running or self._is_shutting_down:
            raise Exception("Cannot clear before shutdown")
        self._definitions: Dict[str, JobDefinition] = {}
        self._real_time: Dict[str, JobRealTimeInfo] = {}
        self._running_jobs: Dict[str, RunningJob] = {}
        self._log_queue: Deque[JobLog] = deque()

    def register(
        self,
        async_callable: Callable[[], Coroutine],
        crontab: str = None,
        name: str = None,
    ):
        name = name or async_callable.__name__
        if name in self._definitions:
            raise Exception(f"Job <{name}> already exists.")

        definition = JobDefinition(
            name=name, async_callable=async_callable, crontab=crontab, enabled=True
        )
        self._definitions[name] = definition
        self._real_time[name] = JobRealTimeInfo(
            name=name, status="registered", next_run_ts=None
        )

        self._log_event("job_registered", definition.name)

    def _log_event(self, event_type: EventType, job_name: str, error: str = None):
        self._log_queue.append(
            JobLog(
                event_type=event_type,
                job_name=job_name,
                crontab=self._definitions[job_name].crontab,
                enabled=self._definitions[job_name].enabled,
                error=error,
            )
        )

    def _get_job_definition(self, name: str) -> JobDefinition:
        try:
            return self._definitions[name]
        except KeyError as e:
            raise JobNotFoundException from e

    def _get_running_job(self, name: str) -> RunningJob:
        try:
            return self._running_jobs[name]
        except KeyError as e:
            raise JobNotRunningException from e

    def _is_job_running(self, name: str) -> bool:
        return name in self._running_jobs

    def get_job_info(self, name: str) -> JobInfo:
        definition = self._get_job_definition(name)
        return JobInfo(
            name=definition.name,
            enabled=definition.enabled,
            crontab=definition.crontab,
            next_run_in=self._get_job_next_run_in(name),
            last_status=self._get_job_status(name),
        )

    def _get_job_status(self, name: str) -> JobStatus:
        rt_info = self._real_time.get(name)
        if not rt_info:
            raise JobNotFoundException("job not found")
        return rt_info.status

    def _get_job_next_run_in(self, name: str) -> Optional[int]:
        definition = self._get_job_definition(name)
        if definition.crontab is None:
            return None
        return CronTab(definition.crontab).next(default_utc=True)

    def _create_running_job(self, definition: JobDefinition) -> RunningJob:
        running_job = RunningJob(
            job_definition=definition,
            asyncio_task=asyncio.get_event_loop().create_task(
                definition.async_callable()
            ),
            since=now().timestamp(),
        )
        running_job.asyncio_task.add_done_callback(
            functools.partial(self._on_job_done, definition.name)
        )
        return running_job

    async def cancel_job(self, name: str):
        logger.info(f"Cancelling {name}")
        self._get_job_definition(name)
        running_job = self._get_running_job(name)
        cancelled = running_job.asyncio_task.cancel()
        # if cancelled:
        #     await cls.on_job_cancelled(name)
        return cancelled

    def start_job(self, name: str) -> None:
        if self._is_job_running(name):
            raise JobAlreadyRunningException("job already running")

        definition = self._get_job_definition(name)
        running_job = self._create_running_job(definition)
        self._running_jobs[definition.name] = running_job
        self._real_time[name] = JobRealTimeInfo(
            name=name,
            status="running",
            next_run_ts=now().timestamp() + (self._get_job_next_run_in(name) or 0),
        )

    def get_all_jobs_info(self) -> List[JobInfo]:
        return [self.get_job_info(name) for name in self._definitions.keys()]

    def _on_job_done(self, job_name: str, task: asyncio.Task) -> None:
        definition = self._get_job_definition(job_name)
        del self._running_jobs[job_name]

        try:
            exception = task.exception()
        except asyncio.CancelledError:
            self._log_event("job_cancelled", definition.name)

            self._real_time[job_name] = JobRealTimeInfo(
                name=job_name, status="cancelled", next_run_ts=None
            )
            task = asyncio.get_event_loop().create_task(self.on_job_cancelled(job_name))
            self._cleanup_tasks.append(task)
            return

        if exception:
            self._log_event("job_failed", definition.name, error=str(exception))

            self._real_time[job_name] = JobRealTimeInfo(
                name=job_name, status="failed", next_run_ts=None
            )
            task = asyncio.get_event_loop().create_task(
                self.on_job_exception(job_name, exception)
            )
            self._cleanup_tasks.append(task)
            return

        self._log_event("job_finished", definition.name)

        self._real_time[job_name] = JobRealTimeInfo(
            name=job_name,
            status="finished",
            next_run_ts=now().timestamp() + self._get_job_next_run_in(job_name)
            if definition.crontab
            else None,
        )
        task = asyncio.get_event_loop().create_task(self.on_job_finished(job_name))
        self._cleanup_tasks.append(task)
        return

    async def _on_job_started(self, job_name: str):
        definition = self._get_job_definition(job_name)
        self._log_event("job_started", definition.name)
        await self.on_job_started(job_name)

    async def run(self, state: State = None):
        if self._is_running:
            logger.warning("Ignoring current calling of run(). Already running.")
            return

        self._is_running = True
        await self.on_startup()

        if state:
            for job_info in state.jobs_info:
                if job_info.name in self._definitions:
                    self._definitions[job_info.name].crontab = job_info.crontab
                    self._definitions[job_info.name].enabled = job_info.enabled

                    self._real_time[job_info.name].status = job_info.last_status

        await self._run_ad_infinitum()

    async def _run_ad_infinitum(self):
        while True and self._is_running:
            for job_name, rt_info in self._real_time.items():
                this_time_ts = now().timestamp()

                if rt_info.status == "registered":
                    delta: int = self._get_job_next_run_in(job_name) or 0

                    self._real_time[job_name] = JobRealTimeInfo(
                        name=job_name,
                        status="pending",
                        next_run_ts=now().timestamp() + delta,
                    )
                elif (
                    not self._is_shutting_down
                    and rt_info.status in ["pending", "finished"]
                    and rt_info.next_run_ts is not None
                    and rt_info.next_run_ts <= this_time_ts
                ):
                    self.start_job(job_name)

                else:  # rt_info.status in ["running", "cancelled", "failed"]:
                    ...
            await asyncio.sleep(1.5)

    async def shutdown(self):
        await asyncio.sleep(2)
        logger.info("Shutting down...")
        logger.info(f"Cancelling {len(self._running_jobs)} running jobs...")
        self._is_shutting_down = True

        for running_job in self._running_jobs.values():
            await self.cancel_job(running_job.job_definition.name)
            logger.debug(f"Cancelled job {running_job.job_definition.name}")

        await asyncio.gather(*self._cleanup_tasks)
        logger.debug("Cleanup tasks finished.")

        await self.on_shutdown()

        self._is_running = False
        self._is_shutting_down = False

    async def on_job_started(self, job_name: str):
        ...

    async def on_job_exception(self, job_name: str, exception: BaseException):
        ...

    async def on_job_cancelled(self, job_name: str):
        logger.info(f"Cancelled {job_name}")

    async def on_job_finished(self, job_name: str):
        logger.info(f"Finished {job_name}")

    async def on_startup(self):
        ...

    async def on_shutdown(self):
        ...

    def state(self) -> State:
        state = State(created_at=now(), jobs_info=self.get_all_jobs_info())
        return state
