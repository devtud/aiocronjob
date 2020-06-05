import pytest
from aiocronjob.job import JobName
from aiocronjob.manager import manager as manager_class


@pytest.fixture
def manager():
    manager_class._jobs.clear()
    return manager_class


def test_register(manager):
    async def task():
        ...

    manager.register(async_callable=task)
    manager.register(async_callable=task, name=JobName("task1-but-different-name"))

    assert 2 == len(manager._jobs)


def test_register_duplicate_names_error(manager):
    async def task():
        ...

    manager.register(async_callable=task, name=JobName("job"))
    with pytest.raises(Exception) as e:
        manager.register(async_callable=task, name=JobName("job"))
    assert str(e.value) == "Job job already exists."


def test_run_twice_error(manager):
    async def task():
        ...

    manager.register(async_callable=task)

    manager.run()

    with pytest.raises(Exception) as e:
        manager.run()

    assert str(e.value) == "Registered jobs were already scheduled."


def test_list_jobs(manager):
    async def task1():
        ...

    async def task2():
        ...

    manager.register(async_callable=task1)
    manager.register(async_callable=task2)
    jobs = manager.list_jobs()
    assert jobs[0].name == "Job_0-task1"
    assert jobs[0]._async_callable is task1
    assert jobs[1].name == "Job_1-task2"
    assert jobs[1]._async_callable is task2
