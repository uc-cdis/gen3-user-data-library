import logging
import time
from importlib.metadata import version

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from starlette import status
from starlette.responses import JSONResponse

from gen3userdatalibrary.db import DataAccessLayer, get_data_access_layer

basic_router = APIRouter()


@basic_router.get(
    "/",
    description="Directs client to the docs",
    summary="Get swagger docs",
)
async def redirect_to_docs():
    """
    Redirects to the API docs if they hit the base endpoint.
    """
    return RedirectResponse(url="/docs")


@basic_router.get(
    "/_version/",
    status_code=status.HTTP_200_OK,
    description="Gets the current version of the service",
    summary="Get current version",
    responses={
        status.HTTP_200_OK: {
            "description": "No content",
        },
    },
)
@basic_router.get("/_version", include_in_schema=False, dependencies=[])
async def get_version(request: Request) -> dict:
    """
    Return the version of the running service

    Returns:
        dict: {"version": "1.0.0"} the version
    """
    service_version = version("gen3userdatalibrary")
    return {"version": service_version}


@basic_router.get(
    "/_status/",
    dependencies=[],
    description="Gets the current status of the service",
    summary="Get service status",
    responses={
        status.HTTP_200_OK: {
            "description": "No content",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "No content",
        },
    },
)
@basic_router.get("/_status", include_in_schema=False, dependencies=[])
async def get_status(
    request: Request,
    data_access_layer: DataAccessLayer = Depends(get_data_access_layer),
) -> JSONResponse:
    """
    Return the status of the running service

    Args:
         request (Request): FastAPI request (so we can check authorization)
         data_access_layer (DataAccessLayer): how we interface with db

    Returns:
        JSONResponse: simple status and timestamp in format: `{"status": "OK", "timestamp": time.time()}`
    """
    return_status = status.HTTP_201_CREATED
    status_text = "OK"

    try:
        await data_access_layer.test_connection()
    except Exception as e:
        logging.error(e)
        return_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        status_text = "UNHEALTHY"

    response = {"status": status_text, "timestamp": time.time()}

    return JSONResponse(status_code=return_status, content=response)
