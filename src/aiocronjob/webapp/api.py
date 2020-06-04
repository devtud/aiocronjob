from typing import Optional

from aiocronjob.manager import manager
from fastapi import FastAPI, HTTPException, APIRouter

app = FastAPI()

api_router = APIRouter()


@app.on_event("startup")
async def init():
    if manager.on_startup:
        await manager.on_startup.__func__()
    manager.run()


@app.on_event("shutdown")
async def shutdown():
    if manager.on_shutdown:
        await manager.on_shutdown.__func__()


@api_router.get("/")
def read_root():
    return {"Hello": "World"}


@api_router.get("/jobs")
async def get_jobs():
    return [job.info() for job in manager.jobs]


@api_router.get("/jobs/{job_name}")
async def get_job(job_name: str):
    job = manager.get_job(job_name)
    if not job:
        raise HTTPException(status_code=404, detail="Not job found")
    return job.info()


@api_router.get("/jobs/{job_name}/cancel")
async def cancel_job(job_name: str):
    job = manager.get_job(job_name)
    if not job:
        raise HTTPException(status_code=404, detail="Not job found")
    job.cancel()
    return {"success": True}


@api_router.get("/jobs/{job_name}/start")
async def start_job(job_name: str):
    job = manager.get_job(job_name)
    if not job:
        raise HTTPException(status_code=404, detail="Not job found")
    manager.schedule_job(job=job, immediately=True)
    return {"success": True}


@api_router.get("/jobs/{job_name}/reschedule/{crontab}")
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


@api_router.get("/jobs/{job_name}/reschedule")
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


app.include_router(api_router, prefix="/api", tags=["api"])
