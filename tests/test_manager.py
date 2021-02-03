import asyncio

from aiocronjob.logger import logger
from aiocronjob.manager import Manager

from .common import IsolatedAsyncioTestCase


class TestCase(IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not hasattr(cls, "loop"):
            policy = asyncio.get_event_loop_policy()
            res = policy.new_event_loop()
            asyncio.set_event_loop(res)
            res._close = res.close
            res.close = lambda: None
            cls.loop = res

    @classmethod
    def tearDownClass(cls) -> None:
        cls.loop._close()

    def setUp(self) -> None:
        async def task1():
            ...

        async def task2():
            ...

        Manager.register(async_callable=task1, name="first task")
        Manager.register(async_callable=task2, name="second task")

    def tearDown(self) -> None:
        self.get_event_loop().run_until_complete(Manager.shutdown())
        Manager.clear()

    def get_event_loop(self):
        self.__class__.setUpClass()
        return self.__class__.loop

    async def test_register(self):
        self.assertEqual("first task", Manager._definitions["first task"].name)
        self.assertEqual("second task", Manager._definitions["second task"].name)

    async def test_register_duplicate_names_error(self):
        async def task():
            ...

        with self.assertRaises(Exception) as ctx:
            Manager.register(async_callable=task, name="first task")

        self.assertEqual(ctx.exception.__str__(), "Job <first task> already exists.")

    async def test_run_twice_warning(self):
        async def long_lasting_task():
            await asyncio.sleep(3)

        Manager.register(long_lasting_task, name="long-lasting-task")

        t1 = asyncio.get_event_loop().create_task(Manager.run())

        await asyncio.sleep(0.01)

        with self.assertLogs(logger, "WARNING") as l:
            await Manager.run()
            self.assertIn(
                "WARNING:aiocronjob:Ignoring current calling of run(). Already running.",
                l.output,
            )

        await Manager.shutdown()
        await asyncio.gather(t1)

    async def test_state(self):
        state = Manager.state()

        self.assertEqual(2, len(state.jobs_info))

        self.assertEqual("registered", state.jobs_info[0].last_status)
