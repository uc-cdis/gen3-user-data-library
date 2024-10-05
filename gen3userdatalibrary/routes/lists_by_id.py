import time

from fastapi import Request, Depends, HTTPException, APIRouter
from starlette import status
from starlette.responses import JSONResponse

from gen3userdatalibrary.models.user_list import RequestedUserListModel
from gen3userdatalibrary.services.auth import authorize_request, get_user_id
from gen3userdatalibrary.services.db import DataAccessLayer, get_data_access_layer
from gen3userdatalibrary.services.helpers import try_conforming_list, make_db_request_or_return_500

lists_by_id_router = APIRouter()


@lists_by_id_router.get("/{ID}")
@lists_by_id_router.get("/{ID}/", include_in_schema=False)
async def get_list_by_id(ID: int, request: Request,
                         data_access_layer: DataAccessLayer = Depends(get_data_access_layer)) -> JSONResponse:
    """
    Find list by its id

    Args:
        :param ID: the id of the list you wish to retrieve
        :param request: FastAPI request (so we can check authorization)
        :param data_access_layer: how we interface with db

    Returns:
        JSONResponse: simple status and timestamp in format: `{"status": "OK", "timestamp": time.time()}`
    """
    await authorize_request(request=request, authz_access_method="read",
                            authz_resources=["/gen3_data_library/service_info/status"])
    status_text = "OK"

    try:
        user_list = await data_access_layer.get_list(ID)
        if user_list is None:
            raise HTTPException(status_code=404, detail="List not found")
        return_status = status.HTTP_200_OK
        response = {"status": status_text, "timestamp": time.time(),
                    "body": {"lists": {user_list.id: user_list.to_dict()}}}
    except HTTPException as e:
        return_status = status.HTTP_404_NOT_FOUND
        content = {"status": e.status_code, "timestamp": time.time()}
        response = {"status": e.status_code, "content": content}
    except Exception as e:
        return_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        status_text = "UNHEALTHY"
        response = {"status": status_text, "timestamp": time.time()}

    return JSONResponse(status_code=return_status, content=response)


@lists_by_id_router.put("/{ID}")
@lists_by_id_router.put("/{ID}/", include_in_schema=False)
async def update_list_by_id(request: Request, ID: int, info_to_update_with: RequestedUserListModel,
                            data_access_layer: DataAccessLayer = Depends(get_data_access_layer)) -> JSONResponse:
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
    await authorize_request(request=request, authz_access_method="upsert",
                            authz_resources=["/gen3_data_library/service_info/status"])
    user_list = await data_access_layer.get_list(ID)
    if user_list is None:
        raise HTTPException(status_code=404, detail="List not found")
    user_id = get_user_id(request=request)
    list_as_orm = await try_conforming_list(user_id, info_to_update_with.__dict__)
    # todo: refactor error handling in this and append items
    try:
        outcome = await data_access_layer.replace_list(ID, list_as_orm)
        response = {"status": "OK", "timestamp": time.time(), "updated_list": outcome.to_dict()}
        return_status = status.HTTP_200_OK
    except Exception as e:
        return_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        status_text = "UNHEALTHY"
        response = {"status": status_text, "timestamp": time.time()}
    return JSONResponse(status_code=return_status, content=response)


@lists_by_id_router.patch("/{ID}")
@lists_by_id_router.patch("/{ID}/", include_in_schema=False)
async def append_items_to_list(request: Request, ID: int, body: dict,
                               data_access_layer: DataAccessLayer = Depends(get_data_access_layer)) -> JSONResponse:
    """
    Adds a list of provided items to an existing list

    Args:
        :param ID: the id of the list you wish to retrieve
        :param request: FastAPI request (so we can check authorization)
        :param data_access_layer: how we interface with db
        :param body: the items to be appended
        :return: JSONResponse: json response with info about the request outcome
    """
    await authorize_request(request=request,  # todo: what methods can we use?
                            authz_access_method="upsert", authz_resources=["/gen3_data_library/service_info/status"])
    # todo: decide to keep ids as is, or switch to guids
    list_exists = await data_access_layer.get_list(ID) is not None
    if not list_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="List does not exist")

    succeeded, data = await make_db_request_or_return_500(lambda: data_access_layer.add_items_to_list(ID, body))
    if succeeded:
        resp_content = {"status": "OK", "timestamp": time.time(), "data": data.to_dict()}
        return_status = status.HTTP_200_OK
        response = JSONResponse(status_code=return_status, content=resp_content)
    else:
        response = data
    return response


@lists_by_id_router.delete("/{ID}")
@lists_by_id_router.delete("/{ID}/", include_in_schema=False)
async def delete_list_by_id(ID: int, request: Request,
                            data_access_layer: DataAccessLayer = Depends(get_data_access_layer)) -> JSONResponse:
    """
    Delete a list under the given id

    Args:
        :param ID: the id of the list you wish to retrieve
        :param request: FastAPI request (so we can check authorization)
        :param data_access_layer: how we interface with db
        :return: JSONResponse: json response with info about the request outcome
    """
    await authorize_request(request=request, authz_access_method="create",
                            authz_resources=["/gen3_data_library/service_info/status"])
    return_status = status.HTTP_200_OK
    status_text = "OK"
    succeeded, data = await make_db_request_or_return_500(lambda: data_access_layer.get_list(ID))
    if not succeeded:
        return data
    elif data is None:
        response = {"status": status_text, "timestamp": time.time(), "list_deleted": False}
        return JSONResponse(status_code=404, content=response)

    succeeded, data = await make_db_request_or_return_500(lambda: data_access_layer.delete_list(ID))
    if succeeded:
        response = {"status": status_text, "timestamp": time.time(), "list_deleted": bool(data)}
    else:
        response = data
    return JSONResponse(status_code=return_status, content=response)
