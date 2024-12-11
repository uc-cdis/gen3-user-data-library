import time
from contextlib import asynccontextmanager
from importlib.metadata import version

import fastapi
from cdislogging import get_logger
from fastapi import FastAPI, HTTPException
from gen3authz.client.arborist.client import ArboristClient
from prometheus_client import CollectorRegistry, make_asgi_app, multiprocess
from starlette.requests import Request
from starlette.responses import JSONResponse

from gen3userdatalibrary import config, logging
from gen3userdatalibrary.auth import get_user_id
from gen3userdatalibrary.db import get_data_access_layer
from gen3userdatalibrary.metrics import Metrics
from gen3userdatalibrary.routes import route_aggregator
from gen3userdatalibrary.utils.core import log_user_data_library_api_call


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Parse the configuration, setup and instantiate necessary classes.

    This is FastAPI's way of dealing with startup logic before the app
    starts receiving requests.

    https://fastapi.tiangolo.com/advanced/events/#lifespan

    Args:
        app (fastapi.FastAPI): The FastAPI app object
    """
    # startup
    app.state.metrics = Metrics(
        enabled=config.ENABLE_PROMETHEUS_METRICS,
        prometheus_dir=config.PROMETHEUS_MULTIPROC_DIR,
    )

    app.state.arborist_client = ArboristClient(
        arborist_base_url=config.ARBORIST_URL,
        logger=get_logger("user_syncer.arborist_client"),
        authz_provider="user-sync",
    )

    try:
        logging.debug(
            "Startup database connection test initiating. Attempting a simple query..."
        )
        dals = get_data_access_layer()
        async for data_access_layer in dals:
            await data_access_layer.test_connection()
            logging.debug("Startup database connection test PASSED.")
    except Exception as exc:
        logging.exception(
            "Startup database connection test FAILED. Unable to connect to the configured database."
        )
        logging.debug(exc)
        raise

    if not config.DEBUG_SKIP_AUTH:
        try:
            logging.debug(
                "Startup policy engine (Arborist) connection test initiating..."
            )
            if not app.state.arborist_client.healthy():
                print("not healthy!")
                # raise Exception("Arborist unhealthy,aborting...")
        except Exception as exc:
            logging.exception(
                "Startup policy engine (Arborist) connection test FAILED. Unable to connect to the policy engine."
            )
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

    fastapi_app = FastAPI(
        title="Gen3 User Data Library Service",
        version=version("gen3userdatalibrary"),
        debug=config.DEBUG,
        root_path=config.URL_PREFIX,
        lifespan=lifespan,
    )
    fastapi_app.include_router(route_aggregator)

    # set up the prometheus metrics
    if config.ENABLE_PROMETHEUS_METRICS:
        metrics_app = make_metrics_app(config.PROMETHEUS_MULTIPROC_DIR)
        fastapi_app.mount("/metrics", metrics_app)

    @fastapi_app.middleware("http")
    async def middleware_log_response_and_api_metric(request: Request, call_next):
        """
        This FastAPI middleware effectively allows pre and post logic to a request.

        We are using this to log the response consistently across defined endpoints (including execution time).

        Args:
            request (Request): the incoming HTTP request
            call_next (Callable): function to call (this is handled by FastAPI's middleware support)
        """
        start_time = time.perf_counter()
        response = await call_next(request)
        response_time_seconds = time.perf_counter() - start_time

        path = request.url.path
        method = request.method
        if path in config.ENDPOINTS_WITHOUT_METRICS:
            return response
        # don't add logs or metrics for the actual metrics gathering endpoint
        try:
            user_id = await get_user_id(request=request)
        except HTTPException as e:
            return JSONResponse(status_code=e.status_code, content=e.detail)
        response_body = getattr(response, "body", None)
        log_user_data_library_api_call(
            logging=logging,
            debug_log=(
                f"Response body: {getattr(response, 'body', None)}"
                if response_body
                else None
            ),
            method=method,
            path=path,
            status_code=response.status_code,
            response_time_seconds=response_time_seconds,
            user_id=user_id,
        )

        if not getattr(fastapi_app.state, "metrics", None):
            return
        metrics = fastapi_app.state.metrics
        metrics.add_user_list_api_interaction(
            method=method,
            path=path,
            user_id=user_id,
            response_time_seconds=response_time_seconds,
            status_code=response.status_code,
        )

        return response

    return fastapi_app


def make_metrics_app(prometheus_multiproc_dir):
    """
    Required for Prometheus multiprocess setup
    See: https://prometheus.github.io/client_python/multiprocess/
    """
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry, prometheus_multiproc_dir)
    return make_asgi_app(registry=registry)


app = get_app()
