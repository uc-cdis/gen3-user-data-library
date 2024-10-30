from gen3userdatalibrary.services.auth import (
    get_lists_endpoint,
    get_list_by_id_endpoint,
)
from gen3userdatalibrary.utils import identity

WHITELIST = {"items", "name"}

uuid4_regex_pattern = (
    "([0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})"
)

recognized_endpoint_functions = {
    "redirect_to_docs",
    "get_version",
    "get_status",
    "read_all_lists",
    "upsert_user_lists",
    "delete_all_lists",
    "get_list_by_id",
    "update_list_by_id",
    "append_items_to_list",
    "delete_list_by_id",
}

endpoints_to_context = {
    "redirect_to_docs": {
        "resource": "/gen3_data_library/service_info/redoc",
        "method": "read",
    },
    "get_version": {
        "resource": "/gen3_data_library/service_info/version",
        "method": "read",
    },
    "get_status": {
        "resource": "/gen3_data_library/service_info/status",
        "method": "read",
    },
    "read_all_lists": {
        "type": "all",
        "resource": lambda user_id: get_lists_endpoint(user_id),
        "method": "read",
    },
    "upsert_user_lists": {
        "type": "all",
        "resource": lambda user_id: get_lists_endpoint(user_id),
        "method": "update",
        "items": lambda body: list(
            map(lambda item_to_update: item_to_update["items"], body["lists"])
        ),
    },
    "delete_all_lists": {
        "type": "all",
        "resource": lambda user_id: get_lists_endpoint(user_id),
        "method": "delete",
    },
    "get_list_by_id": {
        "type": "id",
        "resource": lambda user_id, list_id: get_list_by_id_endpoint(user_id, list_id),
        "method": "read",
    },
    "update_list_by_id": {
        "type": "id",
        "resource": lambda user_id, list_id: get_list_by_id_endpoint(user_id, list_id),
        "method": "update",
        "items": lambda b: b["items"],
    },
    "append_items_to_list": {
        "type": "id",
        "resource": lambda user_id, list_id: get_list_by_id_endpoint(user_id, list_id),
        "method": "update",
        "items": identity,
    },
    "delete_list_by_id": {
        "type": "id",
        "resource": lambda user_id, list_id: get_list_by_id_endpoint(user_id, list_id),
        "method": "delete",
    },
}
