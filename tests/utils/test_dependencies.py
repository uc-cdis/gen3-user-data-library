from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from fastapi import Request, Depends, HTTPException
from fastapi.routing import APIRoute
from gen3authz.client.arborist.errors import ArboristError
from httpx import Headers
from starlette import status

from gen3userdatalibrary import config
from gen3userdatalibrary.db import DataAccessLayer, get_data_access_layer
from gen3userdatalibrary.routes import route_aggregator
from gen3userdatalibrary.routes.basic import PUBLIC_ROUTES
from gen3userdatalibrary.routes.injection_dependencies import (
    validate_items,
    validate_user_list_item,
    parse_and_auth_request,
    ensure_list_exists_and_items_less_than_max,
    ensure_user_exists,
)
from tests.data.example_lists import (
    VALID_LIST_A,
    PATCH_BODY,
    VALID_LIST_B,
    VALID_LIST_C,
    REPLACE_LIST_A,
    INVALID_LIST_B,
)
from tests.helpers import create_basic_list, get_id_from_response
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


def test_validate_user_list_item():
    with pytest.raises(HTTPException):
        outcome = validate_user_list_item({"type": "foo"})


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):
    router = route_aggregator

    async def test_all_endpoints_have_auth_dep(self, app_client_pair):
        """
        This test ensures that any new endpoints created are forced to have parse_and_auth_request
        as a dependency unless we deliberately set it otherwise (add it to whitelist)
        """
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

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_max_lists_against_two_different_users(
        self, get_token_claims, arborist, user_list, client, monkeypatch
    ):
        headers = {"Authorization": "Bearer ofa.valid.token"}
        previous_config = config.MAX_LISTS
        monkeypatch.setattr(config, "MAX_LISTS", 1)
        arborist.auth_request.return_value = True
        get_token_claims.return_value = {"sub": "1"}
        resp1 = await create_basic_list(
            arborist, get_token_claims, client, user_list, headers
        )
        resp2 = await client.put(
            "/lists", headers=headers, json={"lists": [VALID_LIST_C]}
        )
        assert resp2.status_code == 422
        resp3 = await client.put("/lists", headers=headers, json={"lists": [user_list]})
        assert resp3.status_code == 409
        monkeypatch.setattr(config, "MAX_LISTS", previous_config)

    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_max_items_dependency_failure(
        self, get_token_claims, arborist, client, endpoint, monkeypatch
    ):
        """
        Test that request fails citing too many items
        """
        previous_max_lists_config = config.MAX_LIST_ITEMS
        monkeypatch.setattr(config, "MAX_LIST_ITEMS", 1)
        get_token_claims.return_value = {"sub": "1"}
        headers = {"Authorization": "Bearer ofa.valid.token"}
        arborist.auth_request.return_value = True
        local_test_list = {
            "name": "õ(*&!@#)(*$%)() 2",
            "items": {
                "drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a64": {
                    "dataset_guid": "phs000001.v1.p1.c1",
                    "type": "GA4GH_DRS",
                },
                "drs://dg.TEST:3418077e-0779-4715-8195-7b60565172f5": {
                    "dataset_guid": "phs000002.v2.p2.c2",
                    "type": "GA4GH_DRS",
                },
            },
        }
        resp1 = await client.put(
            endpoint, headers=headers, json={"lists": [local_test_list]}
        )
        assert (
            resp1.status_code == 409
            and resp1.text == '{"detail":"Too many items in list"}'
        )
        monkeypatch.setattr(config, "MAX_LIST_ITEMS", previous_max_lists_config)

    @pytest.mark.parametrize("user_list", [VALID_LIST_A])
    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_max_lists_dependency_success(
        self,
        get_token_claims,
        arborist,
        user_list,
        app_client_pair,
        endpoint,
        monkeypatch,
    ):
        """
        Tests max lists config by adding lists for different users.
        """
        previous_max_lists_config = config.MAX_LISTS
        monkeypatch.setattr(config, "MAX_LISTS", 1)
        previous_skip_auth_config = config.DEBUG_SKIP_AUTH
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", False)

        app, test_client = app_client_pair
        app.state.arborist_client = AsyncMock()
        headers = {"Authorization": "Bearer ofa.valid.token"}
        arborist.auth_request.return_value = True
        arborist.create_user_if_not_exist.return_value = True

        # Add lists under user 1
        get_token_claims.return_value = {"sub": "1"}
        resp2 = await test_client.put(
            "/lists", headers=headers, json={"lists": [VALID_LIST_C]}
        )
        assert resp2.status_code == 201

        resp1 = await create_basic_list(
            arborist, get_token_claims, test_client, user_list, headers, "2"
        )

        # Add list under user 2
        get_token_claims.return_value = {"sub": "2"}
        test_list = {"name": user_list["name"], "items": VALID_LIST_C["items"]}
        resp3 = await test_client.put(
            "/lists", headers=headers, json={"lists": [test_list]}
        )
        assert resp3.status_code == 201
        monkeypatch.setattr(config, "MAX_LISTS", previous_max_lists_config)
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_skip_auth_config)

    @pytest.mark.parametrize("user_list", [VALID_LIST_A])
    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_max_lists_dependency_failure(
        self,
        get_token_claims,
        arborist,
        user_list,
        app_client_pair,
        endpoint,
        monkeypatch,
    ):
        app, test_client = app_client_pair
        app.state.arborist_client = AsyncMock()
        previous_skip_auth_config = config.DEBUG_SKIP_AUTH
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", False)
        previous_max_lists_config = config.MAX_LISTS
        monkeypatch.setattr(config, "MAX_LISTS", 1)

        # Test max lists for user 1
        headers = {"Authorization": "Bearer ofa.valid.token"}
        arborist.auth_request.return_value = True
        get_token_claims.return_value = {"sub": "1"}
        resp1 = await create_basic_list(
            arborist, get_token_claims, test_client, user_list, headers
        )
        resp2 = await test_client.put(
            "/lists", headers=headers, json={"lists": [VALID_LIST_B]}
        )
        assert resp1.status_code == 201 and resp2.status_code == 422
        assert resp2.json()["detail"] == "Max number of lists reached!"

        # Test max lists for user 2
        get_token_claims.return_value = {"sub": "2"}
        resp3 = await test_client.put(
            "lists", headers=headers, json={"lists": [user_list]}
        )
        resp4 = await test_client.put(
            "/lists", headers=headers, json={"lists": [VALID_LIST_C]}
        )
        assert resp3.status_code == 201 and resp4.status_code == 422
        assert resp4.json()["detail"] == "Max number of lists reached!"
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_skip_auth_config)
        monkeypatch.setattr(config, "MAX_LISTS", previous_max_lists_config)

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_validate_id(self, get_token_claims, arborist, user_list, client):
        """
        Test that validation recognizes uuid but not other string types
        """
        headers = {"Authorization": "Bearer ofa.valid.token"}
        arborist.auth_request.return_value = True
        get_token_claims.return_value = {"sub": "1"}
        l_id = "550e8400-e29b-41d4-a716-446655440000"
        resp_1 = await client.get(f"/lists/{l_id}", headers=headers)
        assert resp_1.status_code == 404
        l_id = "1"
        resp_2 = await client.get(f"/lists/{l_id}", headers=headers)
        assert resp_2.status_code == 422

    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_item_validation_update_and_create(
        self, get_token_claims, arborist, client
    ):
        headers = {"Authorization": "Bearer ofa.valid.token"}
        arborist.auth_request.return_value = True
        get_token_claims.return_value = {"sub": "1"}
        response1 = await client.put(
            "/lists", headers=headers, json={"lists": [VALID_LIST_A]}
        )
        response2 = await client.put(
            "/lists",
            headers=headers,
            json={"lists": [REPLACE_LIST_A, VALID_LIST_B, VALID_LIST_C]},
        )
        assert response2.status_code == 201

    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_appending_to_non_existent_list_fails(
        self, get_token_claims, arborist, client, mocker
    ):
        headers = {"Authorization": "Bearer ofa.valid.token"}
        arborist.auth_request.return_value = True
        get_token_claims.return_value = {"sub": "1"}
        response = await client.put(
            "/lists", headers=headers, json={"lists": [VALID_LIST_A]}
        )
        l_id = get_id_from_response(response)
        mocker.patch(
            "gen3userdatalibrary.routes.injection_dependencies.DataAccessLayer.get_existing_list_or_throw",
            side_effect=ValueError("mock exception"),
        )
        response = await client.patch(
            f"/lists/{l_id}",
            headers=headers,
            json=PATCH_BODY,
        )
        assert response.status_code == 404

    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_invalid_lists_to_create(
        self, get_token_claims, arborist, client, monkeypatch
    ):
        previous_config = config.DEBUG_SKIP_AUTH
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", False)
        headers = {"Authorization": "Bearer ofa.valid.token"}
        arborist.auth_request.return_value = True
        get_token_claims.return_value = {"sub": "1"}
        response = await client.put(
            "/lists", headers=headers, json={"lists": [INVALID_LIST_B]}
        )
        assert (
            response.status_code == 400
            and response.text == '{"detail":"No items provided for list for user: 1"}'
        )
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)

    async def test_ensure_list_exists_and_items_less_than_max(
        self, alt_session, mocker
    ):
        dal = DataAccessLayer(alt_session)
        with pytest.raises(HTTPException) as e:
            outcome = await ensure_list_exists_and_items_less_than_max(
                {}, dal, "550e8400-e29b-41d4-a716-446655440000"
            )
        assert e.value.status_code == status.HTTP_404_NOT_FOUND
        mocker.patch(
            "gen3userdatalibrary.routes.injection_dependencies.DataAccessLayer.get_existing_list_or_throw",
            side_effect=ArboristError(message="mock error", code=0),
        )
        with pytest.raises(HTTPException) as e2:
            outcome = await ensure_list_exists_and_items_less_than_max(
                {}, DataAccessLayer("abc"), "550e8400-e29b-41d4-a716-446655440000"
            )
        assert e2.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

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
        Test the auth dependency hits the correct auth function

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
    @patch("gen3userdatalibrary.routes.injection_dependencies.get_user_id")
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
