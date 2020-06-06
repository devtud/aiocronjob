import asyncio

from aiocronjob import manager, Job
from aiocronjob import run_app


async def first_task():
    for i in range(20):
        print("first task log", i)
        await asyncio.sleep(1)


async def second_task():
    for i in range(10):
        await asyncio.sleep(1.5)
        print("second task log", i)
    raise Exception("second task exception")


manager.register(async_callable=first_task, crontab="22 * * * *")

manager.register(async_callable=second_task, crontab="23 * * * *")


async def on_job_exception(job: Job, exc: BaseException):
    print(f"An exception occurred for job {job.name}: {exc}")


async def on_job_cancelled(job: Job):
    print(f"{job.name} was cancelled...")


async def on_startup():
    print("The app started.")


async def on_shutdown():
    print("The app stopped.")


manager.set_on_job_cancelled_callback(on_job_cancelled)
manager.set_on_job_exception_callback(on_job_exception)
manager.set_on_shutdown_callback(on_shutdown)
manager.set_on_startup_callback(on_startup)

if __name__ == "__main__":
    run_app()
