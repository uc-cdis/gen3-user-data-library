import json
import re

from fastapi import Request, HTTPException

from gen3userdatalibrary.models.data import endpoints_to_context
from gen3userdatalibrary.services.auth import authorize_request, get_user_id
from gen3userdatalibrary.services.helpers import validate_user_list_item


# def ensure_any_items_match_schema(endpoint_context, conformed_body):
#     item_dict = endpoint_context.get("items", lambda _: [])(conformed_body)
#     body_type = type(item_dict)
#     if body_type is list:
#         for item_set in item_dict:
#             for item_contents in item_set.values():
#                 validate_user_list_item(item_contents)
#     else:  # assume dict
#         for item_contents in item_dict.values():
#             validate_user_list_item(item_contents)


# async def handle_data_check_before_endpoint(request: Request):
#     # WARNING: This design does not bode well. We should find a better way to derive
#     # the matching endpoint they're trying to hit, if possible.
#     # Otherwise, we may need to handle endpoints such
#     # as `/abc/{param1}/def/{param2}?foo=bar&blah` which could be rough
#
#     if not endpoint_context:
#         raise HTTPException(status_code=404, detail="Unrecognized endpoint, could not authenticate user!")
#
#     raw_body = await request.body()
#     if bool(raw_body):
#         conformed_body = json.loads(raw_body)



# async def middleware_catcher(request: Request, call_next):
#     """ Catch the request, pass it into the actual handler """
#     # await handle_data_check_before_endpoint(request)
#     response = await call_next(request)
#     # routes = request.scope['router'].routes
#     # paths = [route
#     #          for route in routes
#     #          if route.endpoint == request.scope['endpoint']]
#     # final_path = paths[0].path
#
#     return response
