from unittest.mock import AsyncMock, patch

import pytest

from gen3userdatalibrary import config
from gen3userdatalibrary.main import route_aggregator
from gen3userdatalibrary.services.auth import _get_token
from tests.routes.conftest import BaseTestRouter


@pytest.mark.asyncio
class TestAuthRouter(BaseTestRouter):
    router = route_aggregator

    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/", "/_version", "/_version/", "/_status", "/_status/", ], )
    # @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    # @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_debug_skip_auth_gets(self,
                                        monkeypatch,
                                        # get_token_claims,
                                        # arborist,
                                        endpoint,
                                        app_client_pair):
        """
        Test that DEBUG_SKIP_AUTH configuration allows access to endpoints without auth
        """
        # arborist.auth_request.return_value = True
        headers = {"Authorization": "Bearer ofa.valid.token"}
        # get_token_claims.return_value = {"sub": "1", "otherstuff": "foobar"}
        previous_config = config.DEBUG_SKIP_AUTH
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", True)
        response = await app_client_pair.get(endpoint)
        assert str(response.status_code).startswith("20")
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)

    @pytest.mark.parametrize("token_param", [None, "something"])
    @pytest.mark.parametrize("request_param", [None, "something"])
    @patch("gen3userdatalibrary.services.auth.get_bearer_token", new_callable=AsyncMock)
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
