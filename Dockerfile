FROM quay.io/cdis/amazonlinux:python3.9-master as build-deps

USER root

ENV appname=gen3datalibrary

RUN pip3 install --no-cache-dir --upgrade poetry

RUN yum update -y && yum install -y --setopt install_weak_deps=0 \
    kernel-devel libffi-devel libxml2-devel libxslt-devel postgresql-devel python3-devel \
    git && yum clean all

WORKDIR /$appname

# copy ONLY poetry artifact, install the dependencies but not gen3datalibrary
# this will make sure that the dependencies are cached
COPY poetry.lock pyproject.toml /$appname/
COPY ./docs/openapi.yaml /$appname/docs/openapi.yaml
RUN poetry config virtualenvs.in-project true \
    && poetry install -vv --no-root --only main --no-interaction \
    && poetry show -v

# copy source code ONLY after installing dependencies
COPY . /$appname

# install gen3datalibrary
RUN poetry config virtualenvs.in-project true \
    && poetry install -vv --only main --no-interaction \
    && poetry show -v

#Creating the runtime image
FROM quay.io/cdis/amazonlinux:python3.9-master

ENV appname=gen3datalibrary

USER root

RUN pip3 install --no-cache-dir --upgrade poetry

RUN yum update -y && yum install -y --setopt install_weak_deps=0 \
    postgresql-devel shadow-utils\
    bash && yum clean all

RUN useradd -ms /bin/bash appuser

COPY --from=build-deps --chown=appuser:appuser /$appname /$appname

WORKDIR /$appname

USER appuser

CMD ["poetry", "run", "gunicorn", "gen3datalibrary.main:app", "-k", "uvicorn.workers.UvicornWorker", "-c", "gunicorn.conf.py"]
