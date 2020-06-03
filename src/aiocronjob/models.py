import datetime

from pydantic import BaseModel


class Job(BaseModel):
    name: str
    status: str
    started_at: datetime.datetime
    reloaded_at: datetime.datetime
    stopped_at: datetime.datetime
