from fastapi import HTTPException, APIRouter, FastAPI
from pydantic import BaseModel
from starlette.responses import JSONResponse, StreamingResponse

from .exceptions import (
    JobNotFoundException,
    JobNotRunningException,
    JobAlreadyRunningException,
)
from .manager import Manager
from .models import JobInfo
from .typing import List


class OperationStatus(BaseModel):
    success: bool
    detail: str = None


class OperationStatusResponse(JSONResponse):
    def __init__(
        self, *, success: bool = True, detail: str = None, status_code: int = 200
    ):
        content = OperationStatus(success=success, detail=detail)
        super().__init__(content.dict(), status_code=status_code)


def add_routes(app: FastAPI, path: str, manager: Manager):
    api_router = APIRouter()

    @api_router.get("/jobs", response_model=List[JobInfo])
    async def get_jobs() -> List[JobInfo]:
        """ List all registered jobs info """
        return manager.get_all_jobs_info()

    @api_router.get("/jobs/{job_name}", response_model=JobInfo)
    async def get_job_info(job_name: str) -> JobInfo:
        """ Get a job info """
        job_info = manager.get_job_info(job_name)
        if not job_info:
            raise HTTPException(status_code=404, detail="Job not found")
        return job_info

    @api_router.get("/jobs/{job_name}/cancel", response_model=OperationStatus)
    async def cancel_job(job_name: str) -> OperationStatusResponse:
        try:
            cancelled = await manager.cancel_job(job_name)
        except JobNotFoundException:
            raise HTTPException(status_code=404, detail="Job not found")
        except JobNotRunningException as e:
            return OperationStatusResponse(
                success=False, status_code=402, detail=str(e)
            )

        return OperationStatusResponse(success=cancelled, status_code=200)

    @api_router.get("/jobs/{job_name}/start", response_model=OperationStatus)
    async def start_job(job_name: str) -> OperationStatusResponse:
        try:
            manager.start_job(job_name)
        except JobNotFoundException:
            raise HTTPException(status_code=404, detail="Job not found")
        except JobAlreadyRunningException as e:
            return OperationStatusResponse(
                success=False, status_code=402, detail=str(e)
            )

        return OperationStatusResponse()

    @api_router.get("/log-stream")
    async def stream_logs():
        log_generator = manager.generate_logs()
        return StreamingResponse(f"{log.json()}\n" async for log in log_generator)

    app.include_router(
        api_router,
        prefix=path,
    )
