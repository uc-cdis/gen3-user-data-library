import time
from importlib.metadata import version
from fastapi import APIRouter, Depends, Request
from starlette import status
from starlette.responses import JSONResponse
from gen3userdatalibrary.services.auth import authorize_request
from gen3userdatalibrary.services.db import DataAccessLayer, get_data_access_layer
from fastapi.responses import RedirectResponse

root_router = APIRouter()


@root_router.get("/", include_in_schema=False)
async def redirect_to_docs():
    """
    Redirects to the API docs if they hit the base endpoint.
    :return:
    """
    return RedirectResponse(url="/redoc")


@root_router.get("/_version/")
@root_router.get("/_version", include_in_schema=False)
async def get_version(request: Request) -> dict:
    """
    Return the version of the running service

    Args:
        request (Request): FastAPI request (so we can check authorization)

    Returns:
        dict: {"version": "1.0.0"} the version
    """
    await authorize_request(
        request=request,
        authz_access_method="read",
        authz_resources=["/gen3_data_library/service_info/version"],
    )

    service_version = version("gen3userdatalibrary")

    return {"version": service_version}


@root_router.get("/_status/")
@root_router.get("/_status", include_in_schema=False)
async def get_status(
        request: Request,
        data_access_layer: DataAccessLayer = Depends(get_data_access_layer)) -> JSONResponse:
    """
    Return the status of the running service

    Args:
        :param request: FastAPI request (so we can check authorization)
        :param data_access_layer: how we interface with db

    Returns:
        JSONResponse: simple status and timestamp in format: `{"status": "OK", "timestamp": time.time()}`
    """
    await authorize_request(
        request=request,
        authz_access_method="read",
        authz_resources=["/gen3_data_library/service_info/status"])

    return_status = status.HTTP_201_CREATED
    status_text = "OK"

    try:
        await data_access_layer.test_connection()
    except Exception as e:
        return_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        status_text = "UNHEALTHY"

    response = {"status": status_text, "timestamp": time.time()}

    return JSONResponse(status_code=return_status, content=response)
