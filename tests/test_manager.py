import asyncio

from aiocronjob.logger import logger
from aiocronjob.manager import Manager

from .common import IsolatedAsyncioTestCase


class TestManager(IsolatedAsyncioTestCase):
    async def test_register(self):
        async def task1():
            ...

        async def task2():
            ...

        manager = Manager()

        manager.register(async_callable=task1, name="first task")
        manager.register(async_callable=task2, name="second task")

        self.assertEqual("first task", manager._definitions["first task"].name)
        self.assertEqual("second task", manager._definitions["second task"].name)

    async def test_register_duplicate_names_error(self):
        async def task():
            ...

        async def another_task():
            ...

        manager = Manager()

        manager.register(async_callable=task, name="first task")

        with self.assertRaises(Exception) as ctx:
            manager.register(async_callable=another_task, name="first task")

        self.assertEqual(ctx.exception.__str__(), "Job <first task> already exists.")

    async def test_run_twice_warning(self):
        async def long_lasting_task():
            await asyncio.sleep(3)

        manager = Manager()

        manager.register(long_lasting_task, name="long-lasting-task")

        t1 = asyncio.get_event_loop().create_task(manager.run())

        await asyncio.sleep(0.01)

        with self.assertLogs(logger, "WARNING") as l:
            await manager.run()
            self.assertIn(
                "WARNING:aiocronjob:Ignoring current calling of run(). Already running.",
                l.output,
            )

        await manager.shutdown()
        await asyncio.gather(t1)

    async def test_state(self):
        async def task1():
            ...

        async def task2():
            ...

        manager = Manager()

        manager.register(async_callable=task1, name="first task")
        manager.register(async_callable=task2, name="second task")

        state = manager.state()

        self.assertEqual(2, len(state.jobs_info))

        self.assertEqual("registered", state.jobs_info[0].last_status)
