FROM quay.io/cdis/amazonlinux:python3.9-master AS build-deps

USER root

ENV appname=gen3userdatalibrary

RUN pip3 install --no-cache-dir --upgrade poetry

RUN yum update -y && yum install -y --setopt install_weak_deps=0 \
    kernel-devel libffi-devel libxml2-devel libxslt-devel postgresql-devel python3-devel \
    git && yum clean all

WORKDIR /$appname

# copy ONLY poetry artifact, install the dependencies but not gen3userdatalibrary
# this will make sure that the dependencies are cached
COPY poetry.lock pyproject.toml /$appname/
RUN poetry config virtualenvs.in-project true \
    && poetry install -vv --no-root --only main --no-interaction \
    && poetry show -v

# copy source code ONLY after installing dependencies
COPY . /$appname

# install gen3userdatalibrary
RUN poetry config virtualenvs.in-project true \
    && poetry install -vv --only main --no-interaction \
    && poetry show -v

# Creating the runtime image
FROM quay.io/cdis/amazonlinux:python3.9-master

ENV appname=gen3userdatalibrary

USER root

RUN pip3 install --no-cache-dir --upgrade poetry

RUN yum update -y && yum install -y --setopt install_weak_deps=0 \
    postgresql-devel shadow-utils\
    bash && yum clean all

RUN useradd -ms /bin/bash appuser

COPY --from=build-deps --chown=appuser:appuser /$appname /$appname

WORKDIR /$appname

USER appuser

CMD ["poetry", "run", "gunicorn", "gen3userdatalibrary.main:app", "-k", "uvicorn.workers.UvicornWorker", "-c", "gunicorn.conf.py", "--user", "appuser", "--group", "appuser"]
