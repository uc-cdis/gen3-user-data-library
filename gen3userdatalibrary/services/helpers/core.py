"""
This is currently for any helpers that do work but don't fall under any files in this directory
"""
from collections import defaultdict
from functools import reduce


from gen3userdatalibrary.utils import find_differences, filter_keys, add_to_dict_set


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
