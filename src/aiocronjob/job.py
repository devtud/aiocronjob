import asyncio
from asyncio.tasks import Task
from typing import Callable, Optional, Literal

from aiocronjob.util import now
from crontab import CronTab

JobStatus = Literal[
    "cancelled", "cancelling", "created", "done", "error", "pending", "running",
]


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
        self.status: JobStatus = "created"

    def run(self, immediately=False):
        if immediately:
            delay = 0
        else:
            delay = self.crontab.next(default_utc=True)
        self.task = asyncio.create_task(
            self.run_with_delay(delay=delay), name=self.name
        )

    def cancel(self):
        if self.status != "running":
            raise Exception(f"Cannot cancel job with status {self.status}")
        self.task.cancel()
        self.status = "cancelling"

    async def run_with_delay(self, delay: float):
        self.status = "pending"
        await asyncio.sleep(delay)
        self.started_at = now()
        self.status = "running"
        try:
            result = await self._async_callable()
        except asyncio.CancelledError:
            self.status = "cancelled"
            raise
        except Exception:
            self.status = "error"
            raise
        self.status = "done"
        return result

    def set_crontab(self, crontab: str):
        self.crontab = CronTab(crontab)
        self.crontab_str = crontab

    def info(self):
        return {
            "name": self.name,
            "next_run_in": self.crontab.next(),
            "last_status": self.status,
            "enabled": self.enabled,
            "crontab": self.crontab_str,
            "created_at": self.created_at,
            "started_at": self.started_at,
        }
