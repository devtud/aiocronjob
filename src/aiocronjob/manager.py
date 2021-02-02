import asyncio
import functools
from collections import deque

from crontab import CronTab
from dataclasses import dataclass

from .logger import logger
from .models import JobDefinition, RunningJob, JobLog, JobInfo, JobStatus
from .typing import Callable, Optional, Coroutine, List, Dict, Deque
from .util import now


@dataclass
class RealTimeInfo:
    status: JobStatus
    next_run_ts: Optional[int]


class manager:
    _definitions: Dict[str, JobDefinition] = {}
    _real_time: Dict[str, RealTimeInfo] = {}
    _running_jobs: Dict[str, RunningJob] = {}
    _log_queue: Deque[JobLog] = deque()

    _is_running: bool = False
    # _load_from_state: State

    @classmethod
    def register(
        cls,
        async_callable: Callable[[], Coroutine],
        crontab: str = None,
        name: str = None,
    ):
        name = name or async_callable.__name__
        if name in cls._definitions:
            raise Exception(f"Job <{name}> already exists.")

        definition = JobDefinition(
            name=name, async_callable=async_callable, crontab=crontab, enabled=True
        )
        cls._definitions[name] = definition
        cls._real_time[name] = RealTimeInfo(status="registered", next_run_ts=None)

        cls._log_event(JobLog(event_name="job_registered", job_definition=definition))

    @classmethod
    def _log_event(cls, log_event: JobLog):
        cls._log_queue.append(log_event)

    @classmethod
    def _get_job_definition(
        cls, name: str, raise_not_found: False
    ) -> Optional[JobDefinition]:
        definition = cls._definitions.get(name)
        if definition:
            return definition
        if raise_not_found:
            raise Exception("job not found")
        return None

    @classmethod
    def _get_running_job(
        cls, name: str, raise_not_found: bool = False
    ) -> Optional[RunningJob]:
        running_job = cls._running_jobs.get(name)
        if running_job:
            return running_job
        if raise_not_found:
            raise Exception("job not running")
        return None

    @classmethod
    def get_job_info(cls, name: str) -> Optional[JobInfo]:
        definition = cls._get_job_definition(name)
        if not definition:
            return None
        return JobInfo(
            name=definition.name,
            enabled=definition.enabled,
            crontab=definition.crontab,
            next_run_in=cls._get_job_next_run_in(name),
            last_status=cls._get_job_status(name),
        )

    @classmethod
    def _get_job_status(cls, name: str) -> JobStatus:
        rt_info = cls._real_time.get(name)
        if not rt_info:
            raise Exception("job not found")
        return rt_info.status

    @classmethod
    def _get_job_next_run_in(cls, name: str) -> int:
        definition = cls._get_job_definition(name, True)
        return CronTab(definition.crontab).next(default_utc=True)

    @classmethod
    async def cancel_job(cls, name: str):
        cls._get_job_definition(name, True)
        running_job = cls._get_running_job(name, True)
        cancelled = running_job.asyncio_task.cancel()
        # if cancelled:
        #     await cls.on_job_cancelled(name)
        return cancelled

    @classmethod
    def start_job(cls, name: str) -> None:
        definition = cls._get_job_definition(name, True)
        if cls._get_running_job(name):
            raise Exception("job already running")
        running_job = RunningJob(
            job_definition=definition,
            asyncio_task=asyncio.get_event_loop().create_task(
                definition.async_callable()
            ),
            since=now().timestamp(),
        )
        running_job.asyncio_task.add_done_callback(
            functools.partial(cls._on_job_done, name)
        )
        cls._running_jobs[definition.name] = running_job
        cls._real_time[name] = RealTimeInfo(
            status="running",
            next_run_ts=now().timestamp()
            + (CronTab(definition.crontab).next() if definition.crontab else 0),
        )

    @classmethod
    def get_all_jobs_info(cls) -> List[JobInfo]:
        return [cls.get_job_info(name) for name in cls._definitions.keys()]

    @classmethod
    async def _on_job_done(cls, job_name: str, task: asyncio.Task) -> None:
        definition = cls._get_job_definition[job_name]
        del cls._running_jobs[job_name]

        try:
            exception = task.exception()
        except asyncio.CancelledError:
            cls._log_event(
                JobLog(event_name="job_cancelled", job_definition=definition)
            )
            cls._real_time[job_name] = RealTimeInfo(
                status="cancelled", next_run_ts=None
            )
            return await cls.on_job_cancelled(job_name)

        if exception:
            cls._log_event(
                JobLog(
                    event_name="job_failed",
                    job_definition=definition,
                    error=str(exception),
                )
            )
            cls._real_time[job_name] = RealTimeInfo(status="failed", next_run_ts=None)
            return await cls.on_job_exception(job_name, exception)

        cls._log_event(
            JobLog(
                event_name="job_finished",
                job_definition=definition,
            )
        )
        cls._real_time[job_name] = RealTimeInfo(
            status="finished",
            next_run_ts=now().timestamp() + CronTab(definition.crontab).next()
            if definition.crontab
            else None,
        )
        return await cls.on_job_finished(job_name)

    @classmethod
    async def _on_job_started(cls, job_name: str):
        cls._log_event(
            JobLog(
                event_name="job_started",
                job_definition=cls._get_job_definition(job_name),
            )
        )
        await cls.on_job_started(job_name)

    @classmethod
    async def run(cls):
        if cls._is_running:
            logger.warning("Ignoring current calling of run(). Already running.")
            return

        cls._is_running = True

        await cls._run_ad_infinitum()

    @classmethod
    async def _run_ad_infinitum(cls):
        while True:
            for job_name, rt_info in cls._real_time.items():
                this_time_ts = now().timestamp()
                definition = cls._definitions[job_name]

                if rt_info.status == "registered":
                    delta: int
                    if not definition.crontab:
                        delta = 0
                    else:
                        delta = CronTab(definition.crontab).next()

                    cls._real_time[job_name] = RealTimeInfo(
                        status="pending", next_run_ts=now().timestamp() + delta
                    )
                elif rt_info.next_run_ts is not None and rt_info.status in [
                    "pending",
                    "finished",
                ]:
                    if rt_info.next_run_ts <= this_time_ts:
                        cls.start_job(job_name)
                else:  # rt_info.status in ["running", "cancelled", "failed"]:
                    ...
            await asyncio.sleep(1.5)

    @classmethod
    async def on_job_started(cls, job_name: str):
        ...

    @classmethod
    async def on_job_exception(cls, job_name: str, exception: BaseException):
        ...

    @classmethod
    async def on_job_cancelled(cls, job_name: str):
        ...

    @classmethod
    async def on_job_finished(cls, job_name: str):
        ...

    @classmethod
    async def on_startup(cls):
        ...

    @classmethod
    async def on_shutdown(cls):
        ...

    # @classmethod
    # def state(cls) -> State:
    #     state = State(
    #         created_at=now(), jobs_info=[job.info() for job in cls.get_all_jobs_info()]
    #     )
    #     return state

    # @classmethod
    # def load_state(cls, state: State):
    #     cls._load_from_state = state

    # @classmethod
    # def run_from_state(cls, state: State, resumed_statuses: Tuple = ("running",)):
    #     if cls._is_running:
    #         raise Exception(f"Registered jobs were already scheduled.")
    #
    #     Job.add_done_callback(cls._handle_done_job)
    #
    #     to_be_scheduled = set(cls._jobs.keys())
    #
    #     for job_info in state.jobs_info:
    #         if job_info.name not in to_be_scheduled:
    #             logger.warning(f"Job {job_info.name} not found. Ignoring...")
    #         else:
    #             schedule_immediately = job_info.last_status in resumed_statuses
    #             cls._jobs[job_info.name].schedule(immediately=schedule_immediately)
    #             to_be_scheduled.remove(job_info.name)
    #     if len(to_be_scheduled) > 0:
    #         for job_name in to_be_scheduled:
    #             cls._jobs[job_name].schedule()
