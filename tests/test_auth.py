import pytest
from unittest.mock import AsyncMock, patch
from fastapi.security import HTTPAuthorizationCredentials
from gen3authz.client.arborist.errors import ArboristError
from fastapi import HTTPException
from gen3userdatalibrary.auth import authorize_request, create_user_policy

@pytest.mark.asyncio
@patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth._get_token", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.get_user_id", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.get_username", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.create_user_policy", new_callable=AsyncMock)
async def test_authorize_request_bypass_no_token(
    mock_create_user_policy, mock_get_username, mock_get_user_id, mock_get_token, mock_arborist, monkeypatch
):
    """
    Test the bypass functionality when DEBUG_SKIP_AUTH is enabled and no token is provided.
    The function should bypass all authorization checks.
    """
    monkeypatch.setattr("gen3userdatalibrary.auth.config.DEBUG_SKIP_AUTH", True)

    await authorize_request(authz_resources=["/example"])

    mock_get_token.assert_not_called()
    mock_get_user_id.assert_not_called()
    mock_arborist.auth_request.assert_not_called()


@pytest.mark.asyncio
@patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth._get_token", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.get_user_id", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.get_username", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.create_user_policy", new_callable=AsyncMock)
async def test_authorize_request_token_not_provided(
    mock_create_user_policy, mock_get_username, mock_get_user_id, mock_get_token, mock_arborist, monkeypatch
):
    """
    Test when DEBUG_SKIP_AUTH is disabled and no token is provided.
    The function should raise an HTTP 401 error.
    """
    monkeypatch.setattr("gen3userdatalibrary.auth.config.DEBUG_SKIP_AUTH", False)
    mock_get_token.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await authorize_request(authz_resources=["/example"])

    assert exc_info.value.status_code == 401
    mock_arborist.auth_request.assert_not_called()


@pytest.mark.asyncio
@patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth._get_token", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.get_user_id", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.get_username", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.create_user_policy", new_callable=AsyncMock)
async def test_authorize_request_successful(
    mock_create_user_policy, mock_get_username, mock_get_user_id, mock_get_token, mock_arborist, monkeypatch
):
    """
    Test successful authorization when the user has access to their user's data library.
    """
    monkeypatch.setattr("gen3userdatalibrary.auth.config.DEBUG_SKIP_AUTH", False)
    mock_get_token.return_value = HTTPAuthorizationCredentials(scheme="Bearer", credentials="mock-token")
    mock_arborist.auth_request.return_value = True
    mock_get_user_id.return_value = "foo"
    mock_get_username.return_value = "bar"

    await authorize_request(authz_resources=["/example"])

    mock_arborist.auth_request.assert_called_once_with(
        "mock-token",
        service="gen3_user_data_library",
        methods="access",
        resources=["/example"],
    )
    mock_create_user_policy.assert_not_called()


@pytest.mark.asyncio
@patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth._get_token", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.get_user_id", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.get_username", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.create_user_policy", new_callable=AsyncMock)
async def test_authorize_request_retry_success(
    mock_create_user_policy, mock_get_username, mock_get_user_id, mock_get_token, mock_arborist, monkeypatch
):
    """
    Test lazily creating the policy to grant a user access to their user's data library when the user is
    denied access to their own data library.
    """
    monkeypatch.setattr("gen3userdatalibrary.auth.config.DEBUG_SKIP_AUTH", False)
    mock_get_token.return_value = HTTPAuthorizationCredentials(scheme="Bearer", credentials="mock-token")
    mock_arborist.auth_request.side_effect = [False, True]
    mock_get_user_id.return_value = "foo"
    mock_get_username.return_value = "bar"

    await authorize_request(authz_resources=["/example"])

    mock_create_user_policy.assert_called_once_with(
        user_id="foo",
        username="bar",
        arborist_client=mock_arborist,
    )
    assert mock_arborist.auth_request.call_count == 2


@pytest.mark.asyncio
@patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth._get_token", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.get_user_id", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.get_username", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.create_user_policy", new_callable=AsyncMock)
async def test_authorize_request_retry_failure(
    mock_create_user_policy, mock_get_username, mock_get_user_id, mock_get_token, mock_arborist, monkeypatch
):
    """
    Test when both initial and retry authorization attempts fail, raising an HTTP 403 error.

    See: test_authorize_request_retry_success
    """
    monkeypatch.setattr("gen3userdatalibrary.auth.config.DEBUG_SKIP_AUTH", False)
    mock_get_token.return_value = HTTPAuthorizationCredentials(scheme="Bearer", credentials="mock-token")
    mock_arborist.auth_request.side_effect = [False, False]
    mock_get_user_id.return_value = "foo"
    mock_get_username.return_value = "bar"

    with pytest.raises(HTTPException) as exc_info:
        await authorize_request(authz_resources=["/example"])

    assert exc_info.value.status_code == 403

    mock_create_user_policy.assert_called_once_with(
        user_id="foo",
        username="bar",
        arborist_client=mock_arborist,
    )
    assert mock_arborist.auth_request.call_count == 2


@pytest.mark.asyncio
@patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth._get_token", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.get_user_id", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.get_username", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.create_user_policy", new_callable=AsyncMock)
async def test_authorize_request_retry_policy_creation_error(
    mock_create_user_policy, mock_get_username, mock_get_user_id, mock_get_token, mock_arborist, monkeypatch
):
    """
    Test when policy creation fails due to an ArboristError, raising an HTTP 500 error.

    See: test_authorize_request_retry_success
    """
    monkeypatch.setattr("gen3userdatalibrary.auth.config.DEBUG_SKIP_AUTH", False)
    mock_get_token.return_value = HTTPAuthorizationCredentials(scheme="Bearer", credentials="mock-token")
    mock_arborist.auth_request.return_value = False
    mock_get_user_id.return_value = "foo"
    mock_get_username.return_value = "bar"
    mock_create_user_policy.side_effect = ArboristError("Error while creating policy in arborist", 500)

    with pytest.raises(HTTPException) as exc_info:
        await authorize_request(authz_resources=["/example"])

    assert exc_info.value.status_code == 500

    mock_create_user_policy.assert_called_once_with(
        user_id="foo",
        username="bar",
        arborist_client=mock_arborist,
    )
    mock_arborist.auth_request.assert_called_once()

@pytest.mark.asyncio
async def test_create_user_policy_resource_already_assigned(
    monkeypatch
):
    """
    Test that the function does nothing if the user already has the necessary resource assigned.
    """
    mock_arborist_client = AsyncMock()
    user_id = "test_user"
    username = "test_username"
    resource = "/users/test_user/user-data-library/lists"

    mock_arborist_client.list_resources_for_user.return_value = [resource]

    await create_user_policy(user_id, username, mock_arborist_client)

    mock_arborist_client.create_user_if_not_exist.assert_not_called()
    mock_arborist_client.update_resource.assert_not_called()
    mock_arborist_client.update_policy.assert_not_called()
    mock_arborist_client.grant_user_policy.assert_not_called()


@pytest.mark.asyncio
async def test_create_user_policy_create_resource_success(
    monkeypatch
):
    """
    Test that the function successfully creates a resource, policy, and grants it when the user doesn't have the resource.
    """
    mock_arborist_client = AsyncMock()
    user_id = "test_user"
    username = "test_username"
    resource = "/users/test_user/user-data-library/lists"

    mock_arborist_client.list_resources_for_user.return_value = []

    await create_user_policy(user_id, username, mock_arborist_client)

    mock_arborist_client.create_user_if_not_exist.assert_called_once_with(username)
    mock_arborist_client.update_resource.assert_called_once_with(
        path="/",
        resource_json={"name": resource, "description": f"Library for user_id {user_id}"},
        merge=True,
        create_parents=True,
    )
    mock_arborist_client.update_policy.assert_called_once_with(
        policy_id=user_id,
        policy_json={
            "id": user_id,
            "description": "policy created by gen3-user-data-library",
            "role_ids": ["create", "read", "update", "delete"],
            "resource_paths": [resource],
        },
        create_if_not_exist=True,
    )
    mock_arborist_client.grant_user_policy.assert_called_once_with(
        username=username, policy_id=user_id
    )


@pytest.mark.asyncio
async def test_create_user_policy_resource_creation_failure(
    monkeypatch
):
    """
    Test that the function raises an HTTP 500 error when resource creation fails.
    """
    mock_arborist_client = AsyncMock()
    user_id = "test_user"
    username = "test_username"
    resource = "/users/test_user/user-data-library/lists"

    mock_arborist_client.list_resources_for_user.return_value = []
    mock_arborist_client.update_resource.side_effect = ArboristError("Resource error", 500)

    with pytest.raises(Exception):
        await create_user_policy(user_id, username, mock_arborist_client)

    mock_arborist_client.update_resource.assert_called_once_with(
        path="/",
        resource_json={"name": resource, "description": f"Library for user_id {user_id}"},
        merge=True,
        create_parents=True,
    )
    mock_arborist_client.update_policy.assert_not_called()
    mock_arborist_client.grant_user_policy.assert_not_called()


@pytest.mark.asyncio
async def test_create_user_policy_policy_creation_failure(
    monkeypatch
):
    """
    Test that the function raises an HTTP 500 error when policy creation fails.
    """
    mock_arborist_client = AsyncMock()
    user_id = "test_user"
    username = "test_username"
    resource = "/users/test_user/user-data-library/lists"

    mock_arborist_client.list_resources_for_user.return_value = []
    mock_arborist_client.update_policy.side_effect = ArboristError("Policy error", 500)

    with pytest.raises(Exception):
        await create_user_policy(user_id, username, mock_arborist_client)

    mock_arborist_client.update_policy.assert_called_once_with(
        policy_id=user_id,
        policy_json={
            "id": user_id,
            "description": "policy created by gen3-user-data-library",
            "role_ids": ["create", "read", "update", "delete"],
            "resource_paths": [resource],
        },
        create_if_not_exist=True,
    )
    mock_arborist_client.grant_user_policy.assert_not_called()


@pytest.mark.asyncio
async def test_create_user_policy_grant_failure(monkeypatch):
    """
    Test that the function raises an HTTP 500 error when granting a policy fails.
    """
    mock_arborist_client = AsyncMock()
    user_id = "test_user"
    username = "test_username"
    resource = "/users/test_user/user-data-library/lists"

    mock_arborist_client.list_resources_for_user.return_value = []
    mock_arborist_client.grant_user_policy.side_effect = ArboristError("Grant error", 500)

    with pytest.raises(Exception):
        await create_user_policy(user_id, username, mock_arborist_client)

    mock_arborist_client.update_resource.assert_called_once_with(
        path="/",
        resource_json={"name": resource, "description": f"Library for user_id {user_id}"},
        merge=True,
        create_parents=True,
    )
    mock_arborist_client.update_policy.assert_called_once_with(
        policy_id=user_id,
        policy_json={
            "id": user_id,
            "description": "policy created by gen3-user-data-library",
            "role_ids": ["create", "read", "update", "delete"],
            "resource_paths": [resource],
        },
        create_if_not_exist=True,
    )
    mock_arborist_client.grant_user_policy.assert_called_once_with(
        username=username, policy_id=user_id
    )
