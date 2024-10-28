from sre_parse import parse
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Request, Depends
from fastapi.routing import APIRoute

from gen3userdatalibrary import config
from gen3userdatalibrary.routes import route_aggregator
from gen3userdatalibrary.services.db import DataAccessLayer, get_data_access_layer
from gen3userdatalibrary.services.helpers.dependencies import parse_and_auth_request, \
    validate_items
from tests.data.example_lists import VALID_LIST_A, PATCH_BODY, VALID_LIST_B, VALID_LIST_C, VALID_LIST_D
from tests.helpers import create_basic_list
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
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_auth_dep_get_validates_correctly(self,
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
    @pytest.mark.parametrize("endpoint", ["/lists/123e4567-e89b-12d3-a456-426614174000",
                                          "/lists/123e4567-e89b-12d3-a456-426614174000/"])
    async def test_middleware_patch_hit(self,
                                        user_list,
                                        app_client_pair,
                                        endpoint):
        app, client_instance = app_client_pair
        app.dependency_overrides[parse_and_auth_request] = raises_mock_simple
        headers = {"Authorization": "Bearer ofa.valid.token"}
        with pytest.raises(DependencyException) as e:
            response = await client_instance.patch(endpoint, headers=headers, json=PATCH_BODY)
        del app.dependency_overrides[parse_and_auth_request]

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/",
                                          "/lists/123e4567-e89b-12d3-a456-426614174000",
                                          "/lists/123e4567-e89b-12d3-a456-426614174000/"])
    async def test_middleware_lists_put_hit(self,
                                            user_list,
                                            app_client_pair,
                                            endpoint):
        app, client_instance = app_client_pair
        app.dependency_overrides[parse_and_auth_request] = raises_mock_simple
        headers = {"Authorization": "Bearer ofa.valid.token"}
        with pytest.raises(DependencyException) as e:
            response = await client_instance.put(endpoint, headers=headers, json=PATCH_BODY)
        del app.dependency_overrides[parse_and_auth_request]

    @pytest.mark.parametrize("user_list", [VALID_LIST_A])
    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/",
                                          "/lists/123e4567-e89b-12d3-a456-426614174000",
                                          "/lists/123e4567-e89b-12d3-a456-426614174000/"])
    async def test_middleware_delete_hit(self,
                                         user_list,
                                         app_client_pair,
                                         endpoint):
        app, client_instance = app_client_pair
        app.dependency_overrides[parse_and_auth_request] = raises_mock_simple
        with pytest.raises(DependencyException) as e:
            response = await client_instance.delete(endpoint)
        del app.dependency_overrides[parse_and_auth_request]

    @pytest.mark.parametrize("user_list", [VALID_LIST_A])
    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/",
                                          "/lists/123e4567-e89b-12d3-a456-426614174000/",
                                          "/lists/123e4567-e89b-12d3-a456-426614174000"])
    async def test_max_items_put_dependency_success(self,
                                                    user_list,
                                                    app_client_pair,
                                                    endpoint):
        app, client_instance = app_client_pair

        app.dependency_overrides[parse_and_auth_request] = lambda r: Request({})
        app.dependency_overrides[validate_items] = mock_items
        headers = {"Authorization": "Bearer ofa.valid.token"}
        with pytest.raises(DependencyException) as e:
            response = await client_instance.put(endpoint, headers=headers)
        del app.dependency_overrides[parse_and_auth_request]

    @pytest.mark.parametrize("user_list", [VALID_LIST_A])
    @pytest.mark.parametrize("endpoint", [
        "/lists/123e4567-e89b-12d3-a456-426614174000/",
        "/lists/123e4567-e89b-12d3-a456-426614174000"])
    async def test_max_items_patch_dependency_success(self,
                                                      user_list,
                                                      app_client_pair,
                                                      endpoint):
        app, client_instance = app_client_pair
        app.dependency_overrides[parse_and_auth_request] = lambda r: Request({})
        app.dependency_overrides[validate_items] = mock_items
        with pytest.raises(DependencyException) as e:
            response = await client_instance.patch(endpoint)
        del app.dependency_overrides[parse_and_auth_request]

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_max_lists_against_two_different_users(self,
                                                         get_token_claims,
                                                         arborist,
                                                         user_list,
                                                         client):
        headers = {"Authorization": "Bearer ofa.valid.token"}
        config.MAX_LISTS = 1
        arborist.auth_request.return_value = True
        get_token_claims.return_value = {"sub": "1"}
        resp1 = await create_basic_list(arborist, get_token_claims, client, user_list, headers)
        resp2 = await client.put("/lists", headers=headers, json={"lists": [VALID_LIST_C]})
        assert resp2.status_code == 507
        resp3 = await create_basic_list(arborist, get_token_claims, client, user_list, headers, "2")
        assert resp3.status_code == 201
        config.MAX_LISTS = 12

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_max_items_dependency_failure(self,
                                                get_token_claims,
                                                user_list,
                                                client,
                                                endpoint):
        config.MAX_LIST_ITEMS = 1
        get_token_claims.return_value = {"sub": "1"}
        headers = {"Authorization": "Bearer ofa.valid.token"}
        resp1 = await client.put(endpoint, headers=headers, json={"lists": [user_list]})
        assert resp1.status_code == 507 and resp1.text == '{"detail":"Too many items in list"}'
        config.MAX_LIST_ITEMS = 24

    @pytest.mark.parametrize("user_list", [VALID_LIST_A])
    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_max_lists_dependency_success(self,
                                                get_token_claims,
                                                arborist,
                                                user_list,
                                                client,
                                                endpoint):
        headers = {"Authorization": "Bearer ofa.valid.token"}
        config.MAX_LISTS = 12
        arborist.auth_request.return_value = True
        resp1 = await create_basic_list(arborist, get_token_claims, client, user_list, headers)
        resp2 = await client.put("/lists", headers=headers, json={"lists": [VALID_LIST_C]})
        assert resp2.status_code == 201
        user_list["items"] = VALID_LIST_C["items"]
        resp3 = await client.put("/lists", headers=headers, json={"lists": [VALID_LIST_D]})
        assert resp3.status_code == 201

    @pytest.mark.parametrize("user_list", [VALID_LIST_A])
    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_max_lists_dependency_failure(self,
                                                get_token_claims,
                                                arborist,
                                                user_list,
                                                client,
                                                endpoint):
        headers = {"Authorization": "Bearer ofa.valid.token"}
        config.MAX_LISTS = 1
        arborist.auth_request.return_value = True
        get_token_claims.return_value = {"sub": "1"}
        resp1 = await create_basic_list(arborist, get_token_claims, client, user_list, headers)
        resp2 = await client.put("/lists", headers=headers, json={"lists": [VALID_LIST_B]})
        assert resp1.status_code == 201 and resp2.status_code == 507
        get_token_claims.return_value = {"sub": "2"}
        resp3 = await create_basic_list(arborist, get_token_claims, client, user_list, headers, user_id="2")
        resp4 = await client.put("/lists", headers=headers, json={"lists": [VALID_LIST_C]})
        assert resp3.status_code == 201 and resp4.status_code == 507
        config.MAX_LISTS = 12
