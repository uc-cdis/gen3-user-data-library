import time

from fastapi import Request, Depends, HTTPException, APIRouter
from gen3authz.client.arborist.errors import ArboristError
from starlette import status
from starlette.responses import JSONResponse

from gen3userdatalibrary import config, logging
from gen3userdatalibrary.models.user_list import UserListResponseModel
from gen3userdatalibrary.services.auth import get_user_id, authorize_request, get_user_data_library_endpoint
from gen3userdatalibrary.services.db import DataAccessLayer, get_data_access_layer
from gen3userdatalibrary.services.helpers import try_conforming_list, derive_changes_to_make
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
    response_user_lists = {}
    for user_list in new_user_lists:
        response_user_lists[user_list.id] = user_list.to_dict()
        del response_user_lists[user_list.id]["id"]
    response = {"lists": response_user_lists}
    end_time = time.time()
    action = "READ"
    response_time_seconds = end_time - start_time
    logging.info(f"Gen3 User Data Library Response. Action: {action}. "
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
    #todo: write docs about shape of create and update
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
                e)  # keep going; maybe just some conflicts from things existing already  # TODO: Unsure if this is
            # safe, we might need to actually error here?

    await authorize_request(request=request, authz_access_method="create",
                            authz_resources=[get_user_data_library_endpoint(user_id)])
    raw_lists = requested_lists.get("lists", {})
    if not raw_lists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No lists provided!")
    start_time = time.time()

    new_lists_as_orm = [await try_conforming_list(user_id, user_list) for user_list in raw_lists]
    unique_list_identifiers = {(user_list.creator, user_list.name): user_list for user_list in new_lists_as_orm}
    lists_to_update = await data_access_layer.grab_all_lists_that_exist("name", list(unique_list_identifiers.keys()))
    set_of_existing_identifiers = set(map(lambda ul: (ul.creator, ul.name), lists_to_update))
    lists_to_create = list(
        filter(lambda ul: (ul.creator, ul.name) not in set_of_existing_identifiers, new_lists_as_orm))

    updated_lists = []
    for list_to_update in lists_to_update:
        identifier = (list_to_update.creator, list_to_update.name)
        new_version_of_list = unique_list_identifiers.get(identifier, None)
        assert new_version_of_list is not None
        changes_to_make = derive_changes_to_make(list_to_update, new_version_of_list)
        updated_list = await data_access_layer.update_and_persist_list(list_to_update.id, changes_to_make)
        updated_lists.append(updated_list)
    for list_to_create in lists_to_create:
        await data_access_layer.persist_user_list(user_id, list_to_create)

    response_user_lists = {}
    for user_list in (lists_to_create + updated_lists):
        response_user_lists[user_list.id] = user_list.to_dict()
        del response_user_lists[user_list.id]["id"]
    response = {"lists": response_user_lists}
    end_time = time.time()
    action = "CREATE"
    response_time_seconds = end_time - start_time
    logging.info(f"Gen3 User Data Library Response. Action: {action}. "
                 f"lists={requested_lists}, response={response}, "
                 f"response_time_seconds={response_time_seconds} user_id={user_id}")
    add_user_list_metric(fastapi_app=request.app, action=action, user_lists=[requested_lists],
                         response_time_seconds=response_time_seconds, user_id=user_id)
    logging.debug(response)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=response)


# todo: remember to check authz for /users/{{subject_id}}/user-data-library/lists/{{ID_0}}

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
    # todo: check this is tested
    user_id = await get_user_id(request=request)

    # dynamically create user policy
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

    response = {"lists_deleted": number_of_lists_deleted}

    end_time = time.time()

    action = "DELETE"
    response_time_seconds = end_time - start_time
    logging.info(f"Gen3 User Data Library Response. Action: {action}. "
                 f"count={number_of_lists_deleted}, response={response}, "
                 f"response_time_seconds={response_time_seconds} user_id={user_id}")

    logging.debug(response)

    return JSONResponse(status_code=status.HTTP_201_CREATED, content=response)
