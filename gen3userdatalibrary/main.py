from contextlib import asynccontextmanager
from importlib.metadata import version

import fastapi
from fastapi import FastAPI
from gen3authz.client.arborist.client import ArboristClient
from prometheus_client import CollectorRegistry, make_asgi_app, multiprocess
from starlette.requests import Request

from gen3userdatalibrary import config, logging
from gen3userdatalibrary.models.metrics import Metrics
from gen3userdatalibrary.routes import route_aggregator
from gen3userdatalibrary.services.db import get_data_access_layer


@asynccontextmanager
async def lifespan(app: Request):
    """
    Parse the configuration, setup and instantiate necessary classes.

    This is FastAPI's way of dealing with startup logic before the app
    starts receiving requests.

    https://fastapi.tiangolo.com/advanced/events/#lifespan

    Args:
        app (fastapi.FastAPI): The FastAPI app object
    """
    # startup
    app.state.metrics = Metrics(enabled=config.ENABLE_PROMETHEUS_METRICS,
                                prometheus_dir=config.PROMETHEUS_MULTIPROC_DIR)

    app.state.arborist_client = ArboristClient(arborist_base_url=config.ARBORIST_URL)

    try:
        logging.debug("Startup database connection test initiating. Attempting a simple query...")
        dals = get_data_access_layer()
        async for data_access_layer in dals:
            await data_access_layer.test_connection()
            logging.debug("Startup database connection test PASSED.")
    except Exception as exc:
        logging.exception("Startup database connection test FAILED. Unable to connect to the configured database.")
        logging.debug(exc)
        raise

    if not config.DEBUG_SKIP_AUTH:
        try:
            logging.debug("Startup policy engine (Arborist) connection test initiating...")
            assert app.state.arborist_client.healthy()
        except Exception as exc:
            logging.exception(
                "Startup policy engine (Arborist) connection test FAILED. Unable to connect to the policy engine.")
            logging.debug(exc)
            raise

    yield

    # teardown

    # NOTE: multiprocess.mark_process_dead is called by the gunicorn "child_exit" function for each worker  #
    # "child_exit" is defined in the gunicorn.conf.py


def get_app() -> fastapi.FastAPI:
    """
    Return the web framework app object after adding routes

    Returns:
        fastapi.FastAPI: The FastAPI app object
    """

    fastapi_app = FastAPI(title="Gen3 User Data Library Service", version=version("gen3userdatalibrary"),
                          debug=config.DEBUG, root_path=config.URL_PREFIX, lifespan=lifespan, )
    fastapi_app.include_router(route_aggregator)
    # This line can be added to add a middleman check on all endpoints
    # fastapi_app.middleware("http")(middleware_catcher)

    # set up the prometheus metrics
    logging.info(f"Prometheus metrics enabled: {config.ENABLE_PROMETHEUS_METRICS}")
    logging.info(f"{config.ENABLE_PROMETHEUS_METRICS == False}")
    if config.ENABLE_PROMETHEUS_METRICS:
        logging.info(f"Setting up prometheus...")
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
