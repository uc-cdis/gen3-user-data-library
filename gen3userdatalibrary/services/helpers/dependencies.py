import json

from fastapi import HTTPException, Request
from jsonschema.validators import validate
from starlette import status

from gen3userdatalibrary import config
from gen3userdatalibrary.models.data import endpoints_to_context
from gen3userdatalibrary.services.auth import get_user_id, authorize_request


def validate_user_list_item(item_contents: dict):
    """
    Ensures that the item component of a user list has the correct setup for type property
    """
    content_type = item_contents.get("type", None)
    matching_schema = config.ITEM_SCHEMAS.get(content_type, None)
    if matching_schema is None:
        config.logging.error("No matching schema for type, aborting!")
        raise HTTPException(status_code=400, detail="No matching schema identified for items, aborting!")
    validate(instance=item_contents, schema=matching_schema)


def get_resource_from_endpoint_context(endpoint_context, user_id, path_params):
    """
    Before any endpoint is hit, we should verify that the requester has access to the endpoint.
    This middleware function handles that.
    """

    endpoint_type = endpoint_context.get("type", None)
    get_resource = endpoint_context.get("resource", None)
    if endpoint_type == "all":
        resource = get_resource(user_id)
    elif endpoint_type == "id":
        list_id = path_params["ID"]
        resource = get_resource(user_id, list_id)
    else:  # None
        resource = get_resource
    return resource


async def parse_and_auth_request(request: Request):
    user_id = await get_user_id(request=request)
    path_params = request.scope["path_params"]
    route_function = request.scope["route"].name
    endpoint_context = endpoints_to_context.get(route_function, {})
    resource = get_resource_from_endpoint_context(endpoint_context, user_id, path_params)
    auth_outcome = await authorize_request(request=request,
                                           authz_access_method=endpoint_context["method"],
                                           authz_resources=[resource])


def ensure_any_items_match_schema(endpoint_context, conformed_body):
    item_dict = endpoint_context.get("items", lambda _: [])(conformed_body)
    body_type = type(item_dict)
    if body_type is list:
        for item_set in item_dict:
            for item_contents in item_set.values():
                validate_user_list_item(item_contents)
    else:  # assume dict for now
        for item_contents in item_dict.values():
            validate_user_list_item(item_contents)


async def validate_items(request: Request):
    route_function = request.scope["route"].name
    endpoint_context = endpoints_to_context.get(route_function, {})
    conformed_body = json.loads(await request.body())
    try:
        ensure_any_items_match_schema(endpoint_context, conformed_body)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Problem trying to validate body. Is your body formatted "
                                                    "correctly?")
    # ensure_items_less_than_max(len(new_version_of_list.items.items()), len(list_to_update.items.items()))

    pass
    # raise NotImplemented


def ensure_items_less_than_max(number_of_new_items, existing_item_count=0):
    more_items_than_max = existing_item_count + number_of_new_items > config.MAX_LIST_ITEMS
    if more_items_than_max:
        raise HTTPException(status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
                            detail="Too many items in list")

