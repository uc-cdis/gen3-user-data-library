from unittest.mock import AsyncMock, patch

import pytest

from gen3userdatalibrary.routes import route_aggregator
from tests.routes.configs_for_test_routes import BaseTestRouter


@pytest.mark.asyncio
class TestAuthRouter(BaseTestRouter):
    router = route_aggregator

    @pytest.mark.parametrize("endpoint", ["/_version", "/_version/"])
    @patch("gen3userdatalibrary.routes.basic.authorize_request")
    async def test_version(self, auth_request, endpoint, client):
        """
        Test that the version endpoint returns a non-empty version
        """
        auth_request.return_value = True
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
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
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
    @patch("gen3userdatalibrary.routes.basic.authorize_request")
    async def test_status(self, auth_req, endpoint, client):
        """
        Test that the status endpoint returns a non-empty status
        """
        auth_req.return_value = True
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
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
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
