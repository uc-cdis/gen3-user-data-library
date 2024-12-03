from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from fastapi import Request, Depends, HTTPException
from fastapi.routing import APIRoute
from tests.data.example_lists import PATCH_BODY, VALID_LIST_A, VALID_LIST_B
from tests.routes.conftest import BaseTestRouter
from gen3authz.client.arborist.errors import ArboristError
from starlette.datastructures import Headers

from gen3userdatalibrary import config
from gen3userdatalibrary.db import DataAccessLayer, get_data_access_layer
from gen3userdatalibrary.routes import route_aggregator
from gen3userdatalibrary.routes.basic import PUBLIC_ROUTES
from gen3userdatalibrary.routes.dependencies import (
    parse_and_auth_request,
    validate_items,
    ensure_user_exists,
)


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

        def not_public_route(api_route):
            return api_route.path not in PUBLIC_ROUTES

        routes_that_should_have_deps = list(
            filter(not_public_route, routes_without_deps)
        )
        for route in routes_that_should_have_deps:
            assert False, f"Endpoint {route.path} is missing auth dependency!"

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
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_auth_dep_get_validates_correctly(
        self,
        get_token_claims,
        user_list,
        app_client_pair,
        endpoint,
    ):
        """
        Test the auth dependency validates correctly

        Args:
            get_token_claims:
            user_list:
            app_client_pair:
            endpoint:

        Returns:

        """
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

    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.routes.dependencies.get_user_id")
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_ensure_user_exists(
        self, arborist, get_token_claims, get_user_id, monkeypatch
    ):
        arborist.auth_request.return_value = True
        get_token_claims.return_value = {"sub": "0", "app": "foo"}
        get_user_id.return_value = "0"
        example_app = MagicMock()
        example_app.state.arborist_client.policies_not_exist.side_effect = Exception
        example_request = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/example",
                "headers": Headers({"host": "127.0.0.1:8000"}).raw,
                "query_string": b"name=example",
                "client": ("127.0.0.1", 8000),
                "app": example_app,
            }
        )

        previous_config = config.DEBUG_SKIP_AUTH
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", False)
        try:
            outcome = await ensure_user_exists(example_request)
        except HTTPException as e:
            assert e.status_code == 500 and e.detail == "Failed checking policy!"
        finally:
            example_app.state.arborist_client.policies_not_exist.side_effect = None
            monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)

        example_app.state.arborist_client.policies_not_exist.return_value = False
        example_app.state.arborist_client.create_policy.side_effect = ArboristError(
            message="fake error", code=0
        )

        previous_config = config.DEBUG_SKIP_AUTH
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", False)

        try:
            outcome = await ensure_user_exists(example_request)
        except HTTPException as e:
            assert (
                e.status_code == 500
                and e.detail == "Internal error creating a policy in arborist"
            )
        finally:
            monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)
