from aiocronjob.manager import manager
from fastapi import FastAPI

app = FastAPI()


@app.on_event("startup")
def init():
    manager.run()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/jobs/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}


@app.get("/jobs")
def read_jobs():
    return [
        {
            "name": job.name,
            "next_run_in": job._crontab.next(),
            "status": job.status.value,
        }
        for job in manager.jobs
    ]
