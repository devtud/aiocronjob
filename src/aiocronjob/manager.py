import asyncio
import functools
from collections import deque
from typing import Callable, Optional, Coroutine, List, Dict, Deque

from crontab import CronTab
from .dependencies import set_manager
from .exceptions import (
    JobNotFoundException,
    JobAlreadyRunningException,
    JobNotRunningException,
)
from .logger import logger
from .models import JobDefinition, JobLog, JobInfo, JobStatus, State, EventType
from .util import now


class Manager:
    def __init__(self):
        self._jobs: dict[str, JobInfo] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._log_queue: Deque[JobLog] = deque()

        self._is_running: bool = False
        self._is_shutting_down: bool = False

        self._cleanup_tasks: List[asyncio.Task] = []

        self._initial_state: Optional[State] = None

    def set_default(self):
        set_manager(self)

    def set_initial_state(self, state: State):
        self._initial_state = state

    async def generate_logs(self, as_json_lines: bool = False):
        last_index = 0
        while True:
            for i in range(last_index, len(self._log_queue)):
                log = self._log_queue[i]
                if as_json_lines:
                    log = f"{log.json()}\n"
                yield log
                print("yielded", log)
            last_index = len(self._log_queue)
            await asyncio.sleep(3)

    def clear(self):
        """Resets the"""
        if not (self._is_running or self._is_shutting_down):
            self._jobs.clear()
            self._tasks.clear()
            self._log_queue.clear()

    def register(
        self,
        async_callable: Callable[[], Coroutine],
        crontab: str = None,
        name: str = None,
    ):
        name = name or async_callable.__name__
        if name in self._jobs:
            raise Exception(f"Job <{name}> already exists.")

        self._jobs[name] = JobInfo(
            definition=JobDefinition(
                name=name, async_callable=async_callable, crontab=crontab, enabled=True
            ),
            status="registered",
        )

        self._log_event("job_registered", name)

    def _log_event(self, event_type: EventType, job_name: str, error: str = None):
        self._log_queue.append(
            JobLog(
                event_type=event_type,
                job_name=job_name,
                crontab=self._jobs[job_name].definition.crontab,
                enabled=self._jobs[job_name].definition.enabled,
                error=error,
            )
        )

    def _get_job(self, name: str) -> JobInfo:
        try:
            return self._jobs[name]
        except KeyError as e:
            raise JobNotFoundException from e

    def _get_task(self, name: str) -> asyncio.Task:
        try:
            return self._tasks[name]
        except KeyError as e:
            raise JobNotRunningException from e

    def _is_job_running(self, name: str) -> bool:
        return name in self._tasks

    def get_job_info(self, name: str) -> JobInfo:
        return self._get_job(name)

    def _get_job_status(self, name: str) -> JobStatus:
        return self._get_job(name).status

    def _get_job_next_start_in(self, name: str) -> Optional[int]:
        job = self._get_job(name)
        if job.definition.crontab is None:
            return None
        return CronTab(job.definition.crontab).next(default_utc=True)

    async def _create_task(self, definition: JobDefinition) -> asyncio.Task:
        task = asyncio.create_task(definition.async_callable(), name=definition.name)
        task.add_done_callback(functools.partial(self._on_job_done, definition.name))
        return task

    async def cancel_job(self, name: str):
        logger.info(f"Cancelling {name}")
        self._get_job(name)
        self._get_task(name).cancel()

    async def start_job(self, name: str) -> None:
        if self._is_job_running(name):
            raise JobAlreadyRunningException

        job = self._get_job(name)
        await self._on_job_started(name)
        self._tasks[name] = await self._create_task(job.definition)
        job.status = "running"
        job.next_start = now().timestamp() + (self._get_job_next_start_in(name) or 0)

    def get_jobs_info(self) -> List[JobInfo]:
        return list(self._jobs.values())

    def _on_job_done(self, job_name: str, task: asyncio.Task) -> None:
        job = self._get_job(job_name)
        del self._tasks[job_name]

        if task.cancelled():
            self._log_event("job_cancelled", job.definition.name)
            job.status = "cancelled"
            job.next_start = None

            task = asyncio.get_event_loop().create_task(self.on_job_cancelled(job_name))
            self._cleanup_tasks.append(task)

        elif exception := task.exception():
            self._log_event("job_failed", job.definition.name, error=str(exception))
            job.status = "failed"
            job.next_start = None

            task = asyncio.create_task(self.on_job_exception(job_name, exception))
            self._cleanup_tasks.append(task)

        else:
            self._log_event("job_finished", job.definition.name)
            job.status = "finished"
            job.next_start = (
                now().timestamp() + self._get_job_next_start_in(job_name)
                if job.definition.crontab
                else None
            )

            task = asyncio.create_task(self.on_job_finished(job_name))
            self._cleanup_tasks.append(task)

    async def _on_job_started(self, job_name: str):
        self._log_event("job_started", job_name)
        await self.on_job_started(job_name)

    async def run(self):
        if self._is_running:
            logger.warning("Ignoring current calling of run(). Already running.")
            return

        self._is_running = True
        await self.on_startup()

        if self._initial_state:
            for job_info in self._initial_state.jobs_info:
                try:
                    job = self._get_job(job_info.get("definition", {}).get("name"))
                except Exception:
                    continue
                job.status = job_info.get("status") or job.status
                job.last_status = job_info.get("last_status") or job.last_status
                job.created_at = job_info.get("created_at") or job.created_at
                job.last_finish = job_info.get("last_finish") or job.last_finish

        await self._run_ad_infinitum()

    async def _run_ad_infinitum(self):
        while True and self._is_running:
            for job_name, job in self._jobs.items():
                this_time_ts = now().timestamp()

                if job.status == "registered":
                    delta: int = self._get_job_next_start_in(job_name) or 0
                    job.status = "pending"
                    job.next_start = now().timestamp() + delta
                elif (
                    not self._is_shutting_down
                    and job.status in ["pending", "finished"]
                    and job.next_start is not None
                    and job.next_start <= this_time_ts
                ):
                    await self.start_job(job_name)
                elif job.status == "running" and not self._is_job_running(job_name):
                    await self.start_job(job_name)
                else:  # job.status in ["cancelled", "failed"]:
                    ...
            await asyncio.sleep(1.5)

    async def shutdown(self):
        await asyncio.sleep(2)
        logger.info("Shutting down...")
        logger.info(f"Cancelling {len(self._tasks)} running jobs...")
        self._is_shutting_down = True

        for running_job in self._tasks.values():
            task_name = running_job.get_name()
            await self.cancel_job(task_name)
            logger.debug(f"Cancelled job {task_name}")

        await asyncio.gather(*self._cleanup_tasks)
        logger.debug("Cleanup tasks finished.")

        await self.on_shutdown()

        self._is_running = False
        self._is_shutting_down = False

    async def on_job_started(self, job_name: str):
        logger.info(f"[JOB_STARTED] job=%s", job_name)

    async def on_job_exception(self, job_name: str, exception: BaseException):
        logger.error("[JOB_EXCEPTION] job=%s, exc_msg=%s", job_name, str(exception))

    async def on_job_cancelled(self, job_name: str):
        logger.info(f"[JOB_CANCELLED] job=%s", job_name)

    async def on_job_finished(self, job_name: str) -> None:
        logger.info(f"[JOB_FINISHED] job=%s", job_name)

    async def on_startup(self) -> None:
        logger.info("[STARTING]")

    async def on_shutdown(self) -> None:
        logger.info("[SHUTTING_DOWN]")

    def state(self) -> State:
        state = State(
            created_at=now(), jobs_info=[job.dict() for job in self.get_jobs_info()]
        )
        return state
