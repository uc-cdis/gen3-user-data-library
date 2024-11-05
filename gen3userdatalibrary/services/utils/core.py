""" General purpose functions """

from functools import reduce
from typing import Dict, Tuple

from sqlalchemy import inspect

identity = lambda P: P


def mutate_keys(mutator, updated_user_lists: dict):
    return dict(map(lambda kvp: (mutator(kvp[0]), kvp[1]), updated_user_lists.items()))


def mutate_values(mutator, provided_dict: dict):
    return dict(map(lambda kvp: (kvp[0], mutator(kvp[1])), provided_dict.items()))


def filter_keys(filter_func, differences):
    return {k: v for k, v in differences.items() if filter_func(k, v)}


def reg_match_key(matcher, dictionary_to_match):
    """
    Matcher should be a boolean lambda. Expects a dictionary.
    Passes the key to the matcher, when a result is found, returns
    the kv pair back.
    """
    dict_contents = dictionary_to_match.items()
    for key, value in dict_contents:
        matches = matcher(key)
        if matches is not None:
            return key, value
    return None, {}


def add_to_dict_set(dict_list, key, value):
    """If I want to add to a default dict set, I want to append and then return the list"""
    dict_list[key].add(value)
    return dict_list


def map_values(mutator, keys_to_old_values: Dict):
    """Quick way to update dict values while preserving relationship"""
    return {key: mutator(value) for key, value in keys_to_old_values.items()}


def find_differences(
    object_to_update: object, new_object: object
) -> Dict[str, Tuple[str, str]]:
    """
    Finds differences in attributes between two objects
    NOTE: Objects must be of the same type!
    """
    mapper = inspect(object_to_update).mapper

    def add_difference(differences, attribute):
        attr_name = attribute.key
        value1 = getattr(object_to_update, attr_name)
        value2 = getattr(new_object, attr_name)
        if value1 != value2:
            differences[attr_name] = (value1, value2)
        return differences

    differences_between_lists = reduce(add_difference, mapper.attrs, {})
    return differences_between_lists


def remove_keys(d: dict, keys: set):
    """Given a dictionary d and set of keys k, remove all k in d"""
    return {k: v for k, v in d.items() if k not in keys}


def update(k, updater, dict_to_update):
    dict_to_update[k] = updater(dict_to_update[k])
    return dict_to_update
