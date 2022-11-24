import asyncio
import datetime
import json
from unittest import mock, IsolatedAsyncioTestCase

import httpx
from async_asgi_testclient import TestClient
from src.aiocronjob import Manager, State
from src.aiocronjob.main import app, init, shutdown, _main_task


class TestApi(IsolatedAsyncioTestCase):
    maxDiff = None

    async def asyncSetUp(self) -> None:
        self.manager = Manager()
        self.manager.set_default()
        self.client = httpx.AsyncClient(app=app, base_url="http://testserver")

    async def asyncTearDown(self) -> None:
        await self.manager.shutdown()
        await self.client.aclose()

    async def test_get_job(self):
        async def task1():
            await asyncio.sleep(1)

        self.manager.register(task1)

        response = await self.client.get("/api/jobs/task1")

        desired_output = {
            "name": "task1",
            "next_run_in": None,
            "last_status": "registered",
            "enabled": True,
            "crontab": None,
            "created_at": mock.ANY,
            "started_at": mock.ANY,
            "stopped_at": mock.ANY,
        }

        self.assertEqual(desired_output, response.json())

    async def test_get_non_existing_job_returns_404(self):
        response = await self.client.get("/api/jobs/non_existing_job")

        self.assertEqual(404, response.status_code)

        self.assertEqual(
            {"detail": "Job not found", "status_code": 404}, response.json()
        )

    async def test_cancel_non_existing_job_returns_404(self):
        response = await self.client.get("/api/jobs/non_existing_job/cancel")

        self.assertEqual(404, response.status_code)

        self.assertEqual(
            {"detail": "Job not found", "status_code": 404}, response.json()
        )

    async def test_cancel_not_running_job_returns_402(self):
        async def task1():
            await asyncio.sleep(1)

        self.manager.register(task1)

        response = await self.client.get("/api/jobs/task1/cancel")

        self.assertEqual(402, response.status_code)

        desired_output = {"status_code": 402, "detail": "Job not running"}

        self.assertEqual(desired_output, response.json())

    async def test_start_job(self):
        async def task1():
            await asyncio.sleep(1)

        self.manager.register(task1)

        response = await self.client.get("/api/jobs/task1/start")

        self.assertEqual(None, response.json())

        self.assertEqual("running", self.manager._jobs["task1"].status)

    async def test_start_non_existing_job_returns_404(self):
        response = await self.client.get("/api/jobs/non_existing_job/start")

        self.assertEqual(404, response.status_code)

        self.assertEqual(
            {"detail": "Job not found", "status_code": 404}, response.json()
        )

    async def test_start_running_job_returns_402(self):
        async def task1():
            await asyncio.sleep(1)

        self.manager.register(task1)

        await self.manager.start_job("task1")

        await asyncio.sleep(1)

        response = await self.client.get("/api/jobs/task1/start")

        self.assertEqual(402, response.status_code)

        desired_output = {"status_code": 402, "detail": "Job already running"}

        self.assertEqual(desired_output, response.json())

    async def test_cancel_job(self):
        async def task1():
            await asyncio.sleep(1)

        self.manager.register(task1)

        await self.manager.start_job("task1")

        await asyncio.sleep(1)

        response = await self.client.get("/api/jobs/task1/cancel")

        self.assertEqual(None, response.json())

        await asyncio.sleep(1)

        self.assertEqual("cancelled", self.manager._jobs["task1"].status)

    async def test_list_jobs(self):
        async def task1():
            await asyncio.sleep(1)

        async def task2():
            await asyncio.sleep(1)

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

    async def test_init_and_shutdown_manager(self):
        await init()
        self.assertIn("task", _main_task)
        self.assertFalse(_main_task["task"].done())
        await shutdown()
        self.assertTrue(_main_task["task"].done())

    async def test_log_stream(self):
        async def task1():
            await asyncio.sleep(0.1)

        self.manager.register(task1)

        client = TestClient(app)
        resp = await client.get("/api/log-stream", stream=True)
        async for chunk in resp.iter_content(chunk_size=10000):
            self.assertEqual(
                {
                    "event_type": "job_registered",
                    "job_name": "task1",
                    "crontab": None,
                    "enabled": True,
                    "error": None,
                    "timestamp": mock.ANY,
                },
                json.loads(chunk.decode()),
            )
            break
