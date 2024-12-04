from gen3userdatalibrary.auth import get_list_by_id_endpoint, get_lists_endpoint
from gen3userdatalibrary.utils.core import identity

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
