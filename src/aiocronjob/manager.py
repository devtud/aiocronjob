import asyncio
import datetime
from asyncio import Task
from typing import Callable, Optional, List

from aiocronjob.models import JobStatus
from crontab import CronTab


def now():
    return datetime.datetime.utcnow()


class Job:
    def __init__(
        self,
        async_callable: Callable,
        crontab: str = None,
        name: str = None,
        enabled: bool = True,
    ):
        self._async_callable = async_callable
        self.crontab_str = ""
        self.crontab: Optional[CronTab] = None

        if crontab:
            self.set_crontab(crontab)

        self.name = name or " ".join(
            async_callable.__name__.capitalize().split("_")
        )

        self.task: Optional[Task] = None
        self.enabled = enabled
        self.created_at = now()
        self.started_at = None
        self.status: JobStatus = JobStatus.created

    def run(self, immediately=False):
        if immediately:
            delay = 0
        else:
            delay = self.crontab.next(default_utc=True)
        self.task = asyncio.create_task(self.run_with_delay(delay=delay))

    def cancel(self):
        if self.status != JobStatus.running:
            raise Exception(
                f"Cannot cancel job with status {self.status.value}"
            )
        self.task.cancel()
        self.status = JobStatus.cancelling

    async def run_with_delay(self, delay: float):
        self.status = JobStatus.pending
        await asyncio.sleep(delay)
        self.started_at = now()
        self.status = JobStatus.running
        try:
            result = await self._async_callable()
        except asyncio.CancelledError:
            self.status = JobStatus.cancelled
            raise
        except Exception:
            self.status = JobStatus.error
            raise
        self.status = JobStatus.done
        return result

    def set_crontab(self, crontab: str):
        self.crontab = CronTab(crontab)
        self.crontab_str = crontab

    def dict(self):
        return {
            "name": self.name,
            "next_run_in": self.crontab.next(),
            "last_status": self.status.value,
            "enabled": self.enabled,
            "crontab": self.crontab_str,
            "created_at": self.created_at,
            "started_at": self.started_at,
        }


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
        job.run(immediately)
        job.task.add_done_callback(cls.handle_done_job)

    @classmethod
    def run(cls):
        for job in cls.jobs:
            if job.enabled and job.crontab:
                cls.schedule_job(job)


manager = JobManager()
