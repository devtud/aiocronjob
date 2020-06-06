import asyncio
import collections
import datetime
from asyncio import Task
from typing import Callable, Optional, Coroutine, List, Tuple

from aiocronjob.job import Job, JobInfo
from aiocronjob.logger import logger
from aiocronjob.util import now
from pydantic import BaseModel

try:
    from typing import OrderedDict
except ImportError:
    from typing import Dict

    OrderedDict = Dict


class State(BaseModel):
    created_at: datetime.datetime
    jobs_info: List[JobInfo]


class manager:
    _jobs: OrderedDict[str, Job] = collections.OrderedDict()
    _has_run: bool = False
    _load_from_state: State

    on_job_cancelled: Optional[Callable[[Job], Coroutine]] = None
    on_job_exception: Optional[Callable[[Job, BaseException], Coroutine]] = None
    on_startup: Optional[Callable[[], Coroutine]] = None
    on_shutdown: Optional[Callable[[], Coroutine]] = None

    @classmethod
    def register(
        cls,
        async_callable: Callable[[], Coroutine],
        crontab: str = None,
        name: str = None,
    ):
        name_prefix = f"Job_{len(cls._jobs)}-"
        name = name or f"{name_prefix}{async_callable.__name__}"

        job = Job(async_callable=async_callable, crontab=crontab, name=name)

        if job.name in cls._jobs:
            raise Exception(f"Job {job.name} already exists.")
        cls._jobs[job.name] = job

    @classmethod
    def get_job(cls, name: str) -> Optional[Job]:
        return cls._jobs.get(name)

    @classmethod
    def list_jobs(cls) -> List[Job]:
        return list(cls._jobs.values())

    @classmethod
    def set_on_job_cancelled_callback(cls, callback: Callable[[Job], Coroutine]):
        """
        Sets on-job-cancelled callback.

        Args:
            callback: Async function which receives the job's name
                to be executed after a job is cancelled. Its return
                value is ignored.

        Returns:
            None

        """
        cls.on_job_cancelled = callback

    @classmethod
    def set_on_job_exception_callback(
        cls, callback: Callable[[Job, BaseException], Coroutine],
    ):
        cls.on_job_exception = callback

    @classmethod
    def set_on_startup_callback(cls, callback: Callable[[], Coroutine]):
        cls.on_startup = callback

    @classmethod
    def set_on_shutdown_callback(cls, callback: Callable[[], Coroutine]):
        cls.on_shutdown = callback

    @classmethod
    def schedule_job(cls, job: Job, immediately: bool = False):
        job.schedule(immediately)

    @classmethod
    def run(cls):
        if cls._has_run:
            raise Exception(f"Registered jobs were already scheduled.")

        Job.add_done_callback(cls._handle_done_job)

        for job in cls._jobs.values():
            if job.enabled and job.crontab:
                cls.schedule_job(job)
        cls._has_run = True

    @classmethod
    def state(cls) -> State:
        state = State(
            created_at=now(), jobs_info=[job.info() for job in cls.list_jobs()]
        )
        return state

    @classmethod
    def load_state(cls, state: State):
        cls._load_from_state = state

    @classmethod
    def run_from_state(cls, state: State, resumed_statuses: Tuple = ("running",)):
        if cls._has_run:
            raise Exception(f"Registered jobs were already scheduled.")

        Job.add_done_callback(cls._handle_done_job)

        to_be_scheduled = set(cls._jobs.keys())

        for job_info in state.jobs_info:
            if job_info.name not in to_be_scheduled:
                logger.warning(f"Job {job_info.name} not found. Ignoring...")
            else:
                schedule_immediately = job_info.last_status in resumed_statuses
                cls._jobs[job_info.name].schedule(immediately=schedule_immediately)
                to_be_scheduled.remove(job_info.name)
        if len(to_be_scheduled) > 0:
            for job_name in to_be_scheduled:
                cls._jobs[job_name].schedule()

    @classmethod
    def _handle_done_job(cls, job: Job):
        status = job.get_status()

        def create_task(coro) -> Task:
            if hasattr(asyncio, "create_task"):
                return asyncio.create_task(coro)
            else:
                loop = asyncio.get_event_loop()
                return loop.create_task(coro)

        if status == "cancelled":
            if cls.on_job_cancelled:
                create_task(cls.on_job_cancelled(job))

        elif status == "error":
            if cls.on_job_exception:
                create_task(cls.on_job_exception(job, job.exception()))

        else:
            if job.enabled and job.crontab:
                """ If no crontab set, job runs only once """
                cls.schedule_job(job)
