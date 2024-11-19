from unittest.mock import patch

import pytest
from fastapi import Request, Depends
from fastapi.routing import APIRoute

from gen3userdatalibrary.db import DataAccessLayer, get_data_access_layer
from gen3userdatalibrary.routes import route_aggregator
from gen3userdatalibrary.routes.dependencies import (
    parse_and_auth_request,
    validate_items,
)
from tests.data.example_lists import VALID_LIST_A, PATCH_BODY, VALID_LIST_B
from tests.routes.conftest import BaseTestRouter


class DependencyException(Exception):
    """A custom exception for specific error handling."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


async def raises_mock_simple(r: Request):
    raise DependencyException("Hit dependency")


async def raises_mock(r: Request, d: DataAccessLayer = Depends(DataAccessLayer)):
    raise DependencyException("Hit dependency")


def mock_items(r: Request, dal: DataAccessLayer = Depends(get_data_access_layer)):
    raise DependencyException("hit dep")


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):
    router = route_aggregator

    async def test_all_endpoints_have_auth_dep(self, app_client_pair):
        app, client = app_client_pair
        api_routes = list(filter(lambda r: isinstance(r, APIRoute), app.routes))

        def route_has_no_dependencies(api_r: APIRoute):
            dependencies = api_r.dependant.dependencies
            return not any(dep.call == parse_and_auth_request for dep in dependencies)

        routes_without_deps = list(filter(route_has_no_dependencies, api_routes))
        for route in routes_without_deps:
            assert False, f"Endpoint {route.path} is missing dependency_X"

    @pytest.mark.parametrize("user_list", [VALID_LIST_A])
    @pytest.mark.parametrize(
        "endpoint",
        [
            "/_version",
            "/_version/",
            "/lists",
            "/lists/",
            "/lists/123e4567-e89b-12d3-a456-426614174000",
            "/lists/123e4567-e89b-12d3-a456-426614174000/",
        ],
    )
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_auth_dep_get_validates_correctly(
        self,
        get_token_claims,
        user_list,
        app_client_pair,
        endpoint,
    ):
        # bonus: test auth request gets correct data instead of just getting hit
        app, client_instance = app_client_pair
        get_token_claims.return_value = {"sub": "foo"}
        app.dependency_overrides[parse_and_auth_request] = raises_mock_simple
        with pytest.raises(DependencyException) as e:
            response = await client_instance.get(endpoint)
        del app.dependency_overrides[parse_and_auth_request]

    @pytest.mark.parametrize("user_list", [VALID_LIST_A])
    @pytest.mark.parametrize(
        "endpoint",
        [
            "/lists/123e4567-e89b-12d3-a456-426614174000",
            "/lists/123e4567-e89b-12d3-a456-426614174000/",
        ],
    )
    async def test_middleware_patch_hit(self, user_list, app_client_pair, endpoint):
        app, client_instance = app_client_pair
        app.dependency_overrides[parse_and_auth_request] = raises_mock_simple
        headers = {"Authorization": "Bearer ofa.valid.token"}
        with pytest.raises(DependencyException) as e:
            response = await client_instance.patch(
                endpoint, headers=headers, json=PATCH_BODY
            )
        del app.dependency_overrides[parse_and_auth_request]

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @pytest.mark.parametrize(
        "endpoint",
        [
            "/lists",
            "/lists/",
            "/lists/123e4567-e89b-12d3-a456-426614174000",
            "/lists/123e4567-e89b-12d3-a456-426614174000/",
        ],
    )
    async def test_middleware_lists_put_hit(self, user_list, app_client_pair, endpoint):
        app, client_instance = app_client_pair
        app.dependency_overrides[parse_and_auth_request] = raises_mock_simple
        headers = {"Authorization": "Bearer ofa.valid.token"}
        with pytest.raises(DependencyException) as e:
            response = await client_instance.put(
                endpoint, headers=headers, json=PATCH_BODY
            )
        del app.dependency_overrides[parse_and_auth_request]

    @pytest.mark.parametrize("user_list", [VALID_LIST_A])
    @pytest.mark.parametrize(
        "endpoint",
        [
            "/lists",
            "/lists/",
            "/lists/123e4567-e89b-12d3-a456-426614174000",
            "/lists/123e4567-e89b-12d3-a456-426614174000/",
        ],
    )
    async def test_middleware_delete_hit(self, user_list, app_client_pair, endpoint):
        app, client_instance = app_client_pair
        app.dependency_overrides[parse_and_auth_request] = raises_mock_simple
        with pytest.raises(DependencyException) as e:
            response = await client_instance.delete(endpoint)
        del app.dependency_overrides[parse_and_auth_request]

    @pytest.mark.parametrize("user_list", [VALID_LIST_A])
    @pytest.mark.parametrize(
        "endpoint",
        [
            "/lists",
            "/lists/",
            "/lists/123e4567-e89b-12d3-a456-426614174000/",
            "/lists/123e4567-e89b-12d3-a456-426614174000",
        ],
    )
    async def test_max_items_put_dependency_success(
        self, user_list, app_client_pair, endpoint
    ):
        app, client_instance = app_client_pair

        app.dependency_overrides[parse_and_auth_request] = lambda r: Request({})
        app.dependency_overrides[validate_items] = mock_items
        headers = {"Authorization": "Bearer ofa.valid.token"}
        with pytest.raises(DependencyException) as e:
            response = await client_instance.put(endpoint, headers=headers)
        del app.dependency_overrides[parse_and_auth_request]

    @pytest.mark.parametrize("user_list", [VALID_LIST_A])
    @pytest.mark.parametrize(
        "endpoint",
        [
            "/lists/123e4567-e89b-12d3-a456-426614174000/",
            "/lists/123e4567-e89b-12d3-a456-426614174000",
        ],
    )
    async def test_max_items_patch_dependency_success(
        self, user_list, app_client_pair, endpoint
    ):
        app, client_instance = app_client_pair
        app.dependency_overrides[parse_and_auth_request] = lambda r: Request({})
        app.dependency_overrides[validate_items] = mock_items
        with pytest.raises(DependencyException) as e:
            response = await client_instance.patch(endpoint)
        del app.dependency_overrides[parse_and_auth_request]

    # todo: add max config tests
