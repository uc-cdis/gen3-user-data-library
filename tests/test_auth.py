from unittest.mock import AsyncMock, patch
import pytest
from tests.routes.conftest import BaseTestRouter
from gen3userdatalibrary import config
from gen3userdatalibrary.auth import _get_token
from gen3userdatalibrary.main import root_router

@pytest.mark.asyncio
class TestAuthRouter(BaseTestRouter):
    router = root_router

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
    async def test_debug_skip_auth_gets(self, monkeypatch, client, endpoint):
        """
        Test that DEBUG_SKIP_AUTH configuration allows access to endpoints without auth
        """
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
