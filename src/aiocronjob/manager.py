import asyncio
import datetime
from asyncio import Task
from enum import Enum
from typing import Callable, Union, Optional, List

from crontab import CronTab


def now():
    return datetime.datetime.utcnow()


class JobStatus(str, Enum):
    created = "created"
    done = "done"
    pending = "pending"
    running = "running"
    error = "error"


class Job:
    def __init__(
            self,
            async_callable: Callable,
            crontab: Union[str, CronTab],
            name: str = None,
    ):
        self._async_callable = async_callable

        if isinstance(crontab, str):
            self._crontab = CronTab(crontab)
        else:
            self._crontab = crontab

        self.name = name or " ".join(
            async_callable.__name__.capitalize().split("_")
        )

        self.future: Optional[Task] = None
        self.created_at = now()
        self.started_at = None
        self.status: JobStatus = JobStatus.created

    def run(self):
        self.future = asyncio.create_task(
            self.run_with_delay(delay=self._crontab.next(default_utc=True))
        )

    async def run_with_delay(self, delay: float):
        self.status = JobStatus.pending
        await asyncio.sleep(delay)
        self.started_at = now()
        self.status = JobStatus.running
        try:
            result = await self._async_callable()
        except Exception as e:
            self.status = JobStatus.error
            raise e
        self.status = JobStatus.done
        return result


class JobManager:
    jobs: List[Job] = []

    @classmethod
    def register(
            cls, async_callable: Callable, crontab: str, name: str = None,
    ):
        cls.jobs.append(
            Job(async_callable=async_callable, crontab=crontab, name=name)
        )

    @classmethod
    def handle_done_job(cls, job_name: str):
        def handler(task: Task):
            print("the task:", task, id(task))
            job = list(filter(lambda j: j.name == job_name, cls.jobs))[0]
            print("the future:", job.future, id(job.future))
            if job.future.cancelled():
                pass
            elif job.future.exception():
                print(
                    f"An exception occurred in task {job.name}: {job.future.exception()}"
                )
            else:
                print(f"Job {job.name} finished successfully! Rescheduling...")
                job.run()

        return handler

    @classmethod
    def run(cls):
        for job in cls.jobs:
            job.run()
            job.future.add_done_callback(cls.handle_done_job(job_name=job.name))


manager = JobManager()
