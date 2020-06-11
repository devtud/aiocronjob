# aiocronjob

Schedule and run `asyncio` coroutines and manage them from a web interface or programmatically using the rest api.

### Requires python >= 3.6

### How to install

```bash
pip3 install aiocronjob
```

### Usage example

```python
# examples/simple_tasks.py

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


manager.register(first_task, name="First task", crontab="22 * * * *")

manager.register(second_task, name="Second task", crontab="23 * * * *")


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
```

After running the app, the [FastAPI](https://fastapi.tiangolo.com) server runs at `localhost:5000`.

#### Web Interface

Open [localhost:5000](http://localhost:5000) in your browser:

![WEBUIScreenshot](https://raw.githubusercontent.com/devtud/aiocronjob/master/examples/simple_tasks-screenshot.png)

#### Rest API

Open [localhost:5000/docs](http://localhost:5000/docs) for endpoints docs.

![EndpointsScreenshot](https://raw.githubusercontent.com/devtud/aiocronjob/master/examples/simple_tasks-endpoints-screenshot.png)

**`curl`** example:
 
```bash
$ curl http://0.0.0.0:5000/api/jobs
```
```json
[
  {
    "name": "First task",
    "next_run_in": "3481.906931",
    "last_status": "pending",
    "enabled": "True",
    "crontab": "22 * * * *",
    "created_at": "2020-06-06T10:20:25.118630+00:00",
    "started_at": null,
    "stopped_at": null
  },
  {
    "name": "Second task",
    "next_run_in": "3541.904723",
    "last_status": "error",
    "enabled": "True",
    "crontab": "23 * * * *",
    "created_at": "2020-06-06T10:20:25.118661+00:00",
    "started_at": "2020-06-06T10:23:00.000906+00:00",
    "stopped_at": "2020-06-06T10:23:15.004351+00:00"
  }
]
```
