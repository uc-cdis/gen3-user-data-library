import time

from fastapi import Request, Depends, HTTPException, APIRouter
from gen3authz.client.arborist.errors import ArboristError
from starlette import status
from starlette.responses import JSONResponse

from gen3userdatalibrary import config, logging
from gen3userdatalibrary.models.user_list import UserListResponseModel, UpdateItemsModel
from gen3userdatalibrary.services.auth import get_user_id, get_user_data_library_endpoint
from gen3userdatalibrary.services.db import DataAccessLayer, get_data_access_layer
from gen3userdatalibrary.services.helpers.core import map_list_id_to_list_dict
from gen3userdatalibrary.services.helpers.db import sort_persist_and_get_changed_lists
from gen3userdatalibrary.services.helpers.dependencies import parse_and_auth_request, validate_items, validate_lists
from gen3userdatalibrary.utils import add_user_list_metric, mutate_keys

lists_router = APIRouter()


@lists_router.get("/", include_in_schema=False, dependencies=[Depends(parse_and_auth_request)])
@lists_router.get("", dependencies=[Depends(parse_and_auth_request)])
async def read_all_lists(request: Request,
                         data_access_layer: DataAccessLayer = Depends(get_data_access_layer)) -> JSONResponse:
    """
    Return all lists for user

    Args:
        :param request: FastAPI request (so we can check authorization)
        :param data_access_layer: how we interface with db
    """
    user_id = await get_user_id(request=request)
    # dynamically create user policy
    start_time = time.time()

    try:
        new_user_lists = await data_access_layer.get_all_lists(user_id)
    except Exception as exc:
        logging.exception(f"Unknown exception {type(exc)} when trying to fetch lists.")
        logging.debug(f"Details: {exc}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid list information provided")
    id_to_list_dict = map_list_id_to_list_dict(new_user_lists)
    response_user_lists = mutate_keys(lambda k: str(k), id_to_list_dict)
    response = {"lists": response_user_lists}
    end_time = time.time()
    response_time_seconds = end_time - start_time
    logging.info(f"Gen3 User Data Library Response. Action: READ. "
                 f"response={response}, response_time_seconds={response_time_seconds} user_id={user_id}")
    logging.debug(response)
    return JSONResponse(status_code=status.HTTP_200_OK, content=response)


@lists_router.put("",  # most of the following stuff helps populate the openapi docs
                  response_model=UserListResponseModel, status_code=status.HTTP_201_CREATED,
                  description="Create user list(s) by providing valid list information", tags=["User Lists"],
                  summary="Create user lists(s)", responses={status.HTTP_201_CREATED: {"model": UserListResponseModel,
                                                                                       "description": "Creates "
                                                                                                      "something from"
                                                                                                      " user request "
                                                                                                      "", },
                                                             status.HTTP_400_BAD_REQUEST: {
                                                                 "description": "Bad request, unable to create list"}},
                  dependencies=[Depends(parse_and_auth_request), Depends(validate_items), Depends(validate_lists)])
@lists_router.put("/",
                  include_in_schema=False,
                  dependencies=[Depends(parse_and_auth_request), Depends(validate_items), Depends(validate_lists)])
async def upsert_user_lists(request: Request,
                            requested_lists: UpdateItemsModel,
                            data_access_layer: DataAccessLayer = Depends(get_data_access_layer)) -> JSONResponse:
    """
    Create a new list with the provided items, or update any lists that already exist

    Args:
        :param request: (Request) FastAPI request (so we can check authorization)
            {"lists": [RequestedUserListModel]}
        :param requested_lists: Body from the POST, expects list of entities
        :param data_access_layer: (DataAccessLayer): Interface for data manipulations
    """
    user_id = await get_user_id(request=request)

    if not config.DEBUG_SKIP_AUTH:
        # make sure the user exists in Arborist
        # IMPORTANT: This is using the user's unique subject ID
        request.app.state.arborist_client.create_user_if_not_exist(user_id)

        resource = get_user_data_library_endpoint(user_id)

        try:
            logging.debug("attempting to update arborist resource: {}".format(resource))
            request.app.state.arborist_client.update_resource("/", resource, merge=True)
        except ArboristError as e:
            logging.error(e)
            # keep going; maybe just some conflicts from things existing already

    raw_lists = requested_lists.lists
    if not raw_lists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No lists provided!")
    start_time = time.time()
    updated_user_lists = await sort_persist_and_get_changed_lists(data_access_layer, raw_lists, user_id)
    response_user_lists = mutate_keys(lambda k: str(k), updated_user_lists)
    end_time = time.time()
    response_time_seconds = end_time - start_time
    response = {"lists": response_user_lists}
    action = "CREATE"
    logging.info(f"Gen3 User Data Library Response. Action: {action}. "
                 f"lists={requested_lists}, response={response}, "
                 f"response_time_seconds={response_time_seconds} user_id={user_id}")
    add_user_list_metric(fastapi_app=request.app, action=action, user_lists=requested_lists.lists,
                         response_time_seconds=response_time_seconds, user_id=user_id)
    logging.debug(response)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=response)


@lists_router.delete("", dependencies=[Depends(parse_and_auth_request)])
@lists_router.delete("/", include_in_schema=False, dependencies=[Depends(parse_and_auth_request)])
async def delete_all_lists(request: Request,
                           data_access_layer: DataAccessLayer = Depends(get_data_access_layer)) -> JSONResponse:
    """
    Delete all lists for a provided user

    Args:
        :param request: FastAPI request (so we can check authorization)
        :param data_access_layer: how we interface with db
    """
    start_time = time.time()
    user_id = await get_user_id(request=request)
    try:
        number_of_lists_deleted = await data_access_layer.delete_all_lists(user_id)
    except Exception as exc:
        logging.exception(f"Unknown exception {type(exc)} when trying to delete lists for user {user_id}.")
        logging.debug(f"Details: {exc}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid list information provided")
    end_time = time.time()
    response_time_seconds = end_time - start_time

    action = "DELETE"
    response = {"lists_deleted": number_of_lists_deleted}
    logging.info(f"Gen3 User Data Library Response. Action: {action}. "
                 f"count={number_of_lists_deleted}, response={response}, "
                 f"response_time_seconds={response_time_seconds} user_id={user_id}")
    logging.debug(response)
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=response)
