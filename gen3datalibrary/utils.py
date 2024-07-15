from typing import Any, Dict

from gen3datalibrary import logging
from gen3datalibrary.factory import Factory


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
