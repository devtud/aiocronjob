import asyncio
from unittest import mock

import httpx
from aiocronjob import Manager
from aiocronjob.main import init_app
from fastapi import FastAPI

from .common import IsolatedAsyncioTestCase


class TestApi(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.manager = Manager()
        fastapi_app = FastAPI()
        init_app(fastapi_app, manager=self.manager)
        self.client = httpx.AsyncClient(app=fastapi_app, base_url="http://example.com")

    def tearDown(self) -> None:
        asyncio.get_event_loop().run_until_complete(self.manager.shutdown())
        asyncio.get_event_loop().run_until_complete(self.client.aclose())

    async def test_list_jobs(self):
        self.maxDiff = None

        async def task1():
            await asyncio.sleep(5)

        async def task2():
            await asyncio.sleep(5)

        self.manager.register(task1)
        self.manager.register(task2)

        response = await self.client.get("/api/jobs")

        desired_output = [
            {
                "name": "task1",
                "next_run_in": None,
                "last_status": "registered",
                "enabled": True,
                "crontab": None,
                "created_at": mock.ANY,
                "started_at": mock.ANY,
                "stopped_at": mock.ANY,
            },
            {
                "name": "task2",
                "next_run_in": None,
                "last_status": "registered",
                "enabled": True,
                "crontab": None,
                "created_at": mock.ANY,
                "started_at": mock.ANY,
                "stopped_at": mock.ANY,
            },
        ]

        self.assertEqual(desired_output, response.json())
