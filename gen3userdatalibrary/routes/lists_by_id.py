import time
from typing import Dict, Any
from uuid import UUID

from fastapi import Request, Depends, HTTPException, APIRouter
from starlette import status
from starlette.responses import JSONResponse

from gen3userdatalibrary.models.user_list import ItemToUpdateModel
from gen3userdatalibrary.services.auth import authorize_request, get_user_id
from gen3userdatalibrary.services.db import DataAccessLayer, get_data_access_layer
from gen3userdatalibrary.services.helpers.dependencies import (
    parse_and_auth_request,
    validate_items,
    ensure_items_less_than_max,
)
from gen3userdatalibrary.services.helpers.error_handling import (
    make_db_request_or_return_500,
)
from gen3userdatalibrary.services.helpers.modeling import try_conforming_list
from gen3userdatalibrary.utils import update

lists_by_id_router = APIRouter()


@lists_by_id_router.get("/{ID}", dependencies=[Depends(parse_and_auth_request)])
@lists_by_id_router.get(
    "/{ID}/", include_in_schema=False, dependencies=[Depends(parse_and_auth_request)]
)
async def get_list_by_id(
    ID: UUID,
    request: Request,
    data_access_layer: DataAccessLayer = Depends(get_data_access_layer),
) -> JSONResponse:
    """
    Find list by its id

    Args:
        :param ID: the id of the list you wish to retrieve
        :param request: FastAPI request (so we can check authorization)
        :param data_access_layer: how we interface with db

    Returns:
        JSONResponse: simple status and timestamp in format: `{"status": "OK", "timestamp": time.time()}`
    """
    await authorize_request(
        request=request,
        authz_access_method="read",
        authz_resources=["/gen3_data_library/service_info/status"],
    )
    status_text = "OK"

    succeeded, get_result = await make_db_request_or_return_500(
        lambda: data_access_layer.get_list(ID)
    )
    if not succeeded:
        response = get_result
    elif get_result is None:
        resp_content = {"status": "NOT FOUND", "timestamp": time.time()}
        response = JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND, content=resp_content
        )
    else:
        data = update("id", lambda ul_id: str(ul_id), get_result.to_dict())
        resp_content = {
            "status": status_text,
            "timestamp": time.time(),
            "body": {"lists": {str(get_result.id): data}},
        }
        response = JSONResponse(status_code=status.HTTP_200_OK, content=resp_content)
    return response


@lists_by_id_router.put(
    "/{ID}", dependencies=[Depends(parse_and_auth_request), Depends(validate_items)]
)
@lists_by_id_router.put(
    "/{ID}/",
    include_in_schema=False,
    dependencies=[Depends(parse_and_auth_request), Depends(validate_items)],
)
async def update_list_by_id(
    request: Request,
    ID: UUID,
    info_to_update_with: ItemToUpdateModel,
    data_access_layer: DataAccessLayer = Depends(get_data_access_layer),
) -> JSONResponse:
    """
    Create a new list if it does not exist with the provided content OR updates a list with the
        provided content if a list already exists.

    Args:
        :param ID: the id of the list you wish to retrieve
        :param request: FastAPI request (so we can check authorization)
        :param data_access_layer: how we interface with db
        :param info_to_update_with: content to change list
        :return: JSONResponse: json response with info about the request outcome
    """
    user_list = await data_access_layer.get_list(ID)
    if user_list is None:
        raise HTTPException(status_code=404, detail="List not found")
    user_id = await get_user_id(request=request)
    list_as_orm = await try_conforming_list(user_id, info_to_update_with)
    ensure_items_less_than_max(len(info_to_update_with.items))
    succeeded, update_result = await make_db_request_or_return_500(
        lambda: data_access_layer.replace_list(ID, list_as_orm)
    )

    if not succeeded:
        response = update_result
    else:
        data = update("id", lambda ul_id: str(ul_id), update_result.to_dict())
        resp_content = {"status": "OK", "timestamp": time.time(), "updated_list": data}
        return_status = status.HTTP_200_OK
        response = JSONResponse(status_code=return_status, content=resp_content)
    return response


@lists_by_id_router.patch(
    "/{ID}", dependencies=[Depends(parse_and_auth_request), Depends(validate_items)]
)
@lists_by_id_router.patch(
    "/{ID}/",
    include_in_schema=False,
    dependencies=[Depends(parse_and_auth_request), Depends(validate_items)],
)
async def append_items_to_list(
    request: Request,
    ID: UUID,
    item_list: Dict[str, Any],
    data_access_layer: DataAccessLayer = Depends(get_data_access_layer),
) -> JSONResponse:
    """
    Adds a list of provided items to an existing list

    Args:
        :param ID: the id of the list you wish to retrieve
        :param request: FastAPI request (so we can check authorization)
        :param data_access_layer: how we interface with db
        :param item_list: the items to be appended
        :return: JSONResponse: json response with info about the request outcome
    """
    user_list = await data_access_layer.get_list(ID)
    list_exists = user_list is not None
    if not list_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="List does not exist"
        )
    ensure_items_less_than_max(len(item_list), len(user_list.items))

    succeeded, append_result = await make_db_request_or_return_500(
        lambda: data_access_layer.add_items_to_list(ID, item_list)
    )

    if succeeded:
        data = update("id", lambda ul_id: str(ul_id), append_result.to_dict())
        resp_content = {"status": "OK", "timestamp": time.time(), "data": data}
        return_status = status.HTTP_200_OK
        response = JSONResponse(status_code=return_status, content=resp_content)
    else:
        response = append_result
    return response


@lists_by_id_router.delete("/{ID}", dependencies=[Depends(parse_and_auth_request)])
@lists_by_id_router.delete(
    "/{ID}/", include_in_schema=False, dependencies=[Depends(parse_and_auth_request)]
)
async def delete_list_by_id(
    ID: UUID,
    request: Request,
    data_access_layer: DataAccessLayer = Depends(get_data_access_layer),
) -> JSONResponse:
    """
    Delete a list under the given id

    Args:
        :param ID: the id of the list you wish to retrieve
        :param request: FastAPI request (so we can check authorization)
        :param data_access_layer: how we interface with db
        :return: JSONResponse: json response with info about the request outcome
    """
    succeeded, delete_result = await make_db_request_or_return_500(
        lambda: data_access_layer.get_list(ID)
    )
    if not succeeded:
        return delete_result
    elif delete_result is None:
        response = {
            "status": "NOT FOUND",
            "timestamp": time.time(),
            "list_deleted": False,
        }
        return JSONResponse(status_code=404, content=response)

    succeeded, data = await make_db_request_or_return_500(
        lambda: data_access_layer.delete_list(ID)
    )
    if succeeded:
        resp_content = {
            "status": "OK",
            "timestamp": time.time(),
            "list_deleted": bool(data),
        }
        response = JSONResponse(status_code=200, content=resp_content)
    else:
        response = data
    return response
