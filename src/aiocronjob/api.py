from pathlib import Path

from aiocronjob.exceptions import (
    JobNotFoundException,
    JobNotRunningException,
    JobAlreadyRunningException,
)
from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.responses import JSONResponse, StreamingResponse
from starlette.staticfiles import StaticFiles

from .logger import logger
from .manager import Manager
from .models import JobInfo
from .typing import List

app = FastAPI(title="AIOCronJob", version="0.3.0")

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
    return Manager.get_all_jobs_info()


@api_router.get("/jobs/{job_name}", response_model=JobInfo)
async def get_job_info(job_name: str) -> JobInfo:
    """ Get a job info """
    job_info = Manager.get_job_info(job_name)
    if not job_info:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_info


@api_router.get("/jobs/{job_name}/cancel", response_model=OperationStatus)
async def cancel_job(job_name: str) -> OperationStatusResponse:
    try:
        cancelled = await Manager.cancel_job(job_name)
    except JobNotFoundException:
        raise HTTPException(status_code=404, detail="Job not found")
    except JobNotRunningException as e:
        return OperationStatusResponse(success=False, status_code=402, detail=str(e))

    return OperationStatusResponse(success=cancelled, status_code=200)


@api_router.get("/jobs/{job_name}/start", response_model=OperationStatus)
async def start_job(job_name: str) -> OperationStatusResponse:
    try:
        Manager.start_job(job_name)
    except JobNotFoundException:
        raise HTTPException(status_code=404, detail="Job not found")
    except JobAlreadyRunningException as e:
        return OperationStatusResponse(success=False, status_code=402, detail=str(e))

    return OperationStatusResponse()


@api_router.get("/log-stream")
async def stream_logs():
    log_generator = Manager.generate_logs()
    return StreamingResponse(f"{log.json()}\n" async for log in log_generator)


app.include_router(api_router, prefix="/api", tags=["api"])

static_dir = Path(__file__).parent.joinpath("build").absolute()

if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    logger.warning("Static directory does not exist!")
