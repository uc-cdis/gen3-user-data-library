from sre_parse import parse

import pytest
from fastapi import Request
from fastapi.routing import APIRoute

from gen3userdatalibrary.routes import route_aggregator
from gen3userdatalibrary.services.helpers.dependencies import parse_and_auth_request
from tests.data.example_lists import VALID_LIST_A
from tests.routes.conftest import BaseTestRouter


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):
    router = route_aggregator

    async def test_all_endpoints_have_auth_dep(self, app_client_pair):
        app, client = app_client_pair
        api_routes = list(filter(lambda r: isinstance(r, APIRoute), app.routes))

        def route_has_no_dependencies(api_r: APIRoute):
            dependencies = api_r.dependant.dependencies
            return not any(dep.call == parse_and_auth_request
                           for dep in dependencies)

        routes_without_deps = list(filter(route_has_no_dependencies, api_routes))
        for route in routes_without_deps:
            assert False, f"Endpoint {route.path} is missing dependency_X"

    @pytest.mark.parametrize("user_list", [VALID_LIST_A])
    @pytest.mark.parametrize("endpoint", ["/_version", "/_version/",
                                          "/lists", "/lists/",
                                          "/lists/123e4567-e89b-12d3-a456-426614174000",
                                          "/lists/123e4567-e89b-12d3-a456-426614174000/"])
    async def test_auth_dep_get_hit(self,
                                    user_list,
                                    app_client_pair,
                                    endpoint):
        app, client_instance = app_client_pair

        class DependencyException(Exception):
            """A custom exception for specific error handling."""

            def __init__(self, message):
                self.message = message
                super().__init__(self.message)

        async def raises_mock(r: Request):
            raise DependencyException("Hit depedency")

        app.dependency_overrides[parse_and_auth_request] = raises_mock  # mock_auth
        with pytest.raises(DependencyException) as e:
            response = await client_instance.get(endpoint)
        del app.dependency_overrides[parse_and_auth_request]
