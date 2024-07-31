import os
from importlib.metadata import version

from contextlib import asynccontextmanager
import fastapi
from fastapi import FastAPI, Request, Response
from prometheus_client import make_asgi_app, multiprocess
from prometheus_client import CollectorRegistry
import yaml

from gen3userdatalibrary import config, logging
from gen3userdatalibrary.routes import root_router
from gen3userdatalibrary.metrics import Metrics


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """
    Parse the configuration, setup and instantiate necessary classes.

    This is FastAPI's way of dealing with startup logic before the app
    starts receiving requests.

    https://fastapi.tiangolo.com/advanced/events/#lifespan

    Args:
        fastapi_app (fastapi.FastAPI): The FastAPI app object
    """
    # startup
    # TODO pass in config
    fastapi_app.state.metrics = Metrics(
        enabled=config.ENABLE_PROMETHEUS_METRICS, prometheus_dir=config.PROMETHEUS_MULTIPROC_DIR
    )

    yield

    # teardown

    # NOTE: multiprocess.mark_process_dead is called by the gunicorn "child_exit" function for each worker
    #       "child_exit" is defined in the gunicorn.conf.py


def get_app() -> fastapi.FastAPI:
    """
    Return the web framework app object after adding routes

    Returns:
        fastapi.FastAPI: The FastAPI app object
    """

    fastapi_app = FastAPI(
        title="Gen3 User Data Library Service",
        version=version("gen3userdatalibrary"),
        debug=config.DEBUG,
        root_path=config.URL_PREFIX,
        lifespan=lifespan,
    )
    fastapi_app.include_router(root_router)

    # this makes the docs at /doc and /redoc the same openapi docs in the docs folder
    # instead of the default behavior of generating openapi spec based from FastAPI
    fastapi_app.openapi = _override_generated_openapi_spec

    # set up the prometheus metrics
    if config.ENABLE_PROMETHEUS_METRICS:
        metrics_app = make_metrics_app()
        fastapi_app.metrics = Metrics()
        fastapi_app.mount("/metrics", metrics_app)

    return fastapi_app


def make_metrics_app():
    """
    Required for Prometheus multiprocess setup
    See: https://prometheus.github.io/client_python/multiprocess/
    """
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    return make_asgi_app(registry=registry)


def _override_generated_openapi_spec():
    json_data = None
    try:
        openapi_filepath = os.path.abspath("./docs/openapi.yaml")
        with open(openapi_filepath, "r", encoding="utf-8") as yaml_in:
            json_data = yaml.safe_load(yaml_in)
    except FileNotFoundError:
        logging.info(
            "could not find custom openapi spec at `docs/openapi.yaml`, using default generated one"
        )

    return json_data


app = get_app()
