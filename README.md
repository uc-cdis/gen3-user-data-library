# Gen3 User Data Library

[short description]

https://docs.google.com/document/d/15V4ukguiPA-05Yg3u4zXEg1_NsxcRz_kq-6AS8xPMZU/edit#heading=h.1xf8she1w5nv
https://towardsdatascience.com/build-an-async-python-service-with-fastapi-sqlalchemy-196d8792fa08


**Table of Contents**

- [auto gen this]


## Overview

[medium description]

## Details

[long description]

## Quickstart

### Setup

[]

#### Configuration

The configuration is done via a `.env` which allows environment variable overrides if you don't want to use the actual file.

Here's an example `.env` file you can copy and modify:

```.env
########## Secrets ##########

# make sure you have `postgresql+asyncpg` or you'll get errors about the default psycopg not supporting async
DB_CONNECTION_STRING="postgresql+asyncpg://postgres:postgres@localhost:5432/gen3userdatalibrary"

########## Configuration ##########

########## Debugging and Logging Configurations ##########

# DEBUG makes the logging go from INFO to DEBUG
DEBUG=False

# DEBUG_SKIP_AUTH will COMPLETELY SKIP AUTHORIZATION for debugging purposes
DEBUG_SKIP_AUTH=False
```

### Running locally

You need Postgres databases set up and you need to migrate them to the latest schema
using Alembic.

#### Setup DBs and Migrate

The test db config by default is:

```
DB_CONNECTION_STRING="postgresql+asyncpg://postgres:postgres@localhost:5432/testgen3datalibrary"
```

So it expects a `postgres` user with access to a `testgen3datalibrary` database.

The general app expects the same `postgres` user with access to `gen3datalibrary`.

> You must create the `testgen3datalibrary` and `gen3datalibrary` databases in Postgres yourself before attempting the migration.
> Once created, you need to `alembic migrate head` on both.

#### Run the Service

Install and run service locally:

```bash
poetry install
./run.sh
```

Hit the API:

[insert example]

> You can change the port in the `run.py` as needed

## Authz

[insert details]

## Local Dev

You can `bash run.sh` after install to run the app locally.

For testing, you can `bash test.sh`. 

The default `pytest` options specified 
in the `pyproject.toml` additionally:

* runs coverage and will error if it falls below the threshold
* profiles using [pytest-profiling](https://pypi.org/project/pytest-profiling/) which outputs into `/prof`

#### Automatically format code and run pylint

This quick `bash clean.sh` script is used to run `isort` and `black` over everything if 
you don't integrate those with your editor/IDE.

> NOTE: This requires the beginning of the setup for using Super 
> Linter locally. You must have the global linter configs in 
> `~/.gen3/.github/.github/linters`. See [Gen3's linter setup docs](https://github.com/uc-cdis/.github/blob/master/.github/workflows/README.md#L1).

`clean.sh` also runs just `pylint` to check Python code for lint.

Here's how you can run it:

```bash
./clean.sh
```

> NOTE: GitHub's Super Linter runs more than just `pylint` so it's worth setting that up locally to run before pushing large changes. See [Gen3's linter setup docs](https://github.com/uc-cdis/.github/blob/master/.github/workflows/README.md#L1) for full instructions. Then you can run pylint more frequently as you develop.

#### Testing Docker Build

To build:

```bash
docker build -t gen3userdatalibrary:latest .
```

To run:

```bash
docker run --name gen3userdatalibrary \
--env-file "./.env" \
-v "$SOME_OTHER_CONFIG":"$SOME_OTHER_CONFIG" \
-p 8089:8089 \
gen3userdatalibrary:latest
```

To exec into a bash shell in running container:

```bash
docker exec -it gen3userdatalibrary bash
```

To kill and remove running container:

```bash
docker kill gen3userdatalibrary
docker remove gen3userdatalibrary
```
