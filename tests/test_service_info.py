from unittest.mock import AsyncMock, patch

import pytest

from gen3userdatalibrary.main import root_router
from tests.routes.conftest import BaseTestRouter


@pytest.mark.asyncio
class TestAuthRouter(BaseTestRouter):
    router = root_router

    @pytest.mark.parametrize("endpoint", ["/_version", "/_version/"])
    @patch("gen3userdatalibrary.routes.authorize_request")
    async def test_version(self, _, endpoint, client):
        """
        Test that the version endpoint returns a non-empty version
        """
        response = await client.get(endpoint)
        response.raise_for_status()
        assert response
        assert response.json().get("version")

    @pytest.mark.parametrize("endpoint", ["/_version", "/_version/"])
    async def test_version_no_token(self, endpoint, client):
        """
        Test that the version endpoint returns a 401 with details when no token is provided
        """
        response = await client.get(endpoint)
        assert response
        assert response.status_code == 401
        assert response.json().get("detail")

    @pytest.mark.parametrize("endpoint", ["/_version", "/_version/"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    async def test_version_unauthorized(self, arborist, endpoint, client):
        """
        Test accessing the endpoint when authorized
        """
        # Simulate an unauthorized request
        arborist.auth_request.return_value = False

        headers = {"Authorization": "Bearer ofbadnews"}
        response = await client.get(endpoint, headers=headers)
        assert response.status_code == 403
        assert response.json().get("detail")

    @pytest.mark.parametrize("endpoint", ["/_status", "/_status/"])
    @patch("gen3userdatalibrary.routes.authorize_request")
    async def test_status(self, _, endpoint, client):
        """
        Test that the status endpoint returns a non-empty status
        """
        response = await client.get(endpoint)
        response.raise_for_status()
        assert response
        assert response.json().get("status")

    @pytest.mark.parametrize("endpoint", ["/_status", "/_status/"])
    async def test_status_no_token(self, endpoint, client):
        """
        Test that the status endpoint returns a 401 with details when no token is provided
        """
        response = await client.get(endpoint)
        assert response
        assert response.status_code == 401
        assert response.json().get("detail")

    @pytest.mark.parametrize("endpoint", ["/_status", "/_status/"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    async def test_status_unauthorized(self, arborist, endpoint, client):
        """
        Test accessing the endpoint when authorized
        """
        # Simulate an unauthorized request
        arborist.auth_request.return_value = False

        headers = {"Authorization": "Bearer ofbadnews"}
        response = await client.get(endpoint, headers=headers)
        assert response.status_code == 403
        assert response.json().get("detail")
