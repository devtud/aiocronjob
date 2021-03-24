try:
    from unittest.async_case import IsolatedAsyncioTestCase
except ImportError:
    from aiounittest.case import AsyncTestCase as IsolatedAsyncioTestCase
