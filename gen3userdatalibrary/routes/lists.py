import time
from typing import List

from fastapi import Request, Depends, HTTPException, APIRouter
from gen3authz.client.arborist.errors import ArboristError
from starlette import status
from starlette.responses import JSONResponse

from gen3userdatalibrary import config, logging
from gen3userdatalibrary.auth import (
    get_user_id,
    get_user_data_library_endpoint,
)
from gen3userdatalibrary.db import DataAccessLayer, get_data_access_layer
from gen3userdatalibrary.models.data import USER_LIST_UPDATE_ALLOW_LIST
from gen3userdatalibrary.models.user_list import (
    UserListResponseModel,
    UpdateItemsModel,
    UserList,
    ItemToUpdateModel,
)
from gen3userdatalibrary.routes.dependencies import (
    parse_and_auth_request,
    validate_items,
    validate_lists,
    sort_lists_into_create_or_update,
)
from gen3userdatalibrary.utils.core import (
    mutate_keys,
    find_differences,
    filter_keys,
)
from gen3userdatalibrary.utils.metrics import add_user_list_metric
from gen3userdatalibrary.utils.modeling import try_conforming_list

lists_router = APIRouter()


@lists_router.get(
    "/", include_in_schema=False, dependencies=[Depends(parse_and_auth_request)]
)
@lists_router.get("", dependencies=[Depends(parse_and_auth_request)])
async def read_all_lists(
    request: Request,
    data_access_layer: DataAccessLayer = Depends(get_data_access_layer),
) -> JSONResponse:
    """
    Return all lists for user

    Args:
        request: FastAPI request (so we can check authorization)
        data_access_layer: how we interface with db
    """
    user_id = await get_user_id(request=request)
    # dynamically create user policy
    start_time = time.time()

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
    response_user_lists = mutate_keys(lambda k: str(k), id_to_list_dict)
    response = {"lists": response_user_lists}
    end_time = time.time()
    response_time_seconds = end_time - start_time
    logging.info(
        f"Gen3 User Data Library Response. Action: READ. "
        f"response={response}, response_time_seconds={response_time_seconds} user_id={user_id}"
    )
    logging.debug(response)
    return JSONResponse(status_code=status.HTTP_200_OK, content=response)


@lists_router.put(
    # most of the following stuff helps populate the openapi docs
    "",
    response_model=UserListResponseModel,
    status_code=status.HTTP_201_CREATED,
    description="Create user list(s) by providing valid list information",
    tags=["User Lists"],
    summary="Create user lists(s)",
    responses={
        status.HTTP_201_CREATED: {
            "model": UserListResponseModel,
            "description": "Creates " "something from" " user request " "",
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Bad request, unable to create list"
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No lists provided!"
        )
    start_time = time.time()
    updated_user_lists = await sort_persist_and_get_changed_lists(
        data_access_layer, raw_lists, user_id
    )
    response_user_lists = mutate_keys(lambda k: str(k), updated_user_lists)
    end_time = time.time()
    response_time_seconds = end_time - start_time
    response = {"lists": response_user_lists}
    action = "CREATE"
    logging.info(
        f"Gen3 User Data Library Response. Action: {action}. "
        f"lists={requested_lists}, response={response}, "
        f"response_time_seconds={response_time_seconds} user_id={user_id}"
    )
    add_user_list_metric(
        fastapi_app=request.app,
        action=action,
        user_lists=requested_lists.lists,
        response_time_seconds=response_time_seconds,
        user_id=user_id,
    )
    logging.debug(response)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=response)


@lists_router.delete("", dependencies=[Depends(parse_and_auth_request)])
@lists_router.delete(
    "/", include_in_schema=False, dependencies=[Depends(parse_and_auth_request)]
)
async def delete_all_lists(
    request: Request,
    data_access_layer: DataAccessLayer = Depends(get_data_access_layer),
) -> JSONResponse:
    """
    Delete all lists for a provided user

    Args:
        request: FastAPI request (so we can check authorization)
        data_access_layer: how we interface with db
    """
    start_time = time.time()
    user_id = await get_user_id(request=request)
    try:
        number_of_lists_deleted = await data_access_layer.delete_all_lists(user_id)
    except Exception as exc:
        logging.exception(
            f"Unknown exception {type(exc)} when trying to delete lists for user {user_id}."
        )
        logging.debug(f"Details: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid list information provided",
        )
    end_time = time.time()
    response_time_seconds = end_time - start_time

    action = "DELETE"
    response = {"lists_deleted": number_of_lists_deleted}
    logging.info(
        f"Gen3 User Data Library Response. Action: {action}. "
        f"count={number_of_lists_deleted}, response={response}, "
        f"response_time_seconds={response_time_seconds} user_id={user_id}"
    )
    logging.debug(response)
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=response)


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


def derive_changes_to_make(list_to_update: UserList, new_list: UserList):
    """
    Given an old list and new list, gets the changes in the new list to be added
    to the old list
    """
    properties_to_old_new_difference = find_differences(list_to_update, new_list)
    relevant_differences = filter_keys(
        lambda k, _: k in USER_LIST_UPDATE_ALLOW_LIST, properties_to_old_new_difference
    )
    has_no_relevant_differences = not relevant_differences or (
        len(relevant_differences) == 1
        and relevant_differences.__contains__("updated_time")
    )
    if has_no_relevant_differences:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing to update!"
        )
    property_to_change_to_make = {
        k: diff_tuple[1] for k, diff_tuple in relevant_differences.items()
    }
    return property_to_change_to_make


async def sort_persist_and_get_changed_lists(
    data_access_layer: DataAccessLayer, raw_lists: List[ItemToUpdateModel], user_id: str
) -> dict[str, dict]:
    """
    Conforms and sorts lists into sets to be updated or created, persists them, and returns an
    id => list (as dict) relationship
    """
    new_lists_as_orm = [
        await try_conforming_list(user_id, user_list) for user_list in raw_lists
    ]
    unique_list_identifiers = {
        (user_list.creator, user_list.name): user_list for user_list in new_lists_as_orm
    }
    lists_to_create, lists_to_update = await sort_lists_into_create_or_update(
        data_access_layer, unique_list_identifiers, new_lists_as_orm
    )
    updated_lists = []
    for list_to_update in lists_to_update:
        identifier = (list_to_update.creator, list_to_update.name)
        new_version_of_list = unique_list_identifiers.get(identifier, None)
        assert new_version_of_list is not None
        changes_to_make = derive_changes_to_make(list_to_update, new_version_of_list)
        updated_list = await data_access_layer.update_and_persist_list(
            list_to_update.id, changes_to_make
        )
        updated_lists.append(updated_list)
    for list_to_create in lists_to_create:
        await data_access_layer.persist_user_list(user_id, list_to_create)
    response_user_lists = {}
    for user_list in lists_to_create + updated_lists:
        response_user_lists[user_list.id] = user_list.to_dict()
        del response_user_lists[user_list.id]["id"]
    return response_user_lists


# endregion
