import time
from importlib.metadata import version

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from starlette import status
from starlette.responses import JSONResponse

from gen3userdatalibrary.services.db import DataAccessLayer, get_data_access_layer
from gen3userdatalibrary.services.dependencies import parse_and_auth_request

basic_router = APIRouter()


@basic_router.get(
    "/", include_in_schema=False, dependencies=[Depends(parse_and_auth_request)]
)
async def redirect_to_docs():
    """
    Redirects to the API docs if they hit the base endpoint.
    """
    return RedirectResponse(url="/redoc")


@basic_router.get("/_version/", dependencies=[Depends(parse_and_auth_request)])
@basic_router.get(
    "/_version", include_in_schema=False, dependencies=[Depends(parse_and_auth_request)]
)
async def get_version(request: Request) -> dict:
    """
    Return the version of the running service

    Args:
        request (Request): FastAPI request (so we can check authorization)

    Returns:
        dict: {"version": "1.0.0"} the version
    """
    service_version = version("gen3userdatalibrary")
    return {"version": service_version}


@basic_router.get("/_status/", dependencies=[Depends(parse_and_auth_request)])
@basic_router.get(
    "/_status", include_in_schema=False, dependencies=[Depends(parse_and_auth_request)]
)
async def get_status(
    request: Request,
    data_access_layer: DataAccessLayer = Depends(get_data_access_layer),
) -> JSONResponse:
    """
    Return the status of the running service

    Args:
        :param request: FastAPI request (so we can check authorization)
        :param data_access_layer: how we interface with db

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
