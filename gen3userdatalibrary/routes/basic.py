import time
from importlib.metadata import version

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from starlette import status
from starlette.responses import JSONResponse

from gen3userdatalibrary.db import DataAccessLayer, get_data_access_layer
from gen3userdatalibrary.routes.dependencies import parse_and_auth_request

basic_router = APIRouter()


@basic_router.get("/", include_in_schema=False)
async def redirect_to_docs():
    """
    Redirects to the API docs if they hit the base endpoint.
    """
    return RedirectResponse(url="/redoc")


@basic_router.get("/_version/", dependencies=[])
@basic_router.get("/_version", include_in_schema=False, dependencies=[])
async def get_version(request: Request) -> dict:
    """
    Return the version of the running service

    Returns:
        dict: {"version": "1.0.0"} the version
    """
    service_version = version("gen3userdatalibrary")
    return {"version": service_version}


@basic_router.get("/_status/", dependencies=[])
@basic_router.get("/_status", include_in_schema=False, dependencies=[])
async def get_status(
    request: Request,
    data_access_layer: DataAccessLayer = Depends(get_data_access_layer),
) -> JSONResponse:
    """
    Return the status of the running service

    Args:
        request: the data in request
        data_access_layer: how we interface with the db

    Returns:
        JSONResponse: simple status and timestamp in format: `{"status": "OK", "timestamp": time.time()}`
    """
    return_status = status.HTTP_201_CREATED
    status_text = "OK"

    try:
        await data_access_layer.test_connection()
    except Exception as e:
        return_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        status_text = "UNHEALTHY"

    response = {"status": status_text, "timestamp": time.time()}

    return JSONResponse(status_code=return_status, content=response)
