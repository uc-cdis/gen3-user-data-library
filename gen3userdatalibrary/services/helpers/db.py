from typing import List

from fastapi import HTTPException
from starlette import status

from gen3userdatalibrary import config
from gen3userdatalibrary.models.data import WHITELIST
from gen3userdatalibrary.models.user_list import ItemToUpdateModel, UserList
from gen3userdatalibrary.services.helpers.modeling import try_conforming_list
from gen3userdatalibrary.utils import find_differences, filter_keys


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


async def sort_persist_and_get_changed_lists(data_access_layer, raw_lists: List[ItemToUpdateModel], user_id):
    """
    Conforms and sorts lists into sets to be updated or created, persists them, and returns an
    id => list (as dict) relationship
    """
    new_lists_as_orm = [await try_conforming_list(user_id, user_list)
                        for user_list in raw_lists]
    unique_list_identifiers = {(user_list.creator, user_list.name): user_list for user_list in new_lists_as_orm}
    lists_to_create, lists_to_update = await sort_lists_into_create_or_update(data_access_layer,
                                                                              unique_list_identifiers,
                                                                              new_lists_as_orm)
    updated_lists = []
    for list_to_update in lists_to_update:
        identifier = (list_to_update.creator, list_to_update.name)
        new_version_of_list = unique_list_identifiers.get(identifier, None)
        assert new_version_of_list is not None
        changes_to_make = derive_changes_to_make(list_to_update, new_version_of_list)
        updated_list = await data_access_layer.update_and_persist_list(list_to_update.id, changes_to_make)
        updated_lists.append(updated_list)
    for list_to_create in lists_to_create:
        if len(list_to_create.items) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"No items provided for list to create: {list_to_create.name}")

        if len(list_to_create.items.items()) > config.MAX_LIST_ITEMS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Too many items for list: "
                                                                                f"{list_to_create.name}")
        await data_access_layer.persist_user_list(user_id, list_to_create)
    response_user_lists = {}
    for user_list in (lists_to_create + updated_lists):
        response_user_lists[user_list.id] = user_list.to_dict()
        del response_user_lists[user_list.id]["id"]
    return response_user_lists


async def sort_lists_into_create_or_update(data_access_layer, unique_list_identifiers, new_lists_as_orm):
    lists_to_update = await data_access_layer.grab_all_lists_that_exist("name", list(unique_list_identifiers.keys()))
    set_of_existing_identifiers = set(map(lambda ul: (ul.creator, ul.name), lists_to_update))
    lists_to_create = list(
        filter(lambda ul: (ul.creator, ul.name) not in set_of_existing_identifiers, new_lists_as_orm))
    return lists_to_create, lists_to_update
