import asyncio
import datetime
import functools
import signal
from asyncio.events import AbstractEventLoop

import pytz


def now():
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)


def attach_loop_signal_handlers():
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    loop = asyncio.get_event_loop()

    def create_shutdown_task(signal):
        coro = shutdown(loop=loop, sig=signal)
        asyncio.create_task(coro)

    for s in signals:
        loop.add_signal_handler(s, functools.partial(create_shutdown_task, s))


async def shutdown(loop: AbstractEventLoop, sig):
    print(f"Received exit signal {sig.name}...")

    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    [task.cancel() for task in tasks if task.get_name()]

    print(f"Cancelling tasks: {[t.get_name() for t in tasks]}")

    _ = await asyncio.gather(*tasks, return_exceptions=True)

    loop.stop()

    print("Shutdown complete!")
