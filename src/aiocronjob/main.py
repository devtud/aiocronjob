import asyncio
from typing import Dict, Type

import uvicorn
from aiocronjob.logger import logger
from fastapi import FastAPI

from .api import app
from .manager import Manager
from .models import State


def run_app(
    manager_class: Type[Manager] = Manager,
    fastapi_app: FastAPI = app,
    state: State = None,
    host="0.0.0.0",
    port=5000,
    log_level="info",
):
    _main_task: Dict[str, asyncio.Task] = {}

    @fastapi_app.on_event("startup")
    async def init():
        if Manager.on_startup:
            await Manager.on_startup()

        _main_task["task"] = asyncio.get_event_loop().create_task(
            manager_class.run(state=state)
        )

    @fastapi_app.on_event("shutdown")
    async def shutdown():
        logger.info("Logger is shutting down...")
        logger.info("Shutting down Manager...")
        await Manager.shutdown()
        logger.info("Shutting down main task...")
        await _main_task["task"]

    uvicorn.run(app=app, host=host, port=port, log_level=log_level)
