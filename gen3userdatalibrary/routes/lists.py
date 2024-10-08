import time

from fastapi import Request, Depends, HTTPException, APIRouter
from gen3authz.client.arborist.errors import ArboristError
from starlette import status
from starlette.responses import JSONResponse

from gen3userdatalibrary import config, logging
from gen3userdatalibrary.models.user_list import UserListResponseModel
from gen3userdatalibrary.services import helpers
from gen3userdatalibrary.services.auth import get_user_id, authorize_request, get_user_data_library_endpoint
from gen3userdatalibrary.services.db import DataAccessLayer, get_data_access_layer
from gen3userdatalibrary.utils import add_user_list_metric

lists_router = APIRouter()


@lists_router.get("/", include_in_schema=False)
@lists_router.get("")
async def read_all_lists(request: Request,
                         data_access_layer: DataAccessLayer = Depends(get_data_access_layer)) -> JSONResponse:
    """
    Return all lists for user

    Args:
        :param request: FastAPI request (so we can check authorization)
        :param data_access_layer: how we interface with db
    """
    user_id = await get_user_id(request=request)
    # todo (myself): automatically auth request instead of typing it out in each endpoint?
    # dynamically create user policy
    await authorize_request(request=request, authz_access_method="read",
                            authz_resources=[get_user_data_library_endpoint(user_id)])
    start_time = time.time()

    try:
        new_user_lists = await data_access_layer.get_all_lists()
    except Exception as exc:
        logging.exception(f"Unknown exception {type(exc)} when trying to fetch lists.")
        logging.debug(f"Details: {exc}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid list information provided")
    response_user_lists = helpers.map_list_id_to_list_dict(new_user_lists)
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
                                                                 "description": "Bad request, unable to create list",
                                                             }})
@lists_router.put("/", include_in_schema=False)
async def upsert_user_lists(request: Request, requested_lists: dict,
                            data_access_layer: DataAccessLayer = Depends(get_data_access_layer)) -> JSONResponse:
    """
    Create a new list with the provided items, or update any lists that already exist

    Args:
        :param request: (Request) FastAPI request (so we can check authorization)
        :param requested_lists: Body from the POST, expects list of entities
        :param data_access_layer: (DataAccessLayer): Interface for data manipulations
    #todo (myself): write docs about shape of create and update
    """
    user_id = await get_user_id(request=request)

    # TODO dynamically create user policy, ROUGH UNTESTED VERSION: need to verify
    if not config.DEBUG_SKIP_AUTH:
        # make sure the user exists in Arborist
        # IMPORTANT: This is using the user's unique subject ID
        request.app.state.arborist_client.create_user_if_not_exist(user_id)

        resource = get_user_data_library_endpoint(user_id)

        try:
            logging.debug("attempting to update arborist resource: {}".format(resource))
            request.app.state.arborist_client.update_resource("/", resource, merge=True)
        except ArboristError as e:
            logging.error(
                e)  # keep going; maybe just some conflicts from things existing already
            # TODO: Unsure if this is
            # safe, we might need to actually error here?
    await authorize_request(request=request, authz_access_method="create",
                            authz_resources=[get_user_data_library_endpoint(user_id)])
    raw_lists = requested_lists.get("lists", {})
    if not raw_lists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No lists provided!")
    start_time = time.time()
    response_user_lists = await helpers.sort_persist_and_get_changed_lists(data_access_layer, raw_lists, user_id)
    end_time = time.time()
    response_time_seconds = end_time - start_time
    response = {"lists": response_user_lists}
    action = "CREATE"
    logging.info(f"Gen3 User Data Library Response. Action: {action}. "
                 f"lists={requested_lists}, response={response}, "
                 f"response_time_seconds={response_time_seconds} user_id={user_id}")
    add_user_list_metric(fastapi_app=request.app, action=action, user_lists=[requested_lists],
                         response_time_seconds=response_time_seconds, user_id=user_id)
    logging.debug(response)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=response)


# todo (addressed): remember to check authz for /users/{{subject_id}}/user-data-library/lists/{{ID_0}}
# lib for arborist requests. when a user makes a req, ensure an auth check goes to authz for
# the records they're trying to modify
# create will always work if they haven't hit limit
# for modify, get authz from the record
# make a request for record to arborist with sub id and id, check if they have write access
# need to check if they have read access
# filtering db based on the user in the first place, but may one day share with others
# make sure requests is done efficently

@lists_router.delete("")
@lists_router.delete("/", include_in_schema=False)
async def delete_all_lists(request: Request,
                           data_access_layer: DataAccessLayer = Depends(get_data_access_layer)) -> JSONResponse:
    """
    Delete all lists for a provided user

    Args:
        :param request: FastAPI request (so we can check authorization)
        :param data_access_layer: how we interface with db
    """
    user_id = await get_user_id(request=request)
    await authorize_request(request=request, authz_access_method="delete",
                            authz_resources=[get_user_data_library_endpoint(user_id)])

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
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=response)
