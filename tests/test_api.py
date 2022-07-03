import asyncio
from unittest import mock, IsolatedAsyncioTestCase

import httpx
from fastapi import FastAPI
from src.aiocronjob import Manager
from src.aiocronjob.main import init_app


class TestApi(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.manager = Manager()
        fastapi_app = FastAPI()
        init_app(fastapi_app, manager=self.manager)
        self.client = httpx.AsyncClient(app=fastapi_app, base_url="http://example.com")

    def tearDown(self) -> None:
        asyncio.run(self.manager.shutdown())
        asyncio.run(self.client.aclose())

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
