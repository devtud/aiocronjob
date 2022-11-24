import asyncio
import datetime
from unittest import IsolatedAsyncioTestCase, mock

from aiocronjob import State
from aiocronjob.logger import logger
from aiocronjob.manager import Manager


class TestManager(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.manager = Manager()
        self.manager_task = None

    async def asyncTearDown(self) -> None:
        await self.manager.shutdown()
        if self.manager_task:
            await self.manager_task

    async def test_register(self):
        async def task1():
            ...

        async def task2():
            ...

        self.manager.register(async_callable=task1, name="first task")
        self.manager.register(async_callable=task2, name="second task")

        self.assertEqual("first task", self.manager._jobs["first task"].definition.name)
        self.assertEqual("second task", self.manager._jobs["second task"].definition.name)

    async def test_register_duplicate_names_error(self):
        async def task():
            ...

        async def another_task():
            ...

        self.manager.register(async_callable=task, name="first task")

        with self.assertRaises(Exception) as ctx:
            self.manager.register(async_callable=another_task, name="first task")

        self.assertEqual(ctx.exception.__str__(), "Job <first task> already exists.")

    async def test_run_twice_warning(self):
        async def long_lasting_task():
            await asyncio.sleep(3)

        self.manager.register(long_lasting_task, name="long-lasting-task")

        t1 = asyncio.create_task(self.manager.run())

        await asyncio.sleep(0.01)

        with self.assertLogs(logger, "WARNING") as l:
            await self.manager.run()
            self.assertIn(
                "WARNING:aiocronjob:Ignoring current calling of run(). Already running.",
                l.output,
            )

    async def test_get_state(self):
        async def task():
            await asyncio.sleep(1)

        self.manager.register(task)

        state = self.manager.state()

        self.assertEqual(
            {
                "created_at": mock.ANY,
                "jobs_info": [{
                    "created_at": None,
                    "definition": {
                        "crontab": None,
                        "enabled": True,
                        "name": "task",
                    },
                    "last_finish": None,
                    "last_finish_status": None,
                    "last_start": None,
                    "last_status": None,
                    "next_start": None,
                    "status": "registered",
                }],
            },
            state.dict(),
        )

    async def test_set_initial_state(self):
        async def task():
            await asyncio.sleep(1)

        self.manager.register(task)

        past_date = datetime.datetime(year=2020, month=12, day=31, hour=23)

        initial_state = State(
            created_at=datetime.datetime.now(),
            jobs_info=[
                {
                    "definition": {"name": "task"},
                    "status": "running",
                    "last_status": "failed",
                    "last_finish": past_date,
                },
                {
                    "definition": {"name": "doesnotexist"},
                }
            ],
        )

        self.manager.set_initial_state(initial_state)

        self.manager_task = asyncio.create_task(self.manager.run())

        await asyncio.sleep(0)

        self.assertEqual("running", self.manager.get_job_info("task").status)
        self.assertEqual("failed", self.manager.get_job_info("task").last_status)
        self.assertEqual(past_date, self.manager.get_job_info("task").last_finish)

    async def test_task_exception(self):
        async def task():
            await asyncio.sleep(1)
            raise ValueError("err")

        self.manager_task = asyncio.create_task(self.manager.run())

        self.manager.register(task)
        # each cycle lasts 1.5 secs, so the task stays as 'registered' max 1.5 secs
        self.assertEqual("registered", self.manager.get_job_info("task").status)

        await asyncio.sleep(3)
        self.assertEqual("failed", self.manager.get_job_info("task").status)
