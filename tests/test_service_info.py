from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.parametrize("endpoint", ["/_version", "/_version/"])
@patch("gen3datalibrary.routes.authorize_request")
def test_version(_, endpoint, client):
    """
    Test that the version endpoint returns a non-empty version
    """
    response = client.get(endpoint)
    response.raise_for_status()
    assert response
    assert response.json().get("version")


@pytest.mark.parametrize("endpoint", ["/_version", "/_version/"])
def test_version_no_token(endpoint, client):
    """
    Test that the version endpoint returns a 401 with details when no token is provided
    """
    response = client.get(endpoint)
    assert response
    assert response.status_code == 401
    assert response.json().get("detail")


@pytest.mark.parametrize("endpoint", ["/_version", "/_version/"])
@patch("gen3datalibrary.auth.arborist", new_callable=AsyncMock)
def test_version_unauthorized(arborist, endpoint, client):
    """
    Test accessing the endpoint when authorized
    """
    # Simulate an unauthorized request
    arborist.auth_request.return_value = False

    headers = {"Authorization": "Bearer ofbadnews"}
    response = client.get(endpoint, headers=headers)
    assert response.status_code == 403
    assert response.json().get("detail")


@pytest.mark.parametrize("endpoint", ["/_status", "/_status/"])
@patch("gen3datalibrary.routes.authorize_request")
def test_status(_, endpoint, client):
    """
    Test that the status endpoint returns a non-empty status
    """
    response = client.get(endpoint)
    response.raise_for_status()
    assert response
    assert response.json().get("status")


@pytest.mark.parametrize("endpoint", ["/_status", "/_status/"])
def test_status_no_token(endpoint, client):
    """
    Test that the status endpoint returns a 401 with details when no token is provided
    """
    response = client.get(endpoint)
    assert response
    assert response.status_code == 401
    assert response.json().get("detail")


@pytest.mark.parametrize("endpoint", ["/_status", "/_status/"])
@patch("gen3datalibrary.auth.arborist", new_callable=AsyncMock)
def test_status_unauthorized(arborist, endpoint, client):
    """
    Test accessing the endpoint when authorized
    """
    # Simulate an unauthorized request
    arborist.auth_request.return_value = False

    headers = {"Authorization": "Bearer ofbadnews"}
    response = client.get(endpoint, headers=headers)
    assert response.status_code == 403
    assert response.json().get("detail")
