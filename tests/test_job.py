import asyncio

from aiocronjob.job import Job


def test_job_name():
    async def task():
        ...

    instance = Job(async_callable=task, crontab="1 * * * *", name="a job")

    assert instance.name == "a job"


def test_job_run(mocker):
    async def task():
        raise Exception()

    async def test():
        mock = mocker.patch("aiocronjob.job.CronTab")
        mock.return_value.next.return_value = 0

        job = Job(async_callable=task, name="task", crontab="1 * * * *")

        job.schedule()

        await asyncio.sleep(1)

        assert job.get_status() == "error"

    asyncio.run(test())


def test_job_status():
    async def task():
        await asyncio.sleep(1)

    async def helper():
        job = Job(async_callable=task, name="task")

        assert job.get_status() == "created"

        job.schedule(immediately=True)

        await asyncio.sleep(0.1)

        assert job.get_status() == "running"

        await asyncio.sleep(1)

        assert job.get_status() == "done"

    asyncio.run(helper())
