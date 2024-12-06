import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field


class MetricModel(BaseModel):
    """A base class for metric models"""

    lists_added: Optional[int] = Field(description="Number of lists added", default=0)
    lists_updated: Optional[int] = Field(
        description="Number of lists updated", default=0
    )
    lists_deleted: Optional[int] = Field(
        description="Number of lists deleted", default=0
    )

    items_added: Optional[int] = Field(
        description="Total number of items added across all lists", default=0
    )
    items_updated: Optional[int] = Field(
        description="Total number of items updated across all lists", default=0
    )
    items_deleted: Optional[int] = Field(
        description="Total number of items deleted across all lists", default=0
    )


def update_user_list_metric(
    fastapi_app: FastAPI,
    user_id: int,
    lists_added: int = 0,
    lists_deleted: int = 0,
    items_added: int = 0,
    items_deleted: int = 0,
    **kwargs: Dict[str, Any],
) -> None:
    """
    Add a metric to the Metrics() instance on the specified FastAPI app for managing user lists.

    This method logs metrics related to the management of user lists, including the number of lists
    added, deleted, items added, and deleted, as well as the response time. It assumes that the .state.metrics
    contains a Metrics() instance.

    Args:
        fastapi_app (FastAPI): The FastAPI application instance where the metrics are being added.
        lists_added (int): The number of lists added during the action.
        lists_deleted (int): The number of lists deleted during the action.
        items_added (int): The number of items added during the action.
        items_deleted (int): The number of items deleted during the action.
        user_id (int): The identifier of the user associated with the action.

    Returns:
        None
    """
    if not getattr(fastapi_app.state, "metrics", None):
        return

    if lists_added:
        fastapi_app.state.metrics.handle_user_lists_gauge(
            value=lists_added,
            action="CREATE",
            user_id=user_id,
        )
    if lists_deleted:
        fastapi_app.state.metrics.handle_user_lists_gauge(
            value=lists_deleted,
            action="DELETE",
            user_id=user_id,
        )
    if items_added:
        fastapi_app.state.metrics.handle_user_items_gauge(
            value=items_added,
            action="CREATE",
            user_id=user_id,
        )
    if items_deleted:
        fastapi_app.state.metrics.handle_user_items_gauge(
            value=items_deleted,
            action="DELETE",
            user_id=user_id,
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
