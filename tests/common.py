import asyncio


try:
    from unittest.async_case import IsolatedAsyncioTestCase
except ImportError:
    from aiounittest.case import AsyncTestCase
    from aiounittest import async_test

    class IsolatedAsyncioTestCase(AsyncTestCase):
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

        def get_event_loop(self):
            self.__class__.setUpClass()
            return self.__class__.loop
