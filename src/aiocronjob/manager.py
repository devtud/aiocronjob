import asyncio
from asyncio import Task
from typing import Callable, Optional, List, Coroutine

from aiocronjob.job import Job


class JobManager:
    jobs: List[Job] = []

    on_job_cancelled: Optional[Callable[[str], Coroutine]] = None
    on_job_exception: Optional[Callable[[str, BaseException], Coroutine]] = None
    on_startup: Optional[Callable[[], Coroutine]] = None
    on_shutdown: Optional[Callable[[], Coroutine]] = None

    @classmethod
    def register(
        cls, async_callable: Callable, crontab: str = None, name: str = None,
    ):
        cls.jobs.append(
            Job(async_callable=async_callable, crontab=crontab, name=name)
        )

    @classmethod
    def get_job(cls, name: str) -> Optional[Job]:
        jobs = list(filter(lambda j: j.name == name, cls.jobs))
        if jobs:
            return jobs[0]
        return None

    @classmethod
    def get_job_by_task(cls, task: Task) -> Optional[Job]:
        jobs = list(filter(lambda j: j.task == task, cls.jobs))
        if jobs:
            return jobs[0]
        return None

    @classmethod
    def handle_done_job(cls, task: Task):
        job = cls.get_job_by_task(task)

        task.remove_done_callback(cls.handle_done_job)

        if task.cancelled():
            if cls.on_job_cancelled:
                asyncio.create_task(cls.on_job_cancelled(job.name))

        elif task.exception():
            if cls.on_job_exception:
                asyncio.create_task(
                    cls.on_job_exception(job.name, task.exception())
                )

        else:
            if job.enabled and job.crontab:
                """ If no crontab set, job runs only once """
                cls.schedule_job(job)

    @classmethod
    def set_on_job_cancelled_callback(
        cls, callback: Callable[[str], Coroutine]
    ):
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
        cls,
        callback: Callable[[str, BaseException], Coroutine],
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
        if job.status == "running":
            raise Exception("Job is already running")

        if job.task and not job.task.done():
            job.task.remove_done_callback(cls.handle_done_job)
            job.task.cancel()

        job.run(immediately)
        job.task.add_done_callback(cls.handle_done_job)

    @classmethod
    def run(cls):
        for job in cls.jobs:
            if job.enabled and job.crontab:
                cls.schedule_job(job)


manager = JobManager()
