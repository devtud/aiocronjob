# aiocronjob

[![Join the chat at https://gitter.im/aiocronjob/community](https://badges.gitter.im/aiocronjob/community.svg)](https://gitter.im/aiocronjob/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/aiocronjob?style=flat-square)
![PyPI](https://img.shields.io/pypi/v/aiocronjob?style=flat-square)
![PyPI - License](https://img.shields.io/pypi/l/aiocronjob?style=flat-square)
![GitHub last commit](https://img.shields.io/github/last-commit/devtud/aiocronjob?style=flat-square)
![PyPI - Status](https://img.shields.io/pypi/status/aiocronjob?style=flat-square)
[![Tests](https://github.com/devtud/aiocronjob/actions/workflows/tests.yml/badge.svg)](https://github.com/devtud/aiocronjob/actions/workflows/tests.yml)
[![Codecov](https://codecov.io/gh/devtud/aiocronjob/branch/main/graph/badge.svg)](https://codecov.io/gh/devtud/aiocronjob)

Schedule and run `asyncio` coroutines and manage them from a web interface or programmatically using the rest api.

### Requires python >= 3.8

### How to install

```bash
pip3 install aiocronjob
```

### Usage example

See [examples/simple_tasks.py](https://github.com/devtud/aiocronjob/blob/master/examples/simple_tasks.py)

#### Rest API

Open [localhost:8000/docs](http://localhost:8000/docs) for endpoints docs.

**`curl`** example:
 
```bash
$ curl http://0.0.0.0:8000/api/jobs
```
```json
TBD
```

### Development

**Requirements**:
- **Python** >= 3.8 and **PDM** for backend


#### Install dependencies

```bash
$ git clone https://github.com/devtud/aiocronjob.git

$ cd aiocronjob

$ pdm sync
```

#### Run tests

```bash
pdm run coverage run -m unittest discover

pdm run coverage report -m
```
