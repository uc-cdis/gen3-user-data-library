import re

from fastapi import Request, HTTPException

from gen3userdatalibrary.models.data import endpoint_method_to_access_method
from gen3userdatalibrary.services.auth import authorize_request, get_user_id


def reg_match_key(matcher, dictionary_to_match):
    for key, value in dictionary_to_match.items():
        matches = matcher(key)
        if matches is not None:
            return key, value
    return None


async def add_process_time_header(request: Request, call_next):
    # todo: test that this is called before every endpoint
    endpoint = "/lists/123e4567-e89b-12d3-a456-426614174000"  # /lists/  # request.scope["path"]
    method = request.method
    matched_pattern, methods_at_endpoint = reg_match_key(lambda endpoint_regex: re.match(endpoint_regex, endpoint),
                                                         endpoint_method_to_access_method)
    endpoint_auth_info = methods_at_endpoint.get(method, {})
    endpoint_type = endpoint_auth_info.get("type", None)
    get_resource = endpoint_auth_info.get("resource", None)
    user_id = await get_user_id(request=request)
    if endpoint_type == "all":
        resource = get_resource(user_id)
    elif endpoint_type == "id":
        list_id = re.search(matched_pattern, endpoint).group(1)
        resource = get_resource(user_id, list_id)
    else:  # None
        resource = get_resource

    if not endpoint_auth_info:
        raise HTTPException(status_code=404, detail="Unrecognized endpoint, could not authenticate user!")
    auth_outcome = await authorize_request(request=request,
                                           authz_access_method=endpoint_auth_info["method"],
                                           authz_resources=[resource])
    response = await call_next(request)
    return response
