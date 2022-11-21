import datetime
from typing import Literal, Coroutine, Callable, Optional

from pydantic import BaseModel, Field

JobStatus = Literal[
    "registered", "running", "finished", "pending", "cancelled", "failed"
]

EventType = Literal[
    "job_registered", "job_started", "job_failed", "job_finished", "job_cancelled"
]


class JobDefinition(BaseModel):
    name: str
    async_callable: Callable[[], Coroutine]
    enabled: bool = True
    crontab: Optional[str] = None


class JobInfo(BaseModel):
    definition: JobDefinition
    created_at: datetime.datetime = None
    last_status: JobStatus = None
    last_start: datetime.datetime = None
    last_finish: datetime.datetime = None
    last_finish_status: JobStatus = None
    next_start: datetime.datetime = None
    status: JobStatus


class JobLog(BaseModel):
    event_type: EventType
    job_name: str
    crontab: str = None
    enabled: bool
    error: str = None
    timestamp: int = Field(default_factory=lambda: datetime.datetime.now().timestamp())


class State(BaseModel):
    created_at: datetime.datetime
    jobs_info: list[dict]
