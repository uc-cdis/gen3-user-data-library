from functools import reduce
from typing import Any, Dict, List, Tuple

from fastapi import FastAPI
from sqlalchemy import inspect
from starlette.requests import Request

from gen3userdatalibrary import logging
from gen3userdatalibrary.models.user_list import UpdateItemsModel, ItemToUpdateModel

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


def add_user_list_metric(
    fastapi_app: Request,
    action: str,
    user_lists: List[ItemToUpdateModel],
    response_time_seconds: float,
    user_id: str,
) -> None:
    """
    Add a metric to the Metrics() instance on the specified FastAPI app for managing user lists.

    Args:
        fastapi_app (FastAPI): The FastAPI application instance where the metrics are being added, this
            assumes that the .state.metrics contains a Metrics() instance
        action (str): The action being performed (e.g., "CREATE", "READ", "UPDATE", "DELETE").
        user_lists (list): A list of dictionaries representing user lists. Each dictionary may contain
                      an "items" key with item details
        response_time_seconds (float): The response time in seconds for the action performed
        user_id (str): The identifier of the user associated with the action
    """
    if not getattr(fastapi_app.state, "metrics", None):
        return

    for user_list in user_lists:
        fastapi_app.state.metrics.add_user_list_counter(
            action=action, user_id=user_id, response_time_seconds=response_time_seconds
        )
        for item_id, item in (user_list.items or {}).items():
            fastapi_app.state.metrics.add_user_list_item_counter(
                action=action,
                user_id=user_id,
                type=item.get("type", "Unknown"),
                schema_version=item.get("schema_version", "Unknown"),
                response_time_seconds=response_time_seconds,
            )


def get_from_cfg_metadata(
    field: str, metadata: Dict[str, Any], default: Any, type_: Any
) -> Any:
    """
    Return `field` from `metadata` dict (or `default` if not available)
    and cast it to `type_`. If we cannot cast `default`, return as-is.

    Args:
        field (str): the desired metadata field (e.g. key) to retrieve
        metadata (dict): dictionary with key values
        default (Any): Any value to set if `field` is not available.
                     MUST be of type `type_`
        type_ (Any): any type, used to cast the `field` to the preferred type

    Returns:
        type_: the value from metadata (either casted `field` for `default`)
    """
    try:
        configured_value = type_(metadata.get(field, default))
    except (TypeError, ValueError):
        configured_value = default
        logging.error(
            f"invalid configuration: "
            f"{metadata.get(field)}. Cannot convert to {type_}. "
            f"Defaulting to {default} and continuing..."
        )
    return configured_value


def update(k, updater, dict_to_update):
    dict_to_update[k] = updater(dict_to_update[k])
    return dict_to_update
