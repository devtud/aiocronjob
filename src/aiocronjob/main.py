import asyncio
from pathlib import Path
from typing import Dict

import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from .api import add_routes
from .logger import logger
from .manager import Manager
from .models import State


def init_app(app: FastAPI, manager: Manager):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    add_routes(
        app=app,
        path="/api",
        manager=manager,
    )

    static_dir = Path(__file__).parent.joinpath("build").absolute()

    if static_dir.exists():
        app.mount(
            "/",
            StaticFiles(directory=static_dir, html=True),
            name="static",
        )
    else:
        logger.warning("Static directory does not exist!")


def run_app(
    manager: Manager,
    fastapi_app: FastAPI = None,
    state: State = None,
    host="0.0.0.0",
    port=5000,
    log_level="info",
):
    _main_task: Dict[str, asyncio.Task] = {}

    if fastapi_app is None:
        fastapi_app = FastAPI(
            title="AIOCronJob",
            version="0.3.0",
        )

    init_app(fastapi_app, manager)

    @fastapi_app.on_event("startup")
    async def init():
        _main_task["task"] = asyncio.get_event_loop().create_task(
            manager.run(state=state),
        )

    @fastapi_app.on_event("shutdown")
    async def shutdown():
        logger.info("App is shutting down...")
        logger.info("Shutting down Manager...")
        await manager.shutdown()
        logger.info("Shutting down main task...")
        await _main_task["task"]

    uvicorn.run(
        app=fastapi_app,
        host=host,
        port=port,
        log_level=log_level,
    )
