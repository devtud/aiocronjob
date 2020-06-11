from pathlib import Path
from typing import List

from aiocronjob.job import JobInfo
from aiocronjob.manager import manager
from fastapi import FastAPI, HTTPException, APIRouter, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.responses import JSONResponse
from starlette.staticfiles import StaticFiles

app = FastAPI(title="AIOCronJob", version="0.2.0")

api_router = APIRouter()

origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown():
    if manager.on_shutdown:
        await manager.on_shutdown()


@api_router.get("/")
def read_root():
    return {"Hello": "World"}


class OperationStatus(BaseModel):
    success: bool
    detail: str = None


class OperationStatusResponse(JSONResponse):
    def __init__(
        self, *, success: bool = True, detail: str = None, status_code: int = 200
    ):
        content = OperationStatus(success=success, detail=detail)
        super().__init__(content.dict(), status_code=status_code)


@api_router.get("/jobs", response_model=List[JobInfo])
async def get_jobs() -> List[JobInfo]:
    """ List all registered jobs info """
    return [job.info() for job in manager.list_jobs()]


@api_router.get("/jobs/{job_name}", response_model=JobInfo)
async def get_job_info(job_name: str) -> JobInfo:
    """ Get a job info """
    job = manager.get_job(job_name)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.info()


@api_router.get("/jobs/{job_name}/cancel", response_model=OperationStatus)
async def cancel_job(job_name: str) -> OperationStatusResponse:
    job = manager.get_job(job_name)
    if not job:
        return OperationStatusResponse(
            success=False, status_code=404, detail="Job not found"
        )
    job.cancel()
    return OperationStatusResponse()


@api_router.get("/jobs/{job_name}/start", response_model=OperationStatus)
async def start_job(job_name: str) -> OperationStatusResponse:
    job = manager.get_job(job_name)
    if not job:
        return OperationStatusResponse(
            success=False, status_code=404, detail="Job not found"
        )

    job.schedule(immediately=True, ignore_pending=True)

    return OperationStatusResponse()


@api_router.post("/jobs/{job_name}/reschedule", response_model=OperationStatus)
async def reschedule_job(
    job_name: str, crontab: str = Body("")
) -> OperationStatusResponse:
    """ Changes the crontab specification of a job. In case of a running job, the new
    crontab will be effective after the job is done.
    """
    job = manager.get_job(job_name)
    if not job:
        return OperationStatusResponse(
            success=False, status_code=404, detail="Job not found"
        )
    if crontab:
        try:
            job.set_crontab(crontab=crontab)
        except ValueError as e:
            return OperationStatusResponse(
                success=False, status_code=400, detail=f"Bad crontab format: {str(e)}"
            )
    if job.get_status() != "running":
        job.schedule(ignore_pending=True)
    return OperationStatusResponse()


app.include_router(api_router, prefix="/api", tags=["api"])

app.mount(
    "/",
    StaticFiles(
        directory=Path(__file__).parent.joinpath("build").absolute(), html=True,
    ),
    name="static",
)
