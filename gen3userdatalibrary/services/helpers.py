import datetime
import time
from collections import defaultdict
from functools import reduce
from itertools import count
from typing import List

from fastapi import HTTPException
from jsonschema import ValidationError, validate
from sqlalchemy.exc import IntegrityError
from starlette import status
from starlette.responses import JSONResponse

import gen3userdatalibrary.config as config
from gen3userdatalibrary.models.data import WHITELIST
from gen3userdatalibrary.models.user_list import UserList, ItemToUpdateModel
from gen3userdatalibrary.services.auth import get_lists_endpoint
from gen3userdatalibrary.utils import find_differences, add_to_dict_set


def ensure_items_less_than_max(number_of_new_items, existing_item_count=0):
    more_items_than_max = existing_item_count + number_of_new_items > config.MAX_LIST_ITEMS
    if more_items_than_max:
        raise HTTPException(status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
                            detail="Too many items in list")


def build_generic_500_response():
    return_status = status.HTTP_500_INTERNAL_SERVER_ERROR
    status_text = "UNHEALTHY"
    response = {"status": status_text, "timestamp": time.time()}
    return JSONResponse(status_code=return_status, content=response)


async def make_db_request_or_return_500(primed_db_query, fail_handler=build_generic_500_response):
    try:
        outcome = await primed_db_query()
        return True, outcome
    except Exception as e:
        outcome = fail_handler()
        return False, outcome


async def sort_persist_and_get_changed_lists(data_access_layer, raw_lists: List[ItemToUpdateModel], user_id):
    """
    Conforms and sorts lists into sets to be updated or created, persists them, and returns an
    id => list (as dict) relationship
    """
    new_lists_as_orm = [await try_conforming_list(user_id, user_list)
                        for user_list in raw_lists]
    unique_list_identifiers = {(user_list.creator, user_list.name): user_list for user_list in new_lists_as_orm}
    lists_to_update = await data_access_layer.grab_all_lists_that_exist("name", list(unique_list_identifiers.keys()))
    set_of_existing_identifiers = set(map(lambda ul: (ul.creator, ul.name), lists_to_update))
    lists_to_create = list(
        filter(lambda ul: (ul.creator, ul.name) not in set_of_existing_identifiers, new_lists_as_orm))
    updated_lists = []
    await data_access_layer.ensure_user_has_not_reached_max_lists(user_id, len(lists_to_create))
    for list_to_update in lists_to_update:
        identifier = (list_to_update.creator, list_to_update.name)
        new_version_of_list = unique_list_identifiers.get(identifier, None)
        assert new_version_of_list is not None
        ensure_items_less_than_max(len(new_version_of_list.items.items()), len(list_to_update.items.items()))
        changes_to_make = derive_changes_to_make(list_to_update, new_version_of_list)
        updated_list = await data_access_layer.update_and_persist_list(list_to_update.id, changes_to_make)
        updated_lists.append(updated_list)
    for list_to_create in lists_to_create:
        if len(list_to_create.items) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"No items provided for list to create: "
                                                                                f"{list_to_create.name}")

        if len(list_to_create.items.items()) > config.MAX_LIST_ITEMS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Too many items for list: "
                                                                                f"{list_to_create.name}")
        await data_access_layer.persist_user_list(user_id, list_to_create)
    response_user_lists = {}
    for user_list in (lists_to_create + updated_lists):
        response_user_lists[user_list.id] = user_list.to_dict()
        del response_user_lists[user_list.id]["id"]
    return response_user_lists


def filter_keys(filter_func, differences):
    return {k: v
            for k, v in differences.items()
            if filter_func(k, v)}


def derive_changes_to_make(list_to_update: UserList, new_list: UserList):
    """
    Given an old list and new list, gets the changes in the new list to be added
    to the old list
    """
    properties_to_old_new_difference = find_differences(list_to_update, new_list)
    relevant_differences = filter_keys(lambda k, _: k in WHITELIST,
                                       properties_to_old_new_difference)
    has_no_relevant_differences = not relevant_differences or (len(relevant_differences) == 1 and
                                                               relevant_differences.__contains__("updated_time"))
    if has_no_relevant_differences:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing to update!")
    property_to_change_to_make = {k: diff_tuple[1] for k, diff_tuple in relevant_differences.items()}
    return property_to_change_to_make


async def try_conforming_list(user_id, user_list: ItemToUpdateModel) -> UserList:
    """
    Handler for modeling endpoint data into a user list orm
    user_id: list creator's id
    user_list: dict representation of the user's list
    """
    try:
        list_as_orm = await create_user_list_instance(user_id, user_list)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="must provide a unique name")
    except ValidationError:
        config.logging.debug(f"Invalid user-provided data when trying to create lists for user {user_id}.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid list information provided")
    except Exception as exc:
        config.logging.exception(f"Unknown exception {type(exc)} when trying to create lists for user {user_id}.")
        config.logging.debug(f"Details: {exc}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid list information provided")
    return list_as_orm


def validate_user_list_item(item_contents: dict):
    """
    Ensures that the item component of a user list has the correct setup for type property
    """
    content_type = item_contents.get("type", None)
    matching_schema = config.ITEM_SCHEMAS.get(content_type, None)
    if matching_schema is None:
        config.logging.error("No matching schema for type, aborting!")
        raise HTTPException(status_code=400, detail="No matching schema identified for items, aborting!")
    validate(instance=item_contents, schema=matching_schema)


async def create_user_list_instance(user_id, user_list: ItemToUpdateModel):
    """
    Creates a user list orm given the user's id and a dictionary representation.
    Tests the type
    Assumes user list is in the correct structure

    """
    assert user_id is not None, "User must have an ID!"
    now = datetime.datetime.now(datetime.timezone.utc)
    name = user_list.name or f"Saved List {now}"
    user_list_items = user_list.items or {}

    new_list = UserList(version=0, creator=str(user_id),
                        # temporarily set authz without the list ID since we haven't created the list in the db yet
                        authz={"version": 0, "authz": [get_lists_endpoint(user_id)]}, name=name, created_time=now,
                        updated_time=now, items=user_list_items)
    return new_list


def map_creator_to_list_ids(lists: dict):
    add_id_to_creator = lambda mapping, id_list_pair: add_to_dict_set(mapping, id_list_pair[1]["creator"],
                                                                      id_list_pair[0])
    return reduce(add_id_to_creator, lists.items(), defaultdict(set))


def map_list_id_to_list_dict(new_user_lists):
    response_user_lists = {}
    for user_list in new_user_lists:
        response_user_lists[user_list.id] = user_list.to_dict()
        del response_user_lists[user_list.id]["id"]
    return response_user_lists


def mutate_keys(mutator, updated_user_lists: dict):
    return dict(map(lambda kvp: (mutator(kvp[0]), kvp[1]), updated_user_lists.items()))


def mutate_values(mutator, updated_user_lists: dict):
    return dict(map(lambda kvp: (kvp[0], mutator(kvp[1])), updated_user_lists.items()))
