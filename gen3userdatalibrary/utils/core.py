""" General purpose functions """

from functools import reduce
from logging import Logger
from typing import Dict, Tuple, Hashable, Any

from sqlalchemy import inspect


def log_user_data_library_api_call(logging: Logger, debug_log: str = None, **kwargs):
    """
    Logs a INFO level response from the Gen3 User Data Library in a standard format with the
    provided kwargs as CSV.

    Args:
        logging (Logger): the logger to use, must be provided for the context of the file that is actually logging.
            if we instantiated here, the log would look like it's coming from the utils file directly.
        debug_log (str): Optional debug log message
        **kwargs: Additional keyword arguments to include in the log message
    """
    log_message = f"Gen3 User Data Library API Call. "
    for kwarg, value in kwargs.items():
        log_message += f"{kwarg}={value}, "
    log_message = log_message.rstrip(", ")

    logging.info(log_message)

    if debug_log:
        logging.debug(f"{debug_log}")


def build_switch_case(cases: dict[Hashable, Any], default):
    """
    A primitive polyfill of pattern matching in python 3.10

    Args:
        cases (Dict[Hashable, Any]): any sort of k => v mapping
        default (Any): outcome if option not found

    Returns:
        f(k) => Union[v, default]
    """
    return lambda instance: cases.get(instance, default)


def mutate_keys(mutator, updated_user_lists: dict):
    """

    Args:
        mutator: function that takes a key k and return the key mutated in some way
        updated_user_lists: id => user_list dictionary

    Returns:

    """
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
