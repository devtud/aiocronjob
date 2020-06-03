from enum import Enum

from pydantic import BaseModel


class JobSettingsPatch(BaseModel):
    name: str = None
    crontab: str = None


class JobStatus(str, Enum):
    cancelled = "cancelled"
    cancelling = "cancelling"
    created = "created"
    done = "done"
    error = "error"
    pending = "pending"
    running = "running"
