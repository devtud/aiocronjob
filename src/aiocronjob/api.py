from typing import Optional

from aiocronjob.manager import manager
from fastapi import FastAPI, HTTPException

app = FastAPI()


@app.on_event("startup")
def init():
    manager.run()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/jobs")
async def get_jobs():
    return [job.dict() for job in manager.jobs]


@app.get("/jobs/{job_name}")
async def get_job(job_name: str):
    job = manager.get_job(job_name)
    if not job:
        raise HTTPException(status_code=404, detail="Not job found")
    return job.dict()


@app.get("/jobs/{job_name}/cancel")
async def cancel_job(job_name: str):
    job = manager.get_job(job_name)
    if not job:
        raise HTTPException(status_code=404, detail="Not job found")
    job.cancel()
    return {"success": True}


@app.get("/jobs/{job_name}/start")
async def start_job(job_name: str):
    job = manager.get_job(job_name)
    if not job:
        raise HTTPException(status_code=404, detail="Not job found")
    manager.schedule_job(job=job, immediately=True)
    return {"success": True}


@app.get("/jobs/{job_name}/reschedule/{crontab}")
async def reschedule_job(job_name: str, crontab: Optional[str]):
    job = manager.get_job(job_name)
    if not job:
        raise HTTPException(status_code=404, detail="Not job found")
    try:
        job.set_crontab(crontab=crontab)
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=f"Bad crontab format: {str(e)}"
        )
    manager.schedule_job(job=job)
    return {"success": True}


@app.get("/jobs/{job_name}/reschedule")
async def reschedule_job(job_name: str):
    job = manager.get_job(job_name)
    if not job:
        raise HTTPException(status_code=404, detail="Not job found")
    if not job.crontab_str:
        raise HTTPException(
            status_code=400, detail="Cannot reschedule job with no crontab"
        )
    manager.schedule_job(job=job)
    return {"success": True}
