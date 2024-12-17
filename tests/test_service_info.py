from unittest.mock import AsyncMock, patch

import pytest

from gen3userdatalibrary.main import route_aggregator
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
