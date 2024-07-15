import time
import uuid
from importlib.metadata import version
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from gen3datalibrary import config, logging
from gen3datalibrary.auth import (
    authorize_request,
    get_user_id,
    raise_if_user_exceeded_limits,
)
from gen3datalibrary.db import DataAccessLayer, get_data_access_layer

root_router = APIRouter()


# CREATE & UPDATE Body for /lists
# ------------------------------------

# {
#   "lists": [
#   {
#     "name": "My Saved List 1",
#     "items": {
#       "drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a64": {
#         "dataset_guid": "phs000001.v1.p1.c1",
#             },
#       "CF_1": {
#        "name": "Cohort Filter 1",
#        "type": "Gen3GraphQL",
#         "schema_version": "c246d0f",
#         "data": { "query": """query ($filter: JSON) { _aggregation { subject (filter: $filter) { file_count { histogram { sum } } } } }""", "variables": { "filter": { "AND": [ {"IN": {"annotated_sex": ["male"]}}, {"IN": {"data_type": ["Aligned Reads"]}}, {"IN": {"data_format": ["CRAM"]}}, {"IN": {"race": ["[\"hispanic\"]"]}} ] } } }
#             }
#     }
#   },
#       { ... }
#   ]
# }


@root_router.post(
    "/lists/",
    dependencies=[
        Depends(raise_if_user_exceeded_limits),
    ],
)
@root_router.post(
    "/lists",
    include_in_schema=False,
    dependencies=[
        Depends(raise_if_user_exceeded_limits),
    ],
)
async def create_list(
    request: Request,
    data: dict,
    data_access_layer: DataAccessLayer = Depends(get_data_access_layer),
) -> dict:
    """
    Create a new list with the provided items

    Args:
        request (Request): FastAPI request (so we can check authorization)
        data (dict): Body from the POST
        data_access_layer (DataAccessLayer): Interface for data manipulations
    """
    user_id = await get_user_id(request=request)

    # TODO dynamically create user policy

    await authorize_request(
        request=request,
        authz_access_method="create",
        authz_resources=[f"/users/{user_id}/user-library/"],
    )

    lists = data.get("lists")

    if not lists:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="no lists provided"
        )

    start_time = time.time()

    # TODO do stuff
    await data_access_layer.create_user_lists(user_lists=lists)

    response = {"response": "asdf"}

    end_time = time.time()
    logging.info(
        "Gen3 Data Library Response. "
        f"lists={lists}, response={response['response']}, response_time_seconds={end_time - start_time} user_id={user_id}"
    )
    logging.debug(response)

    return response


@root_router.get(
    "/lists/",
    dependencies=[
        Depends(raise_if_user_exceeded_limits),
    ],
)
@root_router.get(
    "/lists",
    include_in_schema=False,
    dependencies=[
        Depends(raise_if_user_exceeded_limits),
    ],
)
async def read_all_lists(
    request: Request,
    data: dict,
) -> dict:
    """
    Create a new list with the provided items

    Args:
        request (Request): FastAPI request (so we can check authorization)
        data (dict): Body from the POST
    """
    user_id = await get_user_id(request=request)

    # dynamically create user policy

    await authorize_request(
        request=request,
        authz_access_method="create",
        authz_resources=[f"/users/{user_id}/user-library/"],
    )


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

    service_version = version("gen3datalibrary")

    return {"version": service_version}


@root_router.get("/_status/")
@root_router.get("/_status", include_in_schema=False)
async def get_status(request: Request) -> dict:
    """
    Return the status of the running service

    Args:
        request (Request): FastAPI request (so we can check authorization)

    Returns:
        dict: simple status and timestamp in format: `{"status": "OK", "timestamp": time.time()}`
    """
    await authorize_request(
        request=request,
        authz_access_method="read",
        authz_resources=["/gen3_data_library/service_info/status"],
    )
    return {"status": "OK", "timestamp": time.time()}
