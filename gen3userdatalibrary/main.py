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
from gen3userdatalibrary.db import get_data_access_layer


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
    fastapi_app.state.metrics = Metrics(
        enabled=config.ENABLE_PROMETHEUS_METRICS,
        prometheus_dir=config.PROMETHEUS_MULTIPROC_DIR,
    )

    try:
        logging.debug(
            "Startup database connection test initiating. Attempting a simple query..."
        )
        async for data_access_layer in get_data_access_layer():
            await data_access_layer.test_connection()
            logging.debug("Startup database connection test PASSED.")
    except Exception as exc:
        logging.exception(
            "Startup database connection test FAILED. Unable to connect to the configured database."
        )
        logging.debug(exc)
        raise

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

    # set up the prometheus metrics
    if config.ENABLE_PROMETHEUS_METRICS:
        metrics_app = make_metrics_app()
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


app = get_app()
