# aiocronjob

[![Join the chat at https://gitter.im/aiocronjob/community](https://badges.gitter.im/aiocronjob/community.svg)](https://gitter.im/aiocronjob/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/aiocronjob?style=flat-square)
![PyPI](https://img.shields.io/pypi/v/aiocronjob?style=flat-square)
![PyPI - License](https://img.shields.io/pypi/l/aiocronjob?style=flat-square)
![GitHub last commit](https://img.shields.io/github/last-commit/devtud/aiocronjob?style=flat-square)
![PyPI - Status](https://img.shields.io/pypi/status/aiocronjob?style=flat-square)

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

![screenshot-actionmenu](https://raw.githubusercontent.com/devtud/aiocronjob/master/examples/screenshot-actionmenu.webp)
![screenshot-all](https://raw.githubusercontent.com/devtud/aiocronjob/master/examples/screenshot-all.webp)

#### Rest API

Open [localhost:5000/docs](http://localhost:5000/docs) for endpoints docs.

![EndpointsScreenshot](https://raw.githubusercontent.com/devtud/aiocronjob/master/examples/screenshot-endpoints.webp)

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

### Development

**Requirements**:
- **Python** >= 3.6 and **Poetry** for backend
- **npm** for frontend

The frontend is a separate Single Page Application (SPA), so the backend does not depend on it. It just calls the backend's API endpoints.

#### Install backend dependencies (Python)

```bash
$ git clone https://github.com/devtud/aiocronjob.git

$ cd aiocronjob

$ poetry install
```

#### Run backend tests

```bash
poetry run pytest --cov -s
```

#### Run backend example

```bash
poetry run python examples/simple_tasks.py
```

`uvicorn` will run the `FastAPI` app at http://localhost:5000.

#### Install frontend dependencies (React SPA)

Open another terminal tab in the project root.

```bash
$ cd src/webapp

$ npm i
```

#### Run frontend tests

```bash
npm test
```

#### Let frontend know about backend

Create `.env` file with the content from `.env.example` file to let the frontend know that the backend is running at http://localhost:5000.

```bash
cp .env.example .env
```

#### Serve frontend

```bash
npm start
```

A `React` app starts at http://localhost:3000.

You should now be able to view the example jobs in your browser at http://localhost:3000.
