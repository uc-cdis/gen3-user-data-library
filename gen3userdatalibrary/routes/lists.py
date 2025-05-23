from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from starlette import status
from starlette.responses import JSONResponse

from gen3userdatalibrary.auth import (
    get_user_id,
)
from gen3userdatalibrary.config import logging
from gen3userdatalibrary.db import DataAccessLayer, get_data_access_layer
from gen3userdatalibrary.models.helpers import (
    try_conforming_list,
    derive_changes_to_make,
)
from gen3userdatalibrary.models.user_list import (
    ItemToUpdateModel,
    UpdateItemsModel,
    UserList,
    UserListResponseModel,
)
from gen3userdatalibrary.routes.injection_dependencies import (
    sort_lists_into_create_or_update,
    validate_items,
    validate_lists,
    parse_and_auth_request,
)
from gen3userdatalibrary.utils.metrics import update_user_list_metric, MetricModel

lists_router = APIRouter()


@lists_router.get(
    "/",
    include_in_schema=False,
    dependencies=[
        Depends(parse_and_auth_request),
    ],
)
@lists_router.get(
    "",
    dependencies=[
        Depends(parse_and_auth_request),
    ],
    response_model=UserListResponseModel,
    status_code=status.HTTP_200_OK,
    description="Returns all lists that user can read",
    summary="Get all of user's lists",
    responses={
        status.HTTP_200_OK: {
            "model": UserListResponseModel,
            "description": "A list of all user lists the user owns",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "User unauthorized when accessing endpoint"
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "User does not have access to requested data"
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Something went wrong internally when processing the request"
        },
    },
)
async def read_all_lists(
    request: Request,
    data_access_layer: DataAccessLayer = Depends(get_data_access_layer),
) -> JSONResponse:
    """
    Return all lists for user

    Args:
        request (Request): FastAPI request (so we can check authorization)
        data_access_layer (DataAccessLayer): how we interface with db
    """
    user_id = await get_user_id(request=request)
    # dynamically create user policy

    try:
        user_lists = await data_access_layer.get_all_lists(user_id)
    except Exception as exc:
        logging.exception(f"Unknown exception {type(exc)} when trying to fetch lists.")
        logging.debug(f"Details: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="There was a problem trying to get list for the user. Try again later!",
        )

    id_to_list_dict = _map_list_id_to_list_dict(user_lists)
    json_conformed_data = jsonable_encoder(id_to_list_dict)
    response_data = {"lists": json_conformed_data}

    return JSONResponse(status_code=status.HTTP_200_OK, content=response_data)


@lists_router.put(
    # most of the following stuff helps populate the openapi docs
    "",
    response_model=UserListResponseModel,
    status_code=status.HTTP_201_CREATED,
    description="Create user list(s) by providing valid list information",
    summary="Create user lists(s)",
    responses={
        status.HTTP_201_CREATED: {
            "model": UserListResponseModel,
            "description": "Creates " "something from" " user request " "",
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Bad request, unable to create list"
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "User unauthorized when accessing endpoint"
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "User does not have access to requested data"
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Something went wrong internally when processing the request"
        },
    },
    dependencies=[
        Depends(parse_and_auth_request),
        Depends(validate_items),
        Depends(validate_lists),
    ],
)
@lists_router.put(
    "/",
    include_in_schema=False,
    dependencies=[
        Depends(parse_and_auth_request),
        Depends(validate_items),
        Depends(validate_lists),
    ],
)
async def upsert_user_lists(
    request: Request,
    requested_lists: UpdateItemsModel,
    data_access_layer: DataAccessLayer = Depends(get_data_access_layer),
) -> JSONResponse:
    """
    Create a new list with the provided items, or update any lists that already exist

    Args:
        request: (Request) FastAPI request (so we can check authorization)
            {"lists": [RequestedUserListModel]}
        requested_lists: (UpdateItemsModel) Body from the POST, expects list of entities
        data_access_layer: (DataAccessLayer): Interface for data manipulations

    Returns:

    """
    user_id = await get_user_id(request=request)

    raw_lists = requested_lists.lists

    updated_user_lists, metrics_info = await sort_persist_and_get_changed_lists(
        data_access_layer, raw_lists, user_id
    )

    json_conformed_data = jsonable_encoder(updated_user_lists)
    response_data = {"lists": json_conformed_data}
    response = JSONResponse(status_code=status.HTTP_201_CREATED, content=response_data)

    update_user_list_metric(
        fastapi_app=request.app,
        user_id=user_id,
        **metrics_info.model_dump(),
    )
    return response


@lists_router.delete(
    "",
    dependencies=[Depends(parse_and_auth_request)],
    status_code=status.HTTP_204_NO_CONTENT,
    description="Deletes all lists owned by the user",
    summary="Delete all of user's lists",
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "Successful request"},
        status.HTTP_401_UNAUTHORIZED: {
            "description": "User unauthorized when accessing endpoint"
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "User does not have access to requested data"
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Something went wrong internally when processing the request"
        },
    },
)
@lists_router.delete(
    "/", include_in_schema=False, dependencies=[Depends(parse_and_auth_request)]
)
async def delete_all_lists(
    request: Request,
    data_access_layer: DataAccessLayer = Depends(get_data_access_layer),
) -> Response:
    """
    Delete all lists for a provided user

    Args:
        request (Request): FastAPI request (so we can check authorization)
        data_access_layer (DataAccessLayer): how we interface with db
    """
    user_id = await get_user_id(request=request)
    try:
        metrics_info = await data_access_layer.delete_all_lists(user_id)
    except Exception as exc:
        logging.exception(
            f"Unknown exception {type(exc)} when trying to delete lists for user {user_id}."
        )
        logging.debug(f"Details: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid list information provided",
        )

    response = Response(status_code=status.HTTP_204_NO_CONTENT)

    update_user_list_metric(
        fastapi_app=request.app,
        user_id=user_id,
        **metrics_info.model_dump(),
    )
    return response


# region Helpers


def _map_list_id_to_list_dict(new_user_lists: List[UserList]):
    """
    maps list id => user list, remove user list id from user list (as dict)
    Args:
        new_user_lists: UserList

    Returns:
        user list id => UserList (as dict, without id)
    """
    response_user_lists = {}
    for user_list in new_user_lists:
        response_user_lists[user_list.id] = user_list.to_dict()
        del response_user_lists[user_list.id]["id"]
    return response_user_lists


async def sort_persist_and_get_changed_lists(
    data_access_layer: DataAccessLayer, raw_lists: List[ItemToUpdateModel], user_id: str
) -> (dict[str, dict], MetricModel):
    """
    Conforms and sorts lists into sets to be updated or created, persists them in db, handles any
    exceptions in trying to do so.

    Returns:
        id => list (as dict) relationship and a MetricModel

    Raises:
        409 HTTP exception if there is nothing to update
    """
    new_user_lists = [
        await try_conforming_list(user_id, user_list) for user_list in raw_lists
    ]
    unique_list_identifiers = {
        (user_list.creator, user_list.name): user_list for user_list in new_user_lists
    }
    lists_to_create, lists_to_update = await sort_lists_into_create_or_update(
        data_access_layer, unique_list_identifiers, new_user_lists
    )

    metrics_info = MetricModel(
        lists_added=len(lists_to_create),
        lists_updated=len(lists_to_update),
        lists_deleted=0,
        items_added=sum(len(user_list.items) for user_list in lists_to_create),
        items_updated=sum(len(user_list.items) for user_list in lists_to_update),
        items_deleted=0,
    )

    updated_lists = [
        await persist_lists_to_update(
            data_access_layer, list_to_update, unique_list_identifiers
        )
        for list_to_update in lists_to_update
    ]
    for list_to_create in lists_to_create:
        await data_access_layer.persist_user_list(user_id, list_to_create)
    response_user_lists = {}
    for user_list in lists_to_create + updated_lists:
        response_user_lists[user_list.id] = user_list.to_dict()
        del response_user_lists[user_list.id]["id"]
    return response_user_lists, metrics_info


async def persist_lists_to_update(
    data_access_layer, list_to_update, unique_list_identifiers
):
    """
    Handler for deriving changes to make to a list and persisting the update

    Args:
        data_access_layer (DataAccessLayer): data access interface
        list_to_update (UserList): list that you want to update the contents of
        unique_list_identifiers (Dict[Tuple[str, str], UserList]): (creator, name) => UserList with updates
    Raises:
        HTTPException if problem deriving changes
        any errors raised by sqlalchemy during persisting

    """
    identifier = (list_to_update.creator, list_to_update.name)
    new_version_of_list = unique_list_identifiers.get(identifier, None)
    if new_version_of_list is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"List to update has no corresponding new list instace to derive updates from. "
            f"List info: {identifier}",
        )
    changes_to_make = derive_changes_to_make(list_to_update, new_version_of_list)
    updated_list = await data_access_layer.update_and_persist_list(
        list_to_update.id, changes_to_make
    )
    return updated_list


# endregion
