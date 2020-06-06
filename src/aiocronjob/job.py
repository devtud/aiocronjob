import asyncio
import datetime
from asyncio.tasks import Task
from typing import Callable, Optional, Coroutine, NewType

from aiocronjob.util import now
from crontab import CronTab
from pydantic import BaseModel

try:
    from typing import Literal

    JobStatus = Literal[
        "cancelled", "created", "done", "error", "pending", "running",
    ]
except ImportError:
    JobStatus = NewType("JobStatus", str)


class JobInfo(BaseModel):
    name: str
    next_run_in: str = None
    last_status: str
    enabled: str
    crontab: str
    created_at: datetime.datetime
    started_at: datetime.datetime = None
    stopped_at: datetime.datetime = None


class Job:
    """ Wraps an async callable and delays its execution according
    to a crontab specification
    """

    _done_callback: Optional[Callable[["Job"], None]] = None

    def __init__(
        self,
        async_callable: Callable[[], Coroutine],
        name: str,
        crontab: str = "",
        enabled: bool = True,
    ):
        self._async_callable = async_callable
        self.crontab_str = ""
        self.crontab: Optional[CronTab] = None

        if crontab:
            self.set_crontab(crontab)

        self.name = name
        self.enabled = enabled
        self.created_at = now()
        self.started_at: Optional[datetime.datetime] = None
        self.stopped_at: Optional[datetime.datetime] = None

        self._task: Optional[Task] = None

    def schedule(self, immediately=False, ignore_pending: bool = False) -> Task:
        """ Runs the job immediately or according to its cronjob spec """
        status = self.get_status()

        if status == "pending":
            if not ignore_pending:
                raise Exception(
                    f"Job is pending. Use `ignore_pending` to force scheduling."
                )

            # Going to cancel the task only to start another one,
            # so there is no need to call the done callback
            self._task.remove_done_callback(self._task_done_callback)
            self._task.cancel()
        elif status == "running":
            raise Exception(f"Job is already running.")

        if immediately:
            delay = 0
        else:
            if self.crontab_str:
                delay = self.crontab.next(default_utc=True)
            else:
                raise Exception(
                    f"Jobs with no crontab spec must be ran with `immediately` flag `True`"
                )

        if hasattr(asyncio, "create_task"):
            self._task = asyncio.create_task(self.run_with_delay(delay=delay))
        else:
            loop = asyncio.get_event_loop()
            self._task = loop.create_task(self.run_with_delay(delay=delay))

        self._task.add_done_callback(self._task_done_callback)

        return self._task

    async def run_with_delay(self, delay: float):
        self.started_at = self.stopped_at = None

        await asyncio.sleep(delay)

        self.started_at = now()

        try:
            result = await self._async_callable()
        finally:
            self.stopped_at = now()
        return result

    def cancel(self) -> bool:
        """ Cancels a running job. """
        if self._task.done():
            raise Exception(f"Job is not running [status={self.get_status()}].")
        return self._task.cancel()

    def exception(self) -> BaseException:
        return self._task.exception()

    def get_status(self) -> JobStatus:
        if self._task:
            if self._task.done():
                if self._task.cancelled():
                    return "cancelled"
                elif self._task.exception():
                    return "error"
                else:
                    return "done"
            else:
                if self.started_at is None:
                    return "pending"
                else:
                    if self.stopped_at is None:
                        return "running"
        else:
            return "created"
        raise Exception("unknown job status")

    def set_crontab(self, crontab: str):
        """ Sets a new crontab or removes the existing one if `crontab`
        is empty string
        """
        if not crontab:
            self.crontab = None
        else:
            self.crontab = CronTab(crontab)
        self.crontab_str = crontab

    def _task_done_callback(self, task: Task):
        if self._done_callback:
            self._done_callback(self)

    @classmethod
    def add_done_callback(cls, callback: Callable[["Job"], None]):
        cls._done_callback = callback

    def info(self) -> JobInfo:
        return JobInfo(
            name=self.name,
            next_run_in=self.crontab.next() if self.crontab_str else None,
            last_status=self.get_status(),
            enabled=self.enabled,
            crontab=self.crontab_str,
            created_at=self.created_at,
            started_at=self.started_at,
            stopped_at=self.stopped_at,
        )
