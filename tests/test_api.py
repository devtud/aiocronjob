import asyncio
from unittest import mock

from aiocronjob import app, Manager
from starlette.testclient import TestClient

from .common import IsolatedAsyncioTestCase

client = TestClient(app=app)


class TestApi(IsolatedAsyncioTestCase):
    def test_list_jobs(self):
        self.maxDiff = None

        async def task1():
            await asyncio.sleep(5)

        async def task2():
            await asyncio.sleep(5)

        Manager.register(task1)
        Manager.register(task2)

        response = client.get("/api/jobs")

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
