import asyncio
from typing import Dict

from starlite import Starlite
from .api import api_router
from .dependencies import get_manager
from .logger import logger

_main_task: Dict[str, asyncio.Task] = {}


async def init():
    manager = get_manager()
    if not manager:
        raise Exception("Please call .set_default() method on your custom manager.")

    global _main_task
    _main_task["task"] = asyncio.create_task(manager.run())


async def shutdown():
    logger.info("App is shutting down...")
    logger.info("Shutting down Manager...")
    manager = get_manager()
    await manager.shutdown()
    logger.info("Shutting down main task...")
    try:
        await _main_task["task"]
    except asyncio.CancelledError:
        logger.info("Shut down complete.")


app = Starlite(route_handlers=[api_router], on_startup=[init], on_shutdown=[shutdown])
