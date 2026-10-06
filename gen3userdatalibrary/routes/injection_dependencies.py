import json
from typing import List, Dict, Tuple, Union, Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from gen3authz.client.arborist.errors import ArboristError
from jsonschema.validators import validate
from starlette import status

from gen3userdatalibrary import config
from gen3userdatalibrary.auth import (
    get_user_id,
    authorize_request,
)
from gen3userdatalibrary.config import logging
from gen3userdatalibrary.db import get_data_access_layer, DataAccessLayer
from gen3userdatalibrary.models.helpers import (
    try_conforming_list,
    conform_to_item_update,
)
from gen3userdatalibrary.models.user_list import UserList
from gen3userdatalibrary.routes.route_configurations import (
    ENDPOINT_TO_CONTEXT,
    get_resource_from_endpoint_context,
)
from gen3userdatalibrary.utils.core import (
    build_switch_case,
    LIST_ID_NOT_FOUND_ERROR_MSG,
)


async def validate_upsert_items(lists_to_upsert, dal, user_id):
    """
    Sort the user's provided list's items for upsert and ensure they have the correct structure

    Args:
        lists_to_upsert (Dict["lists": [ItemsToUpdateModel]]): lists to be created or added
        dal (DataAccessLayer): data access interface
        user_id (str): creator id
    Raises:
        any exceptions from sorting the lists or checking the items
    """
    raw_lists = lists_to_upsert["lists"]
    new_user_lists = [
        await try_conforming_list(user_id, conform_to_item_update(user_list))
        for user_list in raw_lists
    ]
    unique_list_identifiers = {
        (user_list.creator, user_list.name): user_list for user_list in new_user_lists
    }
    lists_to_create, lists_to_update = await sort_lists_into_create_or_update(
        dal, unique_list_identifiers, new_user_lists
    )
    for list_to_update in lists_to_update:
        await check_items_in_list_to_update_less_than_max(
            list_to_update, unique_list_identifiers
        )
    for item_to_create in lists_to_create:
        ensure_items_less_than_max(len(item_to_create.items))


async def check_items_in_list_to_update_less_than_max(
    old_list_to_update, identifier_to_new_user_list: Dict[Tuple[str, str], UserList]
):
    """
    Checks that the items in the old version of the list + the new version of the list are less that max config

    Args:
        old_list_to_update (UserList): old version of list before the new changes
        identifier_to_new_user_list (Dict[Tuple[str, str], UserList]): maps (creator, name) to new version of user list

    Raises:
        exception if old list doesn't have any matching new list to update, which should not happen
    """
    identifier = (old_list_to_update.creator, old_list_to_update.name)
    new_version_of_list = identifier_to_new_user_list.get(identifier, None)
    if new_version_of_list is None:
        raise ValueError("No unique identifier, cannot update list!")
    ensure_items_less_than_max(
        len(new_version_of_list.items), len(old_list_to_update.items)
    )


async def ensure_list_exists_and_items_less_than_max(basic_list_info, dal, list_id):
    """
    Check we can get the list and that items are less than max config

    Args:
        basic_list_info (ItemToUpdateModel as Dict): basic info about the list; name and creator
        dal (DataAccessLayer): data access layer instance
        list_id (UUID): id of the list
    Raises:
        HTTPException if the id is not recognized or something happened with arborist
    """
    try:
        list_to_append = await dal.get_existing_list_or_throw(list_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=LIST_ID_NOT_FOUND_ERROR_MSG
        )
    except ArboristError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something went wrong while validating request!",
        )
    ensure_items_less_than_max(len(basic_list_info["items"]), len(list_to_append.items))


async def parse_and_auth_request(
    request: Request, dal: DataAccessLayer = Depends(get_data_access_layer)
):
    """
    Authorize the request with arborist to ensure the request can be made

    For endpoints that act on a specific list, the resources checked are the ones stored
    in that list's `authz` field (set to the creator's path on creation), so a user cannot
    act on another user's list just by supplying its id. For those endpoints, a denied
    request is reported the same way as a list that does not exist, so a requester cannot
    tell whether a list they cannot access exists.

    Args:
        request (Request): fastapi request entity
        dal (DataAccessLayer): data access instance

    Raises:
        HTTPException based on authorize_request outcome, or 404 if access to a specific
            list is denied
    """
    user_id = await get_user_id(request=request)
    path_params = request.scope["path_params"]
    route_function = request.scope["route"].name

    if route_function not in ENDPOINT_TO_CONTEXT:
        raise Exception(f"Undefined route '{route_function}', unable to auth")

    endpoint_context = ENDPOINT_TO_CONTEXT[route_function]
    resources = await get_list_authz_resources(endpoint_context, path_params, dal)
    if resources is None:
        # not a list-specific endpoint (or the list does not exist, which the endpoint
        # will report as a 404), so check against the requester's own resource path
        resources = [
            get_resource_from_endpoint_context(endpoint_context, user_id, path_params)
        ]
    logging.debug(f"Authorizing user: {user_id}")
    try:
        await authorize_request(
            request=request,
            authz_access_method=endpoint_context["method"],
            authz_resources=resources,
        )
    except HTTPException as exc:
        is_list_endpoint = endpoint_context.get("type", None) == "id"
        if is_list_endpoint and exc.status_code == status.HTTP_403_FORBIDDEN:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=LIST_ID_NOT_FOUND_ERROR_MSG,
            ) from exc
        raise


async def get_list_authz_resources(
    endpoint_context: Dict[str, Any], path_params: dict, dal: DataAccessLayer
) -> Union[List[str], None]:
    """
    Get the arborist resource paths stored on the list referenced by the request

    Args:
        endpoint_context (Dict[str, Any]): information about an endpoint from ENDPOINT_TO_CONTEXT
        path_params (dict): any params from the request scope
        dal (DataAccessLayer): data access instance

    Returns:
        the list's `authz` resource paths, or None if the endpoint does not act on a
        specific list or the list does not exist

    Raises:
        HTTPException (404) if the list exists but has no authz resources recorded
    """
    if endpoint_context.get("type", None) != "id":
        return None

    try:
        list_id = UUID(str(path_params["list_id"]))
    except ValueError:
        logging.debug(f"Rejecting malformed list_id: {path_params["list_id"]}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=LIST_ID_NOT_FOUND_ERROR_MSG
        )

    user_list = await dal.get_user_list_by_list_id(list_id)
    if user_list is None:
        return None

    resources = (user_list.authz or {}).get("authz", [])
    if not resources:
        logging.error(f"List {user_list.id} has no authz resources, denying access")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=LIST_ID_NOT_FOUND_ERROR_MSG
        )
    return resources


# region User Lists


async def sort_lists_into_create_or_update(
    data_access_layer, unique_list_identifiers, new_user_lists: List[UserList]
):
    """
    Discerns if a list is to be created or updated, so we know whether to compare it against an existing user list

    Args:
        data_access_layer (DataAccessLayer): data access instance
        unique_list_identifiers (Dict[Tuple(str, str)], UserList]): (name, creator) => new user list
        new_user_lists (List[UserList]): list of user lists to either create or update

    Returns:

    """
    lists_to_update = await data_access_layer.grab_all_lists_that_exist(
        "name", list(unique_list_identifiers.keys())
    )
    set_of_existing_identifiers = set(
        map(lambda ul: (ul.creator, ul.name), lists_to_update)
    )
    lists_to_create = list(
        filter(
            lambda ul: (ul.creator, ul.name) not in set_of_existing_identifiers,
            new_user_lists,
        )
    )
    return lists_to_create, lists_to_update


async def validate_lists(
    request: Request, dal: DataAccessLayer = Depends(get_data_access_layer)
):
    """
    Ensures user hasn't added too many lists

    Args:
        request (Request): fastapi request entity
        dal (DataAccessLayer): data access instance

    Raises:
        exceptions from sorting, validating items, or validating lists

    """
    user_id = await get_user_id(request=request)
    conformed_body = json.loads(await request.body())
    raw_lists = conformed_body["lists"]
    new_user_lists = [
        await try_conforming_list(user_id, conform_to_item_update(user_list))
        for user_list in raw_lists
    ]
    unique_list_identifiers = {
        (user_list.creator, user_list.name): user_list for user_list in new_user_lists
    }
    lists_to_create, lists_to_update = await sort_lists_into_create_or_update(
        dal, unique_list_identifiers, new_user_lists
    )

    for item_to_create in lists_to_create:
        ensure_items_less_than_max(len(item_to_create.items))

    await dal.ensure_user_has_not_reached_max_lists(user_id, len(lists_to_create))


# endregion

# region List Items


def validate_user_list_item(item_contents: dict):
    """
    Ensures that the item component of a user list has the correct setup for type property

    Args:
        item_contents (Dict[str, Any): the item component of a user list
    Raises:
        exception based on the outcome of validate
    """
    content_type = item_contents.get("type", None)
    matching_schema = config.ITEM_SCHEMAS.get(content_type, None)
    if matching_schema is None:
        config.logging.error("No matching schema for type, aborting!")
        raise HTTPException(
            status_code=400, detail="No matching schema identified for items, aborting!"
        )
    validate(instance=item_contents, schema=matching_schema)


def ensure_any_items_match_schema(endpoint_context, basic_user_lists):
    """
    Ensure lists from the request validate against schema config
    Args:
        endpoint_context (Dict[str, Any]): endpoint specific information for validation purposes
        basic_user_lists (Dict["lists": List[ItemToUpdateModel as Dict]]):

    """
    item_dict: Union[List, Dict] = endpoint_context.get("items", lambda _: [])(
        basic_user_lists
    )
    body_type = type(item_dict)
    if body_type is list:
        for item_set in item_dict:
            for item_contents in item_set.values():
                validate_user_list_item(item_contents)
    elif body_type is dict:
        for item_contents in item_dict.values():
            validate_user_list_item(item_contents)


def _raise_exception(e):
    raise e


async def validate_items(
    request: Request, dal: DataAccessLayer = Depends(get_data_access_layer)
):
    """
    General item validator dependency for all kinds of endpoints

    Args:
        request (Request): fast api request entity
        dal (DataAccessLayer): data access instance

    Raises:
        HTTPException if body is not correctly formatted
    """
    route_function = request.scope["route"].name
    endpoint_context = ENDPOINT_TO_CONTEXT.get(route_function, {})
    conformed_body = json.loads(await request.body())
    user_id = await get_user_id(request=request)
    list_id = request["path_params"].get("list_id", None)

    # check existence before validating the body, so a missing list responds the same as a
    # list the requester cannot access (which is rejected before this dependency runs)
    if list_id is not None:
        try:
            list_exists = (
                await dal.get_user_list_by_list_id(UUID(str(list_id))) is not None
            )
        except ValueError:
            logging.debug(f"Rejecting malformed list_id: {list_id}")
            list_exists = False
        if not list_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=LIST_ID_NOT_FOUND_ERROR_MSG,
            )

    try:
        ensure_any_items_match_schema(endpoint_context, conformed_body)
    except Exception as e:
        logging.error(e)
        raise HTTPException(
            status_code=400,
            detail="Problem trying to validate body. Is your body formatted "
            "correctly?",
        )
    route_function_to_validation_handler = build_switch_case(
        {
            "upsert_user_lists": lambda: validate_upsert_items(
                conformed_body, dal, user_id
            ),
            "append_items_to_list": lambda: validate_items_to_append(
                conformed_body, dal, list_id
            ),
            "update_list_by_id": lambda: ensure_list_exists_and_items_less_than_max(
                conformed_body, dal, list_id
            ),
        },
        lambda: _raise_exception(Exception("Invalid route function identified! ")),
    )
    run_validation_handler = route_function_to_validation_handler(route_function)
    await run_validation_handler()


def ensure_items_less_than_max(number_of_new_items, existing_item_count=0):
    """
    Basic check to see total item count is less than max config

    Args:
        number_of_new_items (int): count of new items to add
        existing_item_count (int): count of existing items

    Raises:
        HTTPException if too many items in list

    """
    more_items_than_max = (
        existing_item_count + number_of_new_items > config.MAX_LIST_ITEMS
    )
    if more_items_than_max:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Too many items in list",
        )


async def validate_items_to_append(
    item_list: Dict[str, Any], dal: DataAccessLayer, list_id: UUID
):
    """
    Validates items to append

    Args:
        item_list (Dict[str, Any]): Items to append
        dal (DataAccessLayer): data access interface
        list_id (UUID): id of list
    Raises:
        HTTPException if list not found or error checking item length
    """
    try:
        list_to_append = await dal.get_existing_list_or_throw(list_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=LIST_ID_NOT_FOUND_ERROR_MSG
        )
    ensure_items_less_than_max(len(item_list), len(list_to_append.items))


# endregion
