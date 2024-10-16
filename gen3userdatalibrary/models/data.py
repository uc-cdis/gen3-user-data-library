from gen3userdatalibrary.services.auth import get_lists_endpoint, get_list_by_id_endpoint
from gen3userdatalibrary.utils import identity

WHITELIST = {"items", "name"}

uuid4_regex_pattern = "([0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})"

recognized_endpoints_as_regex = {
    r"^/docs/?$",
    r"^/redoc/?$",
    r"^/_version/?$",
    r"^/_status/?$",
    r"^/?$",
    r"^/lists/?$",
    rf"^/lists/{uuid4_regex_pattern}/?$"}

endpoints_to_context = {
    r"^/docs/?$": {"GET": {"resource": "/gen3_data_library/service_info/docs",
                           "method": "read"}},
    r"^/redoc/?$": {"GET": {"resource": "/gen3_data_library/service_info/docs",
                            "method": "read"}},
    r"^/_version/?$": {"GET": {"resource": "/gen3_data_library/service_info/version",
                               "method": "read"}},
    r"^/_status/?$": {"GET": {"resource": "/gen3_data_library/service_info/status",
                              "method": "read"}},
    r"^/?$": {"GET": {"resource": "/gen3_data_library/service_info/redoc",
                      "method": "read"}},
    r"^/lists/?$": {
        "GET": {
            "type": "all",
            "resource": lambda user_id: get_lists_endpoint(user_id),
            "method": "read",
        },
        "PUT": {
            "type": "all",
            "resource": lambda user_id: get_lists_endpoint(user_id),
            "method": "update",
            "items": lambda b: list(map(lambda item_to_update: item_to_update["items"], b["lists"]))
        },
        "DELETE": {
            "type": "all",
            "resource": lambda user_id: get_lists_endpoint(user_id),
            "method": "delete"}},
    rf"^/lists/{uuid4_regex_pattern}/?$": {
        "GET": {
            "type": "id",
            "resource": lambda user_id, list_id: get_list_by_id_endpoint(user_id, list_id),
            "method": "read"},
        "PUT": {
            "type": "id",
            "resource": lambda user_id, list_id: get_list_by_id_endpoint(user_id, list_id),
            "method": "update",
            "items": lambda b: b["items"]
        },
        "PATCH": {
            "type": "id",
            "resource": lambda user_id, list_id: get_list_by_id_endpoint(user_id, list_id),
            "method": "update",
            "items": identity
        },
        "DELETE": {
            "type": "id",
            "resource": lambda user_id, list_id: get_list_by_id_endpoint(user_id, list_id),
            "method": "delete"}}}
