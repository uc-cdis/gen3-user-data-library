import datetime
from collections import defaultdict
from functools import reduce
from http.client import responses

from fastapi import HTTPException
from jsonschema import ValidationError, validate
from sqlalchemy.exc import IntegrityError
from starlette import status

from gen3userdatalibrary.config import logging
from gen3userdatalibrary.models.items_schema import BLACKLIST, SCHEMA_RELATIONSHIPS
from gen3userdatalibrary.models.user_list import UserList
from gen3userdatalibrary.services.auth import get_lists_endpoint
from gen3userdatalibrary.utils import find_differences, remove_keys, add_to_dict_set


def derive_changes_to_make(list_to_update: UserList, new_list: UserList):
    """
    Given an old list and new list, gets the changes in the new list to be added
    to the old list
    """
    differences = find_differences(list_to_update, new_list)
    relevant_differences = remove_keys(differences, BLACKLIST)
    has_no_relevant_differences = not relevant_differences or (
            len(relevant_differences) == 1 and relevant_differences.__contains__("updated_time"))
    if has_no_relevant_differences:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing to update!")
    changes_to_make = {k: diff_tuple[1] for k, diff_tuple in relevant_differences.items()}
    return changes_to_make


async def try_conforming_list(user_id, user_list: dict) -> UserList:
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
        logging.debug(f"Invalid user-provided data when trying to create lists for user {user_id}.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid list information provided")
    except Exception as exc:
        logging.exception(f"Unknown exception {type(exc)} when trying to create lists for user {user_id}.")
        logging.debug(f"Details: {exc}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid list information provided")
    return list_as_orm


def validate_user_list_item(item_contents: dict):
    """
    Ensures that the item component of a user list has the correct setup for type property

    """
    # TODO THIS NEEDS TO BE CFG
    content_type = item_contents.get("type", None)
    matching_schema = SCHEMA_RELATIONSHIPS[content_type]
    validate(instance=item_contents, schema=matching_schema)
    if content_type is None:
        logging.warning("User-provided JSON is an unknown type. Creating anyway...")


async def create_user_list_instance(user_id, user_list: dict):
    """
    Creates a user list orm given the user's id and a dictionary representation.
    Tests the type
    Assumes user list is in the correct structure

    """
    assert user_id is not None, "User must have an ID!"
    now = datetime.datetime.now(datetime.timezone.utc)
    name = user_list.get("name", f"Saved List {now}")
    user_list_items = user_list.get("items", {})  # todo: what if they don't have any items?
    for item in user_list_items.values():
        validate_user_list_item(item)

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
