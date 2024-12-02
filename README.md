# Gen3 User Data Library

The user data library is a relatively
**Table of Contents**

- [Overview](#Overview)
- [Details](#Details)
- [Quickstart](#Quickstart)
- [Authz](#Authz)
- [Local Development](#local-dev)

## Overview

The Gen3 User Data Library service allows management of many user selections of data. It creates a "library" containing
all of a user's data selections.

Data selections are internally referred to as `lists`. A user can have 0 to many lists forming their library. A list has
unique items
that represent data in different forms. Lists can be stored, retrieved, modified, and deleted per user.

At the moment the lists support the following items:

- Global Alliance for Genomics and Health (GA4GH) Data Repository Service (DRS) Uniform Resource Identifiers (URIs)
- Gen3 GraphQL queries

## Details

[long description]

## Quickstart

### Setup

The api should nearly work out of the box. You will
need to install poetry dependencies, as well as set
up a `.env` file at the top level. The configuration
for this is described directly below. Once you have
a `.env` set up, running `run.sh` should boot up
an api you can access in your browser by going to
`localhost:8000` assuming you use the default ports.

#### Configuration

The configuration is done via a `.env` which allows environment variable overrides if you don't want to use the actual
file.

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

So it expects a `postgres` user with access to a `testgen3datalibrary` database; you will need to ensure both are
created and set up correctly.

The general app (by default) expects the same `postgres` user with access to `gen3datalibrary`.

> NOTE: The run.sh (and test.sh) scripts will attempt to create the database using the configured `DB_CONNECTION_STRING`
> if it doesn't exist.

The following script will migrate, setup env, and run the service locally:

```bash
./run.sh
```

Hit the API:

[insert example]

## Authz

[insert details]

## Local Dev

You can `bash ./run.sh` after install to run the app locally.

For testing, you can `bash ./test.sh`.

The default `pytest` options specified
in the `pyproject.toml` additionally:

* runs coverage and will error if it falls below the threshold

> TODO: Setup profiling. cProfile actually doesn't play well with async, so pytest-profiling won't work.
>       Perhaps use: https://github.com/joerick/pyinstrument ?

#### Automatically format code and run pylint

This quick `bash ./clean.sh` script is used to run `isort` and `black` over everything if
you don't integrate those with your editor/IDE.

> NOTE: This requires the beginning of the setup for using Super
> Linter locally. You must have the global linter configs in
> `~/.gen3/.github/.github/linters`.
> See [Gen3's linter setup docs](https://github.com/uc-cdis/.github/blob/master/.github/workflows/README.md#L1).

`clean.sh` also runs just `pylint` to check Python code for lint.

Here's how you can run it:

```bash
./clean.sh
```

> NOTE: GitHub's Super Linter runs more than just `pylint` so it's worth setting that up locally to run before pushing
> large changes.
> See [Gen3's linter setup docs](https://github.com/uc-cdis/.github/blob/master/.github/workflows/README.md#L1) for full
> instructions. Then you can run pylint more frequently as you develop.

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
-p 8089:8000 \
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

#### Debug in an IDE (such as PyCharm)

If you want to debug the running app in an IDE and the bash scripts
are not an easy option (I'm looking at you PyCharm), then
you can use `debug_run.py` in the root folder as an entrypoint.

> NOTE: There are some setup steps that the bash scripts do that you'll need to ensure
> are done. A key one is ensuring that the `PROMETHEUS_MULTIPROC_DIR` env var is set (default
> is `/var/tmp/prometheus_metrics`). And make sure the database exists and is migrated.

## Metrics

Metrics can be exposed at a `/metrics` endpoint compatible with Prometheus scraping and visualize in Prometheus or Graphana, etc.

The metrics are defined in `gen3userdatalibrary/metrics.py` and in 1.0.0 are as follows:

* **gen3_user_data_library_user_lists**: Gen3 User Data Library User Lists. Does not count the items WITHIN the list, just the lists themselves.
* **gen3_user_data_library_user_items**: Gen3 User Data Library User Items (within Lists). This counts the amount of items within lists, rather than the lists themselves.
* **gen3_user_data_library_api_requests_total**:  API requests for modifying Gen3 User Data Library User Lists. This includes all CRUD actions.

You can [run Prometheus locally](https://github.com/prometheus/prometheus) if you want to test or visualize these.

### tl;dr

Run the service locally using `poetry run bash run.sh`.

Create a [`prometheus.yml` config file](https://prometheus.io/docs/prometheus/latest/configuration/configuration), such as: `~/Documents/prometheus/conf/prometheus.yml`.

Put this in:

```yaml
global:
  scrape_interval:     15s # By default, scrape targets every 15 seconds.

# A scrape configuration containing exactly one endpoint to scrape:
# Here it's Prometheus itself.
scrape_configs:
  # The job name is added as a label `job=<job_name>` to any timeseries scraped from this config.
  - job_name: 'gen3_user_data_library'

    # Override the global default and scrape targets from this job every 5 seconds.
    scrape_interval: 5s

    static_configs:
      # NOTE: The `host.docker.internal` below is so docker on MacOS can properly find the locally running service
      - targets: ['host.docker.internal:8000']
```

> Note: Tested the above config on MacOS, with Linux you can maybe adjust these commands to actually expose the local
> network to the running prometheus container.

Then run this:

```
docker run --name prometheus -v ~/Documents/prometheus/conf/prometheus.yml:/etc/prometheus/prometheus.yml -d -p 127.0.0.1:9090:9090 prom/prometheus
```

Then go to [http://127.0.0.1:9090](http://127.0.0.1:9090).

And some recommended PromQL queries:

```promql
sum by (user_id) (gen3_user_data_library_user_lists)
```

```promql
sum by (user_id) (gen3_user_data_library_user_items)
```

```promql
sum by (status_code) (gen3_user_data_library_api_requests_total)
```
