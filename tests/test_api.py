import asyncio

from aiocronjob import app, manager
from starlette.testclient import TestClient

client = TestClient(app=app)


def test_list_jobs(mocker):
    some_datetime = "2020-06-06T08:39:14.065188+00:00"
    mock = mocker.patch("aiocronjob.job.now")
    mock.return_value = some_datetime

    async def task1():
        await asyncio.sleep(5)

    async def task2():
        await asyncio.sleep(5)

    manager.register(task1)
    manager.register(task2)

    response = client.get("/api/jobs")

    desired_output = [
        {
            "name": "Job_0-task1",
            "next_run_in": None,
            "last_status": "created",
            "enabled": "True",
            "crontab": "",
            "created_at": some_datetime,
            "started_at": None,
            "stopped_at": None,
        },
        {
            "name": "Job_1-task2",
            "next_run_in": None,
            "last_status": "created",
            "enabled": "True",
            "crontab": "",
            "created_at": some_datetime,
            "started_at": None,
            "stopped_at": None,
        },
    ]

    assert response.json() == desired_output
