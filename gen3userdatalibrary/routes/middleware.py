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
    dict_contents = dictionary_to_match.items()
    for key, value in dict_contents:
        matches = matcher(key)
        if matches is not None:
            return key, value
    return None, {}


def ensure_endpoint_authorized(user_id, endpoint, method):
    """
    Before any endpoint is hit, we should verify that the requester has access to the endpoint.
    This middleware function handles that.
    """

    # WARNING: This design does not bode well. We should find a better way to derive
    # the matching endpoint they're trying to hit, if possible.
    # Otherwise, we may need to handle `/abc/def?foo=bar&blah` which could be rough

    def regex_matches_endpoint(endpoint_regex):
        return re.match(endpoint_regex, endpoint)

    matched_pattern, methods_at_endpoint = reg_match_key(regex_matches_endpoint,
                                                         endpoint_method_to_access_method)
    endpoint_auth_info = methods_at_endpoint.get(method, {})
    endpoint_type = endpoint_auth_info.get("type", None)
    get_resource = endpoint_auth_info.get("resource", None)
    if endpoint_type == "all":
        resource = get_resource(user_id)
    elif endpoint_type == "id":
        list_id = re.search(matched_pattern, endpoint).group(1)
        resource = get_resource(user_id, list_id)
    else:  # None
        resource = get_resource

    if not endpoint_auth_info:
        raise HTTPException(status_code=404, detail="Unrecognized endpoint, could not authenticate user!")
    return endpoint_auth_info, resource


async def middleware_catcher(request: Request, call_next):
    """ Catch the request, pass it into the auth checker """
    endpoint = request.scope["path"]
    method = request.method
    user_id = await get_user_id(request=request)
    endpoint_auth_info, resource = ensure_endpoint_authorized(user_id, endpoint, method)
    auth_outcome = await authorize_request(request=request,
                                           authz_access_method=endpoint_auth_info["method"],
                                           authz_resources=[resource])
    response = await call_next(request)
    return response
