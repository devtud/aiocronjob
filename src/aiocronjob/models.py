import datetime
from asyncio.tasks import Task
from dataclasses import dataclass

from pydantic import BaseModel, Field
from .typing import Literal, Coroutine, Callable, Optional, List

JobStatus = Literal[
    "registered", "running", "finished", "pending", "cancelled", "failed"
]

EventType = Literal[
    "job_registered", "job_started", "job_failed", "job_finished", "job_cancelled"
]


class JobInfo(BaseModel):
    name: str
    last_status: str
    enabled: bool
    crontab: str = None
    created_at: datetime.datetime = None
    started_at: datetime.datetime = None
    stopped_at: datetime.datetime = None
    next_run_in: int = None


class JobDefinition(BaseModel):
    name: str
    async_callable: Callable[[], Coroutine]
    enabled: bool = True
    crontab: Optional[str] = None


@dataclass
class RunningJob:
    job_definition: JobDefinition
    asyncio_task: Task
    since: datetime.datetime


class JobLog(BaseModel):
    event_type: EventType
    job_name: str
    crontab: str = None
    enabled: bool
    error: str = None
    timestamp: int = Field(default_factory=lambda: datetime.datetime.now().timestamp())


class State(BaseModel):
    created_at: datetime.datetime
    jobs_info: List[JobInfo]


class JobRealTimeInfo(BaseModel):
    name: str
    status: JobStatus
    next_run_ts: Optional[int]
