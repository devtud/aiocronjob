from typing import List

from starlite import HTTPException, Router, get, Provide, Stream, MediaType
from .dependencies import get_manager
from .exceptions import (
    JobNotFoundException,
    JobNotRunningException,
    JobAlreadyRunningException,
)
from .manager import Manager


@get("/jobs", dependencies={"manager": Provide(get_manager)}, media_type=MediaType.JSON)
async def get_jobs(manager: Manager) -> List[dict]:
    """List all registered jobs info"""
    return [
        job.dict(exclude={"definition": {"async_callable"}})
        for job in manager.get_jobs_info()
    ]


@get(
    "/jobs/{job_name:str}",
    dependencies={"manager": Provide(get_manager)},
    media_type=MediaType.JSON,
)
async def get_job_info(job_name: str, manager: Manager) -> dict:
    """Get a job info"""
    try:
        job_info = manager.get_job_info(job_name)
    except JobNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    return job_info.dict(exclude={"definition": {"async_callable"}})


@get(
    "/jobs/{job_name:str}/cancel",
    dependencies={"manager": Provide(get_manager)},
    media_type=MediaType.JSON,
)
async def cancel_job(job_name: str, manager: Manager) -> None:
    try:
        await manager.cancel_job(job_name)
    except JobNotFoundException as e:
        raise HTTPException(detail=str(e), status_code=404)
    except JobNotRunningException as e:
        raise HTTPException(detail=str(e), status_code=402)
    return None


@get(
    "/jobs/{job_name:str}/start",
    dependencies={"manager": Provide(get_manager)},
    media_type=MediaType.JSON,
)
async def start_job(job_name: str, manager: Manager) -> None:
    try:
        await manager.start_job(job_name)
    except JobNotFoundException as e:
        raise HTTPException(detail=str(e), status_code=404)
    except JobAlreadyRunningException as e:
        raise HTTPException(detail=str(e), status_code=402)
    return None


@get("/log-stream", dependencies={"manager": Provide(get_manager)})
async def stream_logs(manager: Manager) -> Stream:
    log_generator = manager.generate_logs(as_json_lines=True)
    return Stream(iterator=log_generator)


api_router = Router(
    "/api",
    route_handlers=[get_jobs, get_job_info, cancel_job, start_job, stream_logs],
)
