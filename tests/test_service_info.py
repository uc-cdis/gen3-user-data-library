import json
from unittest.mock import AsyncMock, patch

import pytest
from starlette.exceptions import HTTPException

from gen3userdatalibrary.routes import route_aggregator
from tests.routes.conftest import BaseTestRouter


@pytest.mark.asyncio
class TestAuthRouter(BaseTestRouter):
    router = route_aggregator

    @pytest.mark.parametrize("endpoint", ["/_version", "/_version/"])
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
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
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_version_no_token(self, get_token_claims, arborist, endpoint, client):
        """
        Test that the version endpoint returns a 401 with details when no token is provided
        """
        arborist.auth_request.return_value = True
        get_token_claims.return_value = {"sub": "1", "otherstuff": "foobar"}
        response = await client.get(endpoint)
        assert response.status_code == 401

    @pytest.mark.parametrize(
        "endpoint", ["/_version", "/_version/", "/_status", "/_status/"]
    )
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_version_and_status_unauthorized(
        self, get_token_claims, arborist, endpoint, client
    ):
        """
        Test accessing the endpoint when authorized
        """
        # Simulate an unauthorized request
        arborist.auth_request.return_value = False
        get_token_claims.return_value = {"sub": "1", "otherstuff": "foobar"}
        headers = {"Authorization": "Bearer ofbadnews"}
        response = await client.get(endpoint, headers=headers)
        assert response.status_code == 403
        assert "Forbidden" in response.text

    @pytest.mark.parametrize("endpoint", ["/_status", "/_status/"])
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
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
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    async def test_status_no_token(self, arborist, endpoint, client):
        """
        Test that the status endpoint returns a 401 with details when no token is provided
        """
        arborist.auth_request.return_value = True
        headers = {"Authorization": "Bearer ofbadnews"}
        response = await client.get(endpoint, headers=headers)
        resp_text = json.loads(response.text)
        assert response.status_code == 401
        assert (
            resp_text["detail"]
            == "Could not verify, parse, and/or validate scope from provided access token."
        )
