import asyncio
from asyncio import Task
from typing import Callable, Optional, List

from aiocronjob.job import Job


class JobManager:
    jobs: List[Job] = []
    on_cancel_callback = None
    on_exception_callback = None

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
            if cls.on_cancel_callback:
                asyncio.create_task(cls.on_cancel_callback(job.name))

        elif task.exception():
            if cls.on_exception_callback:
                asyncio.create_task(
                    cls.on_exception_callback(job.name, task.exception())
                )

        else:
            if job.enabled and job.crontab:
                """ If no crontab set, job runs only once """
                cls.schedule_job(job)

    @classmethod
    def set_on_cancel_callback(cls, callback: Callable[[str], None]):
        cls.on_cancel_callback = callback

    @classmethod
    def set_on_exception_callback(
        cls, callback: Callable[[str, Exception], None]
    ):
        cls.on_exception_callback = callback

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
