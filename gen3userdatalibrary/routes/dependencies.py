import json

from fastapi import HTTPException, Request, Depends
from jsonschema.validators import validate
from pydantic import ValidationError
from starlette import status

from gen3userdatalibrary import config
from gen3userdatalibrary.auth import get_user_id, authorize_request
from gen3userdatalibrary.db import get_data_access_layer, DataAccessLayer
from gen3userdatalibrary.models.data import endpoints_to_context
from gen3userdatalibrary.models.user_list import ItemToUpdateModel
from gen3userdatalibrary.utils.modeling import try_conforming_list


def validate_user_list_item(item_contents: dict):
    """
    Ensures that the item component of a user list has the correct setup for type property
    """
    content_type = item_contents.get("type", None)
    matching_schema = config.ITEM_SCHEMAS.get(content_type, None)
    if matching_schema is None:
        config.logging.error("No matching schema for type, aborting!")
        raise HTTPException(
            status_code=400, detail="No matching schema identified for items, aborting!"
        )
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
    resource = get_resource_from_endpoint_context(
        endpoint_context, user_id, path_params
    )
    auth_outcome = await authorize_request(
        request=request,
        authz_access_method=endpoint_context["method"],
        authz_resources=[resource],
    )


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


def conform_to_item_update(items_to_update_as_dict) -> ItemToUpdateModel:
    try:
        validated_data = ItemToUpdateModel(**items_to_update_as_dict)
        return validated_data
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad data structure, cannot process",
        )


async def validate_items(
    request: Request, dal: DataAccessLayer = Depends(get_data_access_layer)
):
    route_function = request.scope["route"].name
    endpoint_context = endpoints_to_context.get(route_function, {})
    conformed_body = json.loads(await request.body())
    user_id = await get_user_id(request=request)
    list_id = request["path_params"].get("ID", None)

    try:
        ensure_any_items_match_schema(endpoint_context, conformed_body)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail="Problem trying to validate body. Is your body formatted "
            "correctly?",
        )
    if route_function == "upsert_user_lists":
        raw_lists = conformed_body["lists"]
        new_lists_as_orm = [
            await try_conforming_list(user_id, conform_to_item_update(user_list))
            for user_list in raw_lists
        ]
        unique_list_identifiers = {
            (user_list.creator, user_list.name): user_list
            for user_list in new_lists_as_orm
        }
        lists_to_create, lists_to_update = await sort_lists_into_create_or_update(
            dal, unique_list_identifiers, new_lists_as_orm
        )
        for list_to_update in lists_to_update:
            identifier = (list_to_update.creator, list_to_update.name)
            new_version_of_list = unique_list_identifiers.get(identifier, None)
            assert new_version_of_list is not None
            ensure_items_less_than_max(
                len(new_version_of_list.items), len(list_to_update.items)
            )
        for item_to_create in lists_to_create:
            ensure_items_less_than_max(len(item_to_create.items))
    elif route_function == "append_items_to_list":
        try:
            list_to_append = await dal.get_existing_list_or_throw(list_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="ID not recognized!"
            )
        ensure_items_less_than_max(len(conformed_body), len(list_to_append.items))
    else:  # 'update_list_by_id'
        try:
            list_to_append = await dal.get_existing_list_or_throw(list_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="ID not recognized!"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Something went wrong while validating request!",
            )
        ensure_items_less_than_max(
            len(conformed_body["items"]), len(list_to_append.items)
        )


def ensure_items_less_than_max(number_of_new_items, existing_item_count=0):
    more_items_than_max = (
        existing_item_count + number_of_new_items > config.MAX_LIST_ITEMS
    )
    if more_items_than_max:
        raise HTTPException(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail="Too many items in list",
        )


async def validate_lists(
    request: Request, dal: DataAccessLayer = Depends(get_data_access_layer)
):
    user_id = await get_user_id(request=request)
    conformed_body = json.loads(await request.body())
    raw_lists = conformed_body["lists"]
    new_lists_as_orm = [
        await try_conforming_list(user_id, conform_to_item_update(user_list))
        for user_list in raw_lists
    ]
    unique_list_identifiers = {
        (user_list.creator, user_list.name): user_list for user_list in new_lists_as_orm
    }
    lists_to_create, lists_to_update = await sort_lists_into_create_or_update(
        dal, unique_list_identifiers, new_lists_as_orm
    )
    for item_to_create in lists_to_create:
        if len(item_to_create.items) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No items provided for list for user: {user_id}",
            )
        ensure_items_less_than_max(len(item_to_create.items))
    await dal.ensure_user_has_not_reached_max_lists(user_id, len(lists_to_create))


async def sort_lists_into_create_or_update(
    data_access_layer, unique_list_identifiers, new_lists_as_orm
):
    lists_to_update = await data_access_layer.grab_all_lists_that_exist(
        "name", list(unique_list_identifiers.keys())
    )
    set_of_existing_identifiers = set(
        map(lambda ul: (ul.creator, ul.name), lists_to_update)
    )
    lists_to_create = list(
        filter(
            lambda ul: (ul.creator, ul.name) not in set_of_existing_identifiers,
            new_lists_as_orm,
        )
    )
    return lists_to_create, lists_to_update
