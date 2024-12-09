"""
Endpoint to context is a static definition of information specific to endpoints used in
dependencies. For example, all endpoints need to authorize the user request, but the
specific resource in question is going to different between endpoints. To handle this,
we can designate a 'resource' key for that endpoint's function-specific use case.

Current recognized properties:
    resource: a descriptive resource path for authorize_request
    method: a description of the method type (e.g. read, write, ...)
    type: defines how to build the 'resource' path if it needs params
        - all: all lists, takes (user_id)
        - ID: by id, takes (user_id, list_id)
    items: defines how to extract the 'items' component from a request body
"""

from typing import Optional, Callable

from gen3userdatalibrary.auth import get_list_by_id_endpoint, get_lists_endpoint


def get_resource_from_endpoint_context(endpoint_context, user_id, path_params):
    """
    Before any endpoint is hit, we should verify that the requester has access to the endpoint.
    This middleware function handles that.

    Args:
        endpoint_context (Dict[str, Any]): information about an endpoint from the ENDPOINT_TO_CONTEXT data structure
        user_id (str): creator id
        path_params (dict): any params from the request scope

    Returns:
        The resource from endpoint_to_context based on the kind of endpoint
    """
    endpoint_type: Optional[str, None] = endpoint_context.get("type", None)
    get_resource: Optional[Callable, None] = endpoint_context.get("resource", None)
    if endpoint_type == "all":
        resource = get_resource(user_id)
    elif endpoint_type == "id":
        list_id = path_params["list_id"]
        resource = get_resource(user_id, list_id)
    else:  # None
        resource = get_resource
    return resource


identity = lambda P: P

ENDPOINT_TO_CONTEXT = {
    "redirect_to_docs": {
        "resource": "/gen3_user_data_library/service_info/redoc",
        "method": "read",
    },
    "get_version": {
        "resource": "/gen3_user_data_library/service_info/version",
        "method": "read",
    },
    "get_status": {
        "resource": "/gen3_user_data_library/service_info/status",
        "method": "read",
    },
    "read_all_lists": {
        "type": "all",
        "resource": get_lists_endpoint,
        "method": "read",
    },
    "upsert_user_lists": {
        "type": "all",
        "resource": get_lists_endpoint,
        "method": "update",
        "items": lambda body: list(
            map(lambda item_to_update: item_to_update["items"], body["lists"])
        ),
    },
    "delete_all_lists": {
        "type": "all",
        "resource": get_lists_endpoint,
        "method": "delete",
    },
    "get_list_by_id": {
        "type": "id",
        "resource": get_list_by_id_endpoint,
        "method": "read",
    },
    "update_list_by_id": {
        "type": "id",
        "resource": get_list_by_id_endpoint,
        "method": "update",
        "items": lambda b: b["items"],
    },
    "append_items_to_list": {
        "type": "id",
        "resource": get_list_by_id_endpoint,
        "method": "update",
        "items": identity,
    },
    "delete_list_by_id": {
        "type": "id",
        "resource": get_list_by_id_endpoint,
        "method": "delete",
    },
}
