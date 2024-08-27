import time
from datetime import datetime
from importlib.metadata import version
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from gen3authz.client.arborist.errors import ArboristError
from jsonschema.exceptions import ValidationError
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from starlette import status

from gen3userdatalibrary import config, logging
from gen3userdatalibrary.auth import authorize_request, get_user_id
from gen3userdatalibrary.db import DataAccessLayer, get_data_access_layer
from gen3userdatalibrary.utils import add_user_list_metric

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
#         "data": { "query": """query ($filter: JSON) { _aggregation { subject (filter: $filter)
#         { file_count { histogram { sum } } } } }""", "variables": { "filter": { "AND": [ {"IN":
#         {"annotated_sex": ["male"]}}, {"IN": {"data_type": ["Aligned Reads"]}}, {"IN":
#         {"data_format": ["CRAM"]}}, {"IN": {"race": ["[\"hispanic\"]"]}} ] } } }
#             }
#     }
#   },
#       { ... }
#   ]
# }


class UserListModel(BaseModel):
    version: int
    creator: str
    authz: Dict[str, Any]
    name: str
    created_time: datetime
    updated_time: datetime
    items: Optional[Dict[str, Any]] = None


class UserListResponseModel(BaseModel):
    lists: Dict[int, UserListModel]


@root_router.post(
    "/lists/",
    # most of the following stuff helps populate the openapi docs
    response_model=UserListResponseModel,
    status_code=status.HTTP_201_CREATED,
    description="Create user list(s) by providing valid list information",
    tags=["User Lists"],
    summary="Create user lists(s)",
    responses={
        status.HTTP_201_CREATED: {
            "model": UserListResponseModel,
            "description": "Creates something from user request ",
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Bad request, unable to create list",
        },
    },
)
@root_router.post(
    "/lists",
    include_in_schema=False,
)
async def create_user_list(
    request: Request,
    data: dict,
    data_access_layer: DataAccessLayer = Depends(get_data_access_layer),
) -> JSONResponse:
    """
    Create a new list with the provided items

    Args:
        request (Request): FastAPI request (so we can check authorization)
        data (dict): Body from the POST
        data_access_layer (DataAccessLayer): Interface for data manipulations
    """
    user_id = await get_user_id(request=request)

    # TODO dynamically create user policy, ROUGH UNTESTED VERSION: need to verify
    if not config.DEBUG_SKIP_AUTH:
        # make sure the user exists in Arborist
        # IMPORTANT: This is using the user's unique subject ID
        request.app.state.arborist_client.create_user_if_not_exist(user_id)

        resource = f"/users/{user_id}/user-data-library"

        try:
            logging.debug("attempting to update arborist resource: {}".format(resource))
            request.app.state.arborist_client.update_resource("/", resource, merge=True)
        except ArboristError as e:
            logging.error(e)
            # keep going; maybe just some conflicts from things existing already
            # TODO: Unsure if this is safe, we might need to actually error here?

    await authorize_request(
        request=request,
        authz_access_method="create",
        authz_resources=[f"/users/{user_id}/user-data-library/"],
    )

    lists = data.get("lists")

    if not lists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="no lists provided"
        )

    start_time = time.time()

    try:
        new_user_lists = await data_access_layer.create_user_lists(user_lists=lists)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="must provide a unique name"
        )
    except ValidationError as exc:
        logging.debug(
            f"Invalid user-provided data when trying to create lists for user {user_id}."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid list information provided",
        )
    except Exception as exc:
        logging.exception(
            f"Unknown exception {type(exc)} when trying to create lists for user {user_id}."
        )
        logging.debug(f"Details: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid list information provided",
        )

    response_user_lists = {}
    for _, user_list in new_user_lists.items():
        response_user_lists[user_list.id] = user_list.to_dict()
        del response_user_lists[user_list.id]["id"]

    response = {"lists": response_user_lists}

    end_time = time.time()

    action = "CREATE"
    response_time_seconds = end_time - start_time
    logging.info(
        f"Gen3 User Data Library Response. Action: {action}. "
        f"lists={lists}, response={response}, response_time_seconds={response_time_seconds} user_id={user_id}"
    )

    add_user_list_metric(
        fastapi_app=request.app,
        action=action,
        user_lists=lists,
        response_time_seconds=response_time_seconds,
        user_id=user_id,
    )

    logging.debug(response)

    return JSONResponse(status_code=status.HTTP_201_CREATED, content=response)


# TODO: add GET for specific list
# remember to check authz for /users/{{subject_id}}/user-data-library/lists/{{ID_0}}


@root_router.get(
    "/lists/",
)
@root_router.get(
    "/lists",
    include_in_schema=False,
)
async def read_all_lists(
    request: Request,
) -> dict:
    """
    Read

    Args:
        request (Request): FastAPI request (so we can check authorization)
    """
    user_id = await get_user_id(request=request)

    # dynamically create user policy

    await authorize_request(
        request=request,
        authz_access_method="read",
        authz_resources=[f"/users/{user_id}/user-data-library/"],
    )

    return {}


@root_router.put(
    "/lists/",
)
@root_router.put(
    "/lists",
    include_in_schema=False,
)
async def delete_all_lists(request: Request, data: dict) -> dict:
    """
    Update

    Args:
        request (Request): FastAPI request (so we can check authorization)
        data (dict): Body from the POST
    """
    user_id = await get_user_id(request=request)

    # dynamically create user policy

    await authorize_request(
        request=request,
        authz_access_method="delete",
        authz_resources=[f"/users/{user_id}/user-data-library/"],
    )

    return {}


@root_router.delete(
    "/lists/",
)
@root_router.delete(
    "/lists",
    include_in_schema=False,
)
async def delete_all_lists(
    request: Request,
) -> dict:
    """
    Delete all lists

    Args:
        request (Request): FastAPI request (so we can check authorization)
    """
    user_id = await get_user_id(request=request)

    # dynamically create user policy

    await authorize_request(
        request=request,
        authz_access_method="delete",
        authz_resources=[f"/users/{user_id}/user-data-library/"],
    )

    return {}


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
    data_access_layer: DataAccessLayer = Depends(get_data_access_layer),
) -> JSONResponse:
    """
    Return the status of the running service

    Args:
        request (Request): FastAPI request (so we can check authorization)

    Returns:
        JSONResponse: simple status and timestamp in format: `{"status": "OK", "timestamp": time.time()}`
    """
    await authorize_request(
        request=request,
        authz_access_method="read",
        authz_resources=["/gen3_data_library/service_info/status"],
    )

    return_status = status.HTTP_201_CREATED
    status_text = "OK"

    try:
        await data_access_layer.test_connection()
    except Exception:
        return_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        status_text = "UNHEALTHY"

    response = {"status": status_text, "timestamp": time.time()}

    return JSONResponse(status_code=return_status, content=response)
