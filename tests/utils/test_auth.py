from unittest.mock import AsyncMock, patch

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from starlette.requests import Request

from gen3userdatalibrary import config, auth
from gen3userdatalibrary.auth import (
    _get_token,
    authorize_request,
)
from gen3userdatalibrary.main import route_aggregator
from tests.routes.conftest import BaseTestRouter


@pytest.fixture
def mock_get_user_id(mocker):
    mock_user_id = mocker.patch(
        "gen3userdatalibrary.auth.get_user_id", new_callable=AsyncMock
    )
    mock_user_id.return_value = "mock_user_id"
    return mock_user_id


@pytest.fixture
def mock_alt_get_token(mocker):
    mock_token = mocker.patch(
        "gen3userdatalibrary.auth._alt_get_token", new_callable=AsyncMock
    )
    mock_token.return_value = "alt mock"
    return mock_token


@pytest.fixture
def mock_get_token(mocker):
    mock_token = mocker.patch(
        "gen3userdatalibrary.auth._get_token", new_callable=AsyncMock
    )
    mock_token.return_value = "normal mock"
    return mock_token


@pytest.fixture
def mock_both_token(mocker):
    mock_token = mocker.patch(
        "gen3userdatalibrary.auth._get_token", new_callable=AsyncMock
    )
    mock_token.return_value = "normal mock"
    alt_mock_token = mocker.patch(
        "gen3userdatalibrary.auth._alt_get_token", new_callable=AsyncMock
    )
    alt_mock_token.return_value = "alt mock"
    return mock_token, alt_mock_token


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

    async def test_id(
        self,
        mocker,
    ):
        mock_token = mocker.patch(
            "gen3userdatalibrary.auth._get_token", new_callable=AsyncMock
        )
        mock_token.return_value = "normal mock"
        alt_mock_token = mocker.patch(
            "gen3userdatalibrary.auth.get_user_id", new_callable=AsyncMock
        )
        alt_mock_token.return_value = "mock id"
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
        outcome = await auth.authorize_request(
            "access",
            ["/users/1/user-data-library/lists"],
            None,  # example_creds,
            example_request,
        )

        assert outcome is False
