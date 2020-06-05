import asyncio
import collections
from typing import Callable, Optional, Coroutine, List, OrderedDict

from aiocronjob.job import Job


class manager:
    _jobs: OrderedDict[str, Job] = collections.OrderedDict()
    _has_run: bool = False

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
    def _handle_done_job(cls, job: Job):
        status = job.get_status()

        if status == "cancelled":
            if cls.on_job_cancelled:
                asyncio.create_task(cls.on_job_cancelled(job))

        elif status == "error":
            if cls.on_job_exception:
                asyncio.create_task(cls.on_job_exception(job, job.exception()))

        else:
            if job.enabled and job.crontab:
                """ If no crontab set, job runs only once """
                cls.schedule_job(job)
