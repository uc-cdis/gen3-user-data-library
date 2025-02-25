from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from starlette import status
from starlette.responses import JSONResponse, Response

from gen3userdatalibrary.auth import get_user_id
from gen3userdatalibrary.db import DataAccessLayer, get_data_access_layer
from gen3userdatalibrary.models.helpers import create_user_list_instance
from gen3userdatalibrary.models.user_list import ItemToUpdateModel
from gen3userdatalibrary.routes.injection_dependencies import (
    validate_items,
    parse_and_auth_request,
)
from gen3userdatalibrary.utils.metrics import update_user_list_metric

only_auth_deps = [Depends(parse_and_auth_request)]
auth_and_items_deps = [Depends(parse_and_auth_request), Depends(validate_items)]

lists_by_id_router = APIRouter()


@lists_by_id_router.get(
    "/{list_id}",
    dependencies=only_auth_deps,
    status_code=status.HTTP_200_OK,
    description="Retrieves the list identified by the id for the user",
    summary="Get user's list by id",
    responses={
        status.HTTP_200_OK: {"description": "Successfully got id"},
        status.HTTP_401_UNAUTHORIZED: {
            "description": "User unauthorized when accessing endpoint"
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "User does not have access to requested data"
        },
        status.HTTP_404_NOT_FOUND: {"description": "Could not find id"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Something went wrong internally when processing the request"
        },
    },
)
@lists_by_id_router.get(
    "/{list_id}/",
    include_in_schema=False,
    dependencies=only_auth_deps,
)
async def get_list_by_id(
    list_id: UUID,
    request: Request,
    data_access_layer: DataAccessLayer = Depends(get_data_access_layer),
) -> JSONResponse:
    """
    Find list by its id

    Args:
         list_id (UUID): the id of the list you wish to retrieve
         request (Request): FastAPI request (so we can check authorization)
         data_access_layer (DataAccessLayer): how we interface with db

    Returns:
        JSONResponse: simple status and timestamp in format: `{"status": "OK", "timestamp": time.time()}`
    """
    result = await data_access_layer.get_user_list_by_list_id(list_id)
    if result is None:
        response = JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND, content="list_id not found!"
        )
    else:
        data = jsonable_encoder(result)
        response = JSONResponse(status_code=status.HTTP_200_OK, content=data)

    return response


@lists_by_id_router.put(
    "/{list_id}",
    dependencies=auth_and_items_deps,
    status_code=status.HTTP_200_OK,
    description="Updates contents of user list by id, name or items",
    summary="Update list by id",
    responses={
        status.HTTP_200_OK: {"description": "Successfully got id"},
        status.HTTP_400_BAD_REQUEST: {
            "description": "Bad request, unable to create list"
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "User unauthorized when accessing endpoint"
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "User does not have access to requested data"
        },
        status.HTTP_404_NOT_FOUND: {"description": "Could not find id"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Something went wrong internally when processing the request"
        },
    },
)
@lists_by_id_router.put(
    "/{list_id}/",
    include_in_schema=False,
    dependencies=auth_and_items_deps,
)
async def update_list_by_id(
    request: Request,
    list_id: UUID,
    info_to_update_with: ItemToUpdateModel,
    data_access_layer: DataAccessLayer = Depends(get_data_access_layer),
) -> JSONResponse:
    """
    Create a new list if it does not exist with the provided content OR updates a list with the
        provided content if a list already exists.

    Args:
         list_id (UUID): the id of the list you wish to retrieve
         request (Request): FastAPI request (so we can check authorization)
         data_access_layer (DataAccessLayer): how we interface with db
         info_to_update_with (ItemToUpdateModel): content to change list

    Returns:
         JSONResponse: json response with info about the request outcome
    """
    existing_list = await data_access_layer.get_user_list_by_list_id(list_id)
    if existing_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No UserList found with id {list_id}",
        )
    user_id = await get_user_id(request=request)
    new_user_list = create_user_list_instance(user_id, info_to_update_with)

    replace_result, metrics_info = await data_access_layer.change_list_contents(
        new_user_list, existing_list
    )
    data = jsonable_encoder(replace_result)
    response = JSONResponse(status_code=status.HTTP_200_OK, content=data)

    update_user_list_metric(
        fastapi_app=request.app,
        user_id=user_id,
        **metrics_info.model_dump(),
    )
    return response


@lists_by_id_router.patch(
    "/{list_id}",
    dependencies=auth_and_items_deps,
    status_code=status.HTTP_200_OK,
    description="Appends to the existing list",
    summary="Add to list",
    responses={
        status.HTTP_200_OK: {"description": "Successfully got id"},
        status.HTTP_400_BAD_REQUEST: {
            "description": "Bad request, unable to change list"
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "User unauthorized when accessing endpoint"
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "User does not have access to requested data"
        },
        status.HTTP_404_NOT_FOUND: {"description": "Could not find id"},
        status.HTTP_409_CONFLICT: {"description": "Nothing to append to list!"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Something went wrong internally when processing the request"
        },
    },
)
@lists_by_id_router.patch(
    "/{list_id}/",
    include_in_schema=False,
    dependencies=auth_and_items_deps,
)
async def append_items_to_list(
    request: Request,
    list_id: UUID,
    item_list: Dict[str, Any],
    data_access_layer: DataAccessLayer = Depends(get_data_access_layer),
) -> JSONResponse:
    """
    Adds a list of provided items to an existing list

    Args:
         list_id (UUID): the id of the list you wish to retrieve
         request (Request): FastAPI request (so we can check authorization)
         data_access_layer (DataAccessLayer): how we interface with db
         item_list (Dict[str, Any): the items to be appended

    Returns:
         JSONResponse: json response with info about the request outcome
    """
    if not item_list:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Nothing to append!"
        )
    user_list = await data_access_layer.get_user_list_by_list_id(list_id)
    list_exists = user_list is not None
    if not list_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="List does not exist"
        )

    append_result, metrics_info = await data_access_layer.add_items_to_list(
        list_id, item_list
    )
    data = jsonable_encoder(append_result)
    response = JSONResponse(status_code=status.HTTP_200_OK, content=data)
    user_id = await get_user_id(request=request)
    update_user_list_metric(
        fastapi_app=request.app,
        user_id=user_id,
        **metrics_info.model_dump(),
    )
    return response


@lists_by_id_router.delete(
    "/{list_id}",
    dependencies=only_auth_deps,
    status_code=status.HTTP_204_NO_CONTENT,
    description="Deletes the specified list",
    summary="Delete a list",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "User unauthorized when accessing endpoint"
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "User does not have access to requested data"
        },
        status.HTTP_404_NOT_FOUND: {"description": "Could not find id"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Something went wrong internally when processing the request"
        },
    },
)
@lists_by_id_router.delete(
    "/{list_id}/",
    include_in_schema=False,
    dependencies=only_auth_deps,
)
async def delete_list_by_id(
    list_id: UUID,
    request: Request,
    data_access_layer: DataAccessLayer = Depends(get_data_access_layer),
) -> Response:
    """
    Delete a list under the given id

    Args:
         list_id (UUID): the id of the list you wish to retrieve
         request (Request): FastAPI request (so we can check authorization)
         data_access_layer (DataAccessLayer): how we interface with db

    Returns:
         JSONResponse: json response with info about the request outcome
    """
    user_id = await get_user_id(request=request)

    get_result = await data_access_layer.get_user_list_by_list_id(list_id)
    if get_result is None:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    metrics_info = await data_access_layer.delete_list(list_id)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)

    update_user_list_metric(
        fastapi_app=request.app,
        user_id=user_id,
        **metrics_info.model_dump(),
    )
    return response
