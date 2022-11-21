import asyncio

from aiocronjob import Manager


async def first_task():
    for i in range(20):
        print("first task log", i)
        await asyncio.sleep(1)


async def second_task():
    for i in range(10):
        await asyncio.sleep(1.5)
        print("second task log", i)
    raise Exception("second task exception")


class CustomManager(Manager):
    async def on_startup(self):
        print("The app started.")

    async def on_shutdown(self):
        print("The app stopped.")

    async def on_job_exception(self, job_name: str, exception: BaseException):
        print(f"An exception occurred for job {job_name}: {exception}")

    async def on_job_cancelled(self, job_name: str):
        print(f"{job_name} was cancelled...")


manager = CustomManager()

manager.register(async_callable=first_task, crontab="* * * * *")
manager.register(async_callable=second_task, crontab="* * * * *")

manager.set_default()
