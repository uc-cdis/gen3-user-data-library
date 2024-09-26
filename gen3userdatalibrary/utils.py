from functools import reduce
from typing import Any, Dict, List
from fastapi import FastAPI
from sqlalchemy import inspect

from gen3userdatalibrary import logging


def find_differences(list_to_update, new_list):
    """
    Finds differences in attributes between two SQLAlchemy ORM objects of the same type.
    """
    mapper = inspect(list_to_update).mapper

    def add_difference(differences, attribute):
        attr_name = attribute.key
        value1 = getattr(list_to_update, attr_name)
        value2 = getattr(new_list, attr_name)
        if value1 != value2:
            differences[attr_name] = (value1, value2)
        return differences

    differences_between_lists = reduce(add_difference, mapper.attrs, {})
    return differences_between_lists


def remove_keys(d: dict, keys: list):
    return {k: v for k, v in d.items() if k not in keys}


def add_user_list_metric(
        fastapi_app: FastAPI,
        action: str,
        user_lists: List[Dict[str, Any]],
        response_time_seconds: float,
        user_id: str) -> None:
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
    # todo: state property does not exist?
    if not getattr(fastapi_app.state, "metrics", None):
        return

    for user_list in user_lists:
        fastapi_app.state.metrics.add_user_list_counter(
            action=action, user_id=user_id, response_time_seconds=response_time_seconds)
        for item_id, item in user_list.get("items", {}).items():
            fastapi_app.state.metrics.add_user_list_item_counter(
                action=action,
                user_id=user_id,
                type=item.get("type", "Unknown"),
                schema_version=item.get("schema_version", "Unknown"),
                response_time_seconds=response_time_seconds,)


def get_from_cfg_metadata(
        field: str, metadata: Dict[str, Any], default: Any, type_: Any) -> Any:
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
