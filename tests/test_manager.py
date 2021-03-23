import asyncio

from aiocronjob.logger import logger
from aiocronjob.manager import Manager

from .common import IsolatedAsyncioTestCase


class TestManager(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        async def task1():
            ...

        async def task2():
            ...

        self.manager = Manager()

        self.manager.register(
            async_callable=task1,
            name="first task",
        )
        self.manager.register(
            async_callable=task2,
            name="second task",
        )

    def tearDown(self) -> None:
        self.get_event_loop().run_until_complete(self.manager.shutdown())

    async def test_register(self):
        self.assertEqual(
            "first task",
            self.manager._definitions["first task"].name,
        )
        self.assertEqual(
            "second task",
            self.manager._definitions["second task"].name,
        )

    async def test_register_duplicate_names_error(self):
        async def task():
            ...

        with self.assertRaises(Exception) as ctx:
            self.manager.register(async_callable=task, name="first task")

        self.assertEqual(
            ctx.exception.__str__(),
            "Job <first task> already exists.",
        )

    async def test_run_twice_warning(self):
        async def long_lasting_task():
            await asyncio.sleep(3)

        self.manager.register(long_lasting_task, name="long-lasting-task")

        t1 = asyncio.get_event_loop().create_task(self.manager.run())

        await asyncio.sleep(0.01)

        with self.assertLogs(logger, "WARNING") as l:
            await self.manager.run()
            self.assertIn(
                "WARNING:aiocronjob:Ignoring current calling of run(). Already running.",
                l.output,
            )

        await self.manager.shutdown()
        await asyncio.gather(t1)

    async def test_state(self):
        state = self.manager.state()

        self.assertEqual(2, len(state.jobs_info))

        self.assertEqual("registered", state.jobs_info[0].last_status)
