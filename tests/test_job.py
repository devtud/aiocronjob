import asyncio

from aiocronjob.job import Job


def test_job_name():
    async def some_job():
        ...

    instance = Job(async_callable=some_job, crontab="1 * * * *")

    assert instance.name == "Some job"

    another_instance = Job(
        async_callable=some_job, crontab="1 * * * *", name="Another job"
    )

    assert another_instance.name == "Another job"


def test_job_run(mocker):
    async def some_job():
        raise ValueError('xxx')

    async def test():
        mock = mocker.patch("aiocronjob.job.CronTab")
        mock.return_value.next.return_value = 0

        instance = Job(async_callable=some_job, crontab="1 * * * *")

        instance.run()

        await asyncio.sleep(1)

        assert instance.task.exception().__str__() == "xxx"

    asyncio.run(test())
