import json
import re

from fastapi import Request, HTTPException

from gen3userdatalibrary.models.data import endpoints_to_context
from gen3userdatalibrary.services.auth import authorize_request, get_user_id
from gen3userdatalibrary.services.helpers import validate_user_list_item


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


def get_resource_from_endpoint_context(endpoint_context, user_id, matched_pattern, endpoint):
    """
    Before any endpoint is hit, we should verify that the requester has access to the endpoint.
    This middleware function handles that.
    """

    endpoint_type = endpoint_context.get("type", None)
    get_resource = endpoint_context.get("resource", None)
    if endpoint_type == "all":
        resource = get_resource(user_id)
    elif endpoint_type == "id":
        list_id = re.search(matched_pattern, endpoint).group(1)
        resource = get_resource(user_id, list_id)
    else:  # None
        resource = get_resource
    return resource


def ensure_any_items_match_schema(endpoint_context, conformed_body):
    item_dict = endpoint_context.get("items", lambda _: [])(conformed_body)
    body_type = type(item_dict)
    if body_type is list:
        for item_set in item_dict:
            for item_contents in item_set.values():
                validate_user_list_item(item_contents)
    else:  # assume dict
        for item_contents in item_dict.values():
            validate_user_list_item(item_contents)


async def handle_data_check_before_endpoint(request: Request):
    # WARNING: This design does not bode well. We should find a better way to derive
    # the matching endpoint they're trying to hit, if possible.
    # Otherwise, we may need to handle endpoints such
    # as `/abc/{param1}/def/{param2}?foo=bar&blah` which could be rough
    endpoint = request.scope["path"]
    method = request.method
    user_id = await get_user_id(request=request)

    def regex_matches_endpoint(endpoint_regex):
        return re.match(endpoint_regex, endpoint)

    matched_pattern, methods_at_endpoint = reg_match_key(regex_matches_endpoint,
                                                         endpoints_to_context)
    endpoint_context = methods_at_endpoint.get(method, {})
    if not endpoint_context:
        raise HTTPException(status_code=404, detail="Unrecognized endpoint, could not authenticate user!")
    resource = get_resource_from_endpoint_context(endpoint_context, user_id, matched_pattern, endpoint)
    auth_outcome = await authorize_request(request=request,
                                           authz_access_method=endpoint_context["method"],
                                           authz_resources=[resource])
    raw_body = await request.body()
    if bool(raw_body):
        conformed_body = json.loads(raw_body)
        try:
            ensure_any_items_match_schema(endpoint_context, conformed_body)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Problem trying to validate body. Is your body formatted "
                                                        "correctly?")


async def middleware_catcher(request: Request, call_next):
    """ Catch the request, pass it into the actual handler """
    await handle_data_check_before_endpoint(request)
    response = await call_next(request)
    # routes = request.scope['router'].routes
    # paths = [route
    #          for route in routes
    #          if route.endpoint == request.scope['endpoint']]
    # final_path = paths[0].path

    return response
