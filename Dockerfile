ARG AZLINUX_BASE_VERSION=master
# Base stage with python-build-base
FROM quay.io/cdis/python-nginx-al:${AZLINUX_BASE_VERSION} AS base

ENV appname=gen3userdatalibrary
COPY --chown=gen3:gen3 . /${appname}
WORKDIR /$appname

FROM base AS builder

USER gen3


# copy ONLY poetry artifact, install the dependencies but not gen3userdatalibrary
# this will make sure that the dependencies are cached
COPY poetry.lock pyproject.toml /$appname/
RUN poetry config virtualenvs.in-project true \
    && poetry install -vv --no-root --only main --no-interaction \
    && poetry show -v

# copy source code ONLY after installing dependencies
COPY --chown=gen3:gen3 . /${appname}

# install gen3userdatalibrary
RUN poetry config virtualenvs.in-project true \
    && poetry install -vv --only main --no-interaction \
    && poetry show -v

# Creating the runtime image
FROM base

COPY --from=builder --chown=appuser:appuser /$appname /$appname

USER gen3

CMD ["poetry", "run", "gunicorn", "gen3userdatalibrary.main:app", "-k", "uvicorn.workers.UvicornWorker", "-c", "gunicorn.conf.py", "--user", "gen3", "--group", "gen3"]
