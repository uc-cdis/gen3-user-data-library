from unittest.mock import AsyncMock, patch

import pytest

from gen3userdatalibrary.routes import route_aggregator
from tests.routes.conftest import BaseTestRouter


@pytest.mark.asyncio
class TestAuthRouter(BaseTestRouter):
    router = route_aggregator

    @pytest.mark.parametrize("endpoint", ["/_version", "/_version/"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_version(self, get_token_claims, arborist, endpoint, client):
        """
        Test that the version endpoint returns a non-empty version
        """
        arborist.auth_request.return_value = True
        headers = {"Authorization": "Bearer ofa.valid.token"}
        get_token_claims.return_value = {"sub": "1", "otherstuff": "foobar"}
        response = await client.get(endpoint, headers=headers)
        response.raise_for_status()
        assert response
        assert response.json().get("version")

    @pytest.mark.parametrize("endpoint", ["/_version", "/_version/"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    @pytest.mark.skip(reason="No auth expected")
    async def test_version_no_token(
        self,
        get_token_claims,
        arborist,
        endpoint,
        client,
        monkeypatch,
    ):
        """
        Test that the version endpoint returns a 401 with details when no token is provided
        """
        # basic methods were decided to not have authorization
        pass
        # previous_config = config.DEBUG_SKIP_AUTH
        # monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", False)
        # # arborist.auth_request.return_value = True
        # get_token_claims.return_value = {"sub": "1"}
        # response = await client.get(endpoint)
        # assert response.status_code == 401
        # monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)

    @pytest.mark.parametrize(
        "endpoint", ["/_version", "/_version/", "/_status", "/_status/"]
    )
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    @pytest.mark.skip(reason="No auth needed to access endpoints")
    async def test_version_and_status_unauthorized(
        self, get_token_claims, arborist, endpoint, client, monkeypatch
    ):
        """
        Test accessing the endpoint when authorized
        """
        pass
        # Simulate an unauthorized request
        # previous_config = config.DEBUG_SKIP_AUTH
        # monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", False)
        # arborist.auth_request.return_value = False
        # get_token_claims.return_value = {"sub": "1", "otherstuff": "foobar"}
        # headers = {"Authorization": "Bearer ofbadnews"}
        # response = await client.get(endpoint, headers=headers)
        # assert response.status_code == 403
        # assert "Forbidden" in response.text
        # monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)

    @pytest.mark.parametrize("endpoint", ["/_status", "/_status/"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_status(self, get_token_claims, arborist, endpoint, client):
        """
        Test that the status endpoint returns a non-empty status
        """
        arborist.auth_request.return_value = True
        headers = {"Authorization": "Bearer ofa.valid.token"}
        get_token_claims.return_value = {"sub": "1", "otherstuff": "foobar"}
        response = await client.get(endpoint, headers=headers)
        response.raise_for_status()
        assert response
        assert response.json().get("status")

    @pytest.mark.parametrize("endpoint", ["/_status", "/_status/"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @pytest.mark.skip(reason="No auth needed to access these endpoints")
    async def test_status_no_token(
        self,
        arborist,
        endpoint,
        client,
        monkeypatch,
    ):
        """
        Test that the status endpoint returns a 401 with details when no token is provided
        """
        pass
        # previous_config = config.DEBUG_SKIP_AUTH
        # monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", False)
        # arborist.auth_request.return_value = True
        # headers = {"Authorization": "Bearer ofbadnews"}
        # response = await client.get(endpoint, headers=headers)
        # resp_text = json.loads(response.text)
        # assert response.status_code == 401
        # assert (
        #     resp_text.get("detail", None)
        #     == "Could not verify, parse, and/or validate scope from provided access token."
        # )
        # monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)
