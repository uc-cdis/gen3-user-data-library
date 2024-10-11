from fastapi import APIRouter

from gen3userdatalibrary.routes.basic import basic_router
from gen3userdatalibrary.routes.lists import lists_router
from gen3userdatalibrary.routes.lists_by_id import lists_by_id_router

route_aggregator = APIRouter()

route_definitions = [(basic_router, "", ["Basic"]),
                     (lists_router, "/lists", ["Lists"]),
                     (lists_by_id_router, "/lists", ["ByID"])]

for router, prefix, tags in route_definitions:
    route_aggregator.include_router(router, prefix=prefix, tags=tags)
