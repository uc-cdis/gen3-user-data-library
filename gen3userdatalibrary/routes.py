import time
from datetime import datetime
from functools import partial
from importlib.metadata import version
from typing import Any, Dict, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Request
from gen3authz.client.arborist.errors import ArboristError
from jsonschema.exceptions import ValidationError
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from starlette import status
from starlette.responses import JSONResponse

from gen3userdatalibrary import config, logging
from gen3userdatalibrary.auth import authorize_request, get_user_id, get_user_data_library_endpoint
from gen3userdatalibrary.db import DataAccessLayer, get_data_access_layer, create_user_list_instance
from gen3userdatalibrary.models import UserList
from gen3userdatalibrary.utils import add_user_list_metric
from fastapi.responses import RedirectResponse

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


@root_router.get("/", include_in_schema=False)
async def redirect_to_docs():
    """
    Redirects to the API docs if they hit the base endpoint.
    :return:
    """
    return RedirectResponse(url="/redoc")


async def try_creating_lists(data_access_layer, user_id, lists) -> Dict[int, UserList]:
    """
    Handler for modeling endpoint data into orm
    :param data_access_layer: an instance of our DAL
    :param lists: list of user lists to shape
    :param user_id: id of the list owner
    :return: dict that maps id -> user list
    """
    try:
        new_user_lists = await data_access_layer.create_user_lists(user_lists=lists)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="must provide a unique name")
    except ValidationError as exc:
        logging.debug(f"Invalid user-provided data when trying to create lists for user {user_id}.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid list information provided", )
    except Exception as exc:
        logging.exception(f"Unknown exception {type(exc)} when trying to create lists for user {user_id}.")
        logging.debug(f"Details: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid list information provided")
    return new_user_lists


@root_router.put(
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
        }})
@root_router.put(
    "/lists",
    include_in_schema=False)
async def upsert_user_lists(
        request: Request,
        data: dict,
        data_access_layer: DataAccessLayer = Depends(get_data_access_layer)) -> JSONResponse:
    """
    Create a new list with the provided items, or update any lists that already exist


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

        resource = get_user_data_library_endpoint(user_id["name"])

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
        authz_resources=[get_user_data_library_endpoint(user_id["name"])])
    lists = data.get("lists")
    if not lists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no lists provided")
    start_time = time.time()

    lists_as_orm = await try_creating_lists(data_access_layer, user_id, lists)
    lists_to_update = await data_access_layer.grab_all_lists_that_exist(list(lists_as_orm.keys()))
    set_of_existing_ids = set(map(lambda ul: ul.id, lists_to_update))
    lists_to_create = list(filter(lambda ul: ul.id not in set_of_existing_ids, list(lists_as_orm.values())))

    for list_to_update in lists_to_update:
        await data_access_layer.replace_list(list_to_update)
    for list_to_create in lists_to_create:
        await data_access_layer.persist_user_list(list_to_create, user_id)

    response_user_lists = {}
    for user_list in (lists_to_create + lists_to_update):
        response_user_lists[user_list.id] = user_list.to_dict()
        del response_user_lists[user_list.id]["id"]
    response = {"lists": response_user_lists}
    end_time = time.time()
    action = "CREATE"
    response_time_seconds = end_time - start_time
    logging.info(
        f"Gen3 User Data Library Response. Action: {action}. "
        f"lists={lists}, response={response}, response_time_seconds={response_time_seconds} user_id={user_id}")
    add_user_list_metric(
        fastapi_app=request.app,
        action=action,
        user_lists=lists,
        response_time_seconds=response_time_seconds,
        user_id=user_id)
    logging.debug(response)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=response)


# remember to check authz for /users/{{subject_id}}/user-data-library/lists/{{ID_0}}

@root_router.get("/lists/")
@root_router.get("/lists", include_in_schema=False, )
async def read_all_lists(
        request: Request,
        data_access_layer: DataAccessLayer = Depends(get_data_access_layer)) -> JSONResponse:
    """
    Return all lists for user

    Args:
        :param request: FastAPI request (so we can check authorization)
        :param data_access_layer: how we interface with db
    """
    user_id = await get_user_id(request=request)

    # dynamically create user policy
    await authorize_request(
        request=request,
        authz_access_method="read",
        authz_resources=[get_user_data_library_endpoint(user_id["name"])])
    start_time = time.time()

    try:
        new_user_lists = await data_access_layer.get_all_lists()
    except Exception as exc:
        logging.exception(f"Unknown exception {type(exc)} when trying to fetch lists.")
        logging.debug(f"Details: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid list information provided")
    response_user_lists = {}
    for user_list in new_user_lists:
        response_user_lists[user_list.id] = user_list.to_dict()
        del response_user_lists[user_list.id]["id"]
    response = {"lists": response_user_lists}
    end_time = time.time()
    action = "READ"
    response_time_seconds = end_time - start_time
    logging.info(
        f"Gen3 User Data Library Response. Action: {action}. "
        f"response={response}, response_time_seconds={response_time_seconds} user_id={user_id}")
    logging.debug(response)
    return JSONResponse(status_code=status.HTTP_200_OK, content=response)


@root_router.delete("/lists/")
@root_router.delete("/lists", include_in_schema=False)
async def delete_all_lists(request: Request,
                           data_access_layer: DataAccessLayer = Depends(get_data_access_layer)) -> JSONResponse:
    """
    Delete all lists for a provided user

    Args:
        :param request: FastAPI request (so we can check authorization)
        :param data_access_layer: how we interface with db
    """
    user_id = await get_user_id(request=request)

    # dynamically create user policy
    await authorize_request(
        request=request,
        authz_access_method="delete",
        authz_resources=[get_user_data_library_endpoint(user_id["name"])])

    start_time = time.time()
    user_id = "1"  # todo: derive correct user id from token

    try:
        number_of_lists_deleted = await data_access_layer.delete_all_lists(user_id)
    except Exception as exc:
        logging.exception(
            f"Unknown exception {type(exc)} when trying to delete lists for user {user_id}."
        )
        logging.debug(f"Details: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid list information provided")

    response = {"lists_deleted": number_of_lists_deleted}

    end_time = time.time()

    action = "DELETE"
    response_time_seconds = end_time - start_time
    logging.info(
        f"Gen3 User Data Library Response. Action: {action}. "
        f"count={number_of_lists_deleted}, response={response}, "
        f"response_time_seconds={response_time_seconds} user_id={user_id}")

    logging.debug(response)

    return JSONResponse(status_code=status.HTTP_201_CREATED, content=response)


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


@root_router.get("/lists/{id}/")
@root_router.get("/lists/{id}", include_in_schema=False)
async def get_list_by_id(
        list_id: int,
        request: Request,
        data_access_layer: DataAccessLayer = Depends(get_data_access_layer)) -> JSONResponse:
    """
    Find list by its id

    Args:
        :param list_id: the id of the list you wish to retrieve
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
        user_list = await data_access_layer.get_list(list_id)
        if user_list is None:
            raise HTTPException(status_code=404, detail="List not found")
        response = {"status": status_text, "timestamp": time.time(), "body": {
            "lists": {
                user_list.id: user_list.to_dict()}}}
    except Exception as e:
        return_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        status_text = "UNHEALTHY"
        response = {"status": status_text, "timestamp": time.time()}

    return JSONResponse(status_code=return_status, content=response)


# todo: put replaces list, patch updates
async def create_list_and_return_response(request, data_access_layer, user_list):
    user_id = await get_user_id(request=request)
    list_info = await try_creating_lists(data_access_layer, user_id, [user_list])
    list_data = list_info.popitem()
    assert list_data is not None
    response = {"status": "OK", "timestamp": time.time(), "created_list": list_data[1].to_dict()}
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=response)


async def try_modeling_user_list(user_list) -> Union[UserList, JSONResponse]:
    try:
        user_id = await get_user_id()
        list_as_orm = await create_user_list_instance(user_list, user_id)
    except Exception as e:
        return_status = status.HTTP_400_BAD_REQUEST
        status_text = "UNHEALTHY"
        response = {"status": status_text, "timestamp": time.time(),
                    "error": "malformed list, could not update"}
        return JSONResponse(status_code=return_status, content=response)
    return list_as_orm


async def ensure_list_exists_and_can_be_conformed(data_access_layer,
                                                  list_id,
                                                  body,
                                                  request) -> Union[UserList, JSONResponse]:
    list_exists = await data_access_layer.get_list(list_id) is not None
    user_list = dict(body.items())
    if not list_exists:
        return await create_list_and_return_response(request, data_access_layer, user_list)
    list_as_orm = await try_modeling_user_list(user_list)
    return list_as_orm


@root_router.put("/lists/{ID}/")
@root_router.put("/lists/{ID}", include_in_schema=False)
async def upsert_list_by_id(
        request: Request,
        list_id: int,
        body: dict,
        data_access_layer: DataAccessLayer = Depends(get_data_access_layer)) -> JSONResponse:
    """
    Create a new list if it does not exist with the provided content OR updates a list with the
        provided content if a list already exists.

    :param list_id: the id of the list you wish to retrieve
    :param request: FastAPI request (so we can check authorization)
    :param data_access_layer: how we interface with db
    :param body: content to change list
    :return: JSONResponse: simple status and timestamp in format: `{"status": "OK", "timestamp": time.time()}`
    """

    await authorize_request(
        request=request,
        # todo: what methods can we use?
        authz_access_method="upsert",
        authz_resources=["/gen3_data_library/service_info/status"])

    # todo: decide to keep ids as is, or switch to guids
    list_as_orm = await ensure_list_exists_and_can_be_conformed(data_access_layer,
                                                                list_id, body, request)
    if isinstance(list_as_orm, JSONResponse):
        return list_as_orm  # todo bonus: variable name is misleading, is there a better way to do this?

    try:
        outcome = await data_access_layer.replace_list(list_as_orm)
        response = {"status": "OK", "timestamp": time.time(), "updated_list": outcome.to_dict()}
        return_status = status.HTTP_200_OK
    except Exception as e:
        return_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        status_text = "UNHEALTHY"
        response = {"status": status_text, "timestamp": time.time()}

    return JSONResponse(status_code=return_status, content=response)


@root_router.patch("/lists/{ID}/")
@root_router.patch("/lists/{ID}", include_in_schema=False)
async def append_items_to_list(
        request: Request,
        list_id: int,
        body: dict,
        data_access_layer: DataAccessLayer = Depends(get_data_access_layer)) -> JSONResponse:
    await authorize_request(
        request=request,
        # todo: what methods can we use?
        authz_access_method="upsert",
        authz_resources=["/gen3_data_library/service_info/status"])
    # todo: decide to keep ids as is, or switch to guids
    list_as_orm = await ensure_list_exists_and_can_be_conformed(data_access_layer,
                                                                list_id, body, request)
    if isinstance(list_as_orm, JSONResponse):
        return list_as_orm  # todo bonus: variable name is misleading, is there a better way to do this?

    try:
        outcome = await data_access_layer.add_items_to_list(list_id, list_as_orm)
        response = {"status": "OK", "timestamp": time.time(), "updated_list": outcome.to_dict()}
        return_status = status.HTTP_200_OK
    except Exception as e:
        return_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        status_text = "UNHEALTHY"
        response = {"status": status_text, "timestamp": time.time()}

    return JSONResponse(status_code=return_status, content=response)



@root_router.delete("/lists/{ID}/")
@root_router.delete("/lists/{ID}", include_in_schema=False)
async def delete_list_by_id(
        list_id: int,
        request: Request,
        data_access_layer: DataAccessLayer = Depends(get_data_access_layer)) -> JSONResponse:
    """
    Delete a list under the given id

    :param list_id: the id of the list you wish to retrieve
    :param request: FastAPI request (so we can check authorization)
    :param data_access_layer: how we interface with db
    :return: JSONResponse: simple status and timestamp in format: `{"status": "OK", "timestamp": time.time()}`
    """
    await authorize_request(
        request=request,
        authz_access_method="create",
        authz_resources=["/gen3_data_library/service_info/status"])

    return_status = status.HTTP_201_CREATED
    status_text = "OK"

    try:
        list_deleted = await data_access_layer.delete_list(list_id)
    except Exception as e:
        return_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        status_text = "UNHEALTHY"
        list_deleted = 0

    response = {"status": status_text, "timestamp": time.time(), "list_deleted": bool(list_deleted)}

    return JSONResponse(status_code=return_status, content=response)
