from typing import Any, Dict

from gen3userdatalibrary import logging


def add_user_list_metric(fastapi_app, action, lists, response_time_seconds, user_id):
    """
    Add a metric to the Metrics() instance on the specified FastAPI app for managing user lists.

    # TODO

    Args:
        fastapi_app:
        action:
        lists:
        response_time_seconds:
        user_id:

    Returns:

    """
    for list in lists:
        fastapi_app.state.metrics.add_user_list_counter(
            action=action, user_id=user_id, response_time_seconds=response_time_seconds
        )
        for item_id, item in list.get("items", {}).items():
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
        default (?): Any value to set if `field` is not available.
                     MUST be of type `type_`
        type_ (?): any type, used to cast the `field` to the preferred type

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
