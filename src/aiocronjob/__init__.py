import uvicorn

from .job import Job, JobInfo, JobStatus
from .manager import manager, State
from aiocronjob.api import app


def run_app(state: State = None, host="0.0.0.0", port=5000):
    @app.on_event("startup")
    async def init():
        if manager.on_startup:
            await manager.on_startup()
        if state:
            manager.run_from_state(state=state)
        else:
            manager.run()

    uvicorn.run(app=app, host=host, port=port, log_level="info")
