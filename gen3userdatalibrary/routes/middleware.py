import re

from fastapi import Request, HTTPException

from gen3userdatalibrary.models.data import endpoint_method_to_access_method
from gen3userdatalibrary.services.auth import authorize_request, get_user_id


def reg_match_key(matcher, dictionary_to_match):
    """
    Matcher should be a boolean lambda. Expects a dictionary.
    Passes the key to the matcher, when a result is found, returns
    the kv pair back.
    """
    for key, value in dictionary_to_match.items():
        matches = matcher(key)
        if matches is not None:
            return key, value
    return None


async def ensure_endpoint_authorized(request: Request):
    """
    Before any endpoint is hit, we should verify that the requester has access to the endpoint.
    This middleware function handles that.
    """
    endpoint = request.scope["path"]
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


async def middleware_catcher(request: Request, call_next):
    """ Catch the request, pass it into the auth checker """
    await ensure_endpoint_authorized(request)
    response = await call_next(request)
    return response
