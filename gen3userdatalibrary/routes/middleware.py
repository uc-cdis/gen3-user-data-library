import re

from fastapi import Request, FastAPI, HTTPException

from gen3userdatalibrary.services.auth import authorize_request, get_user_data_library_endpoint

uuid4_regex_pattern = "[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"

endpoint_method_to_access_method = {
    "^/_version/?$": {"methods": {"GET": {"resource": "/gen3_data_library/service_info/version",
                                          "method": "read"}}},
    "^/_status/?$": {"methods": {"GET": {"resource": "/gen3_data_library/service_info/status",
                                         "method": "read"}}},
    "^/?$": {"methods": {"GET": {"resource": "/gen3_data_library/service_info/redoc",
                                 "method": "read"}}},
    "^/lists/?$": {"GET": "read", "PUT": "update", "DELETE": "delete"},
    f"^/lists/{uuid4_regex_pattern}/?$": {
        "methods": {"GET": {"resource": lambda user_id: get_user_data_library_endpoint(user_id),
                            "method": "read"},
                    "PUT": {"resource": lambda user_id: get_user_data_library_endpoint(user_id),
                            "method": "update"},
                    "PATCH": {"resource": lambda user_id: get_user_data_library_endpoint(user_id),
                              "method": "update"},
                    "DELETE": {"resource": lambda user_id: get_user_data_library_endpoint(user_id),
                               "method": "delete"}},
        }
}


def reg_match_key(matcher, dictionary_to_match):
    for key, value in dictionary_to_match.items():
        matches = matcher(key)
        if matches is not None:
            return value
    return None


async def add_process_time_header(request: Request, call_next):
    # todo: test that this is called before every endpoint
    endpoint = request.scope["path"]
    method = request.method
    methods_at_endpoint = reg_match_key(lambda endpoint_regex: re.match(endpoint_regex, endpoint),
                                        endpoint_method_to_access_method)
    access_method = methods_at_endpoint.get(method, None)
    if access_method is None:
        raise HTTPException(status_code=404, detail="Unrecognized endpoint, could not authenticate user!")
    auth_outcome = await authorize_request(request=request,
                                           authz_access_method=access_method,
                                           authz_resources=["/gen3_data_library/service_info/status"])
    response = await call_next(request)
    return response
