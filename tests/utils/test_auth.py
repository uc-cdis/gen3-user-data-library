from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.datastructures import Headers
from starlette.requests import Request

from gen3userdatalibrary import config, auth
from gen3userdatalibrary.auth import (
    _get_token,
    authorize_request,
)
from gen3userdatalibrary.main import route_aggregator
from tests.routes.conftest import BaseTestRouter


@pytest.mark.asyncio
class TestAuthRouter(BaseTestRouter):
    router = route_aggregator

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/lists",
            "/lists/",
            "/_version",
            "/_version/",
            "/_status",
            "/_status/",
        ],
    )
    async def test_debug_skip_auth_gets(self, monkeypatch, endpoint, client):
        """
        Test that DEBUG_SKIP_AUTH configuration allows access to endpoints without auth
        """
        headers = {"Authorization": "Bearer ofa.valid.token"}
        previous_config = config.DEBUG_SKIP_AUTH
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", True)
        response = await client.get(endpoint)
        assert str(response.status_code).startswith("20")
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)

    @pytest.mark.parametrize("token_param", [None, "something"])
    @pytest.mark.parametrize("request_param", [None, "something"])
    @patch("gen3userdatalibrary.auth.get_bearer_token", new_callable=AsyncMock)
    async def test_get_token(self, get_bearer_token, request_param, token_param):
        """
        Test helper function returns proper token
        """
        get_bearer_token.return_value = "parsed token from request"

        output = await _get_token(token_param, request_param)

        if token_param:
            assert output == token_param
        else:
            if request_param:
                assert output == "parsed token from request"
            else:
                assert output == token_param

    async def test_authorize_request(self, monkeypatch):
        example_creds = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="my_access_token"
        )
        example_request = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/example",
                "headers": Headers({"host": "127.0.0.1:8000"}).raw,
                "query_string": b"name=example",
                "client": ("127.0.0.1", 8000),
            }
        )
        with pytest.raises(HTTPException):
            outcome = await authorize_request(
                "access",
                ["/users/1/user-data-library/lists"],
                None,  # example_creds,
                example_request,
            )

    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    async def test_id(
        self,
        arborist,
        mocker,
    ):
        arborist.auth_request.return_value = True
        mock_token = mocker.patch(
            "gen3userdatalibrary.auth._get_token", new_callable=AsyncMock
        )
        mock_token.return_value = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="my_access_token"
        )
        mock_get_id = mocker.patch(
            "gen3userdatalibrary.auth.get_user_id", new_callable=AsyncMock
        )
        mock_get_id.return_value = "mock id"

        class MockException(Exception):
            pass

        mock_get_id.side_effect = MockException("mock throw")
        example_request = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/example",
                "headers": Headers({"host": "127.0.0.1:8000"}).raw,
                "query_string": b"name=example",
                "client": ("127.0.0.1", 8000),
            }
        )
        with pytest.raises(MockException):
            outcome = await auth.authorize_request(
                "access",
                ["/users/1/user-data-library/lists"],
                None,  # example_creds,
                example_request,
            )
        mock_get_id.side_effect = None

        class MockExceptionTwo(Exception):
            pass

        arborist.auth_request.side_effect = MockExceptionTwo("mock throw")
        with pytest.raises(HTTPException):
            outcome = await auth.authorize_request(
                "access",
                ["/users/1/user-data-library/lists"],
                None,
                example_request,
            )
        assert 1 == 1
