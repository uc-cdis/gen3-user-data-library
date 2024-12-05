from unittest.mock import patch


import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials

from gen3userdatalibrary.auth import authorize_request

@pytest.mark.asyncio
@patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth._get_token", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.get_user_id", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.create_user_policy", new_callable=AsyncMock)
async def test_authorize_request_bypass_no_token(
    create_user_policy,
    get_user_id,
    _get_token,
    arborist,
    monkeypatch
):
    await authorize_request(authz_resources=["/example"])

    # No token or further checks should be performed
    _get_token.assert_not_called()
    get_user_id.assert_not_called()
    arborist.auth_request.assert_not_called()


@pytest.mark.asyncio
@patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth._get_token", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.get_user_id", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.create_user_policy", new_callable=AsyncMock)
async def test_authorize_request_token_not_provided(
    create_user_policy,
    get_user_id,
    _get_token,
    arborist,
    monkeypatch
):
    monkeypatch.setattr("gen3userdatalibrary.auth.config.DEBUG_SKIP_AUTH", False)
    _get_token.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await authorize_request(authz_resources=["/example"])

    assert exc_info.value.status_code == 401
    _get_token.assert_called_once()
    get_user_id.assert_not_called()
    arborist.auth_request.assert_not_called()



@pytest.mark.asyncio
@patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth._get_token", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.get_user_id", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.create_user_policy", new_callable=AsyncMock)
async def test_authorize_request_successful(
    create_user_policy,
    get_user_id,
    _get_token,
    arborist,
    monkeypatch
):
    monkeypatch.setattr("gen3userdatalibrary.auth.config.DEBUG_SKIP_AUTH", False)

    _get_token.return_value = HTTPAuthorizationCredentials(scheme="Bearer", credentials="mock-token")
    arborist.auth_request.return_value = True
    get_user_id.return_value = "foo"

    await authorize_request(authz_resources=["/example"])

    _get_token.assert_called_once()
    get_user_id.assert_called_once_with(_get_token.return_value, None)
    arborist.auth_request.assert_called_once_with(
        "mock-token",
        service="gen3_user_data_library",
        methods="access",
        resources=["/example"],
    )
    create_user_policy.assert_not_called()


@pytest.mark.asyncio
@patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth._get_token", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.get_user_id", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.get_username", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.create_user_policy", new_callable=AsyncMock)
async def test_authorize_request_retry_success(
    create_user_policy,
    get_username,
    get_user_id,
    _get_token,
    arborist,
    monkeypatch
):
    monkeypatch.setattr("gen3userdatalibrary.auth.config.DEBUG_SKIP_AUTH", False)

    _get_token.return_value = HTTPAuthorizationCredentials(scheme="Bearer", credentials="mock-token")
    arborist.auth_request.side_effect = [False, True]
    get_user_id.return_value = "foo"
    get_username.return_value = "bar"

    await authorize_request(authz_resources=["/example"])

    _get_token.assert_called_once()
    get_user_id.assert_called_once_with(_get_token.return_value, None)
    get_username.assert_called_once_with(_get_token.return_value, None)
    create_user_policy.assert_called_once_with(
        user_id="foo",
        username="bar",
        arborist_client=arborist,
    )
    assert arborist.auth_request.call_count == 2


@pytest.mark.asyncio
@patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth._get_token", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.get_user_id", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.get_username", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.create_user_policy", new_callable=AsyncMock)
async def test_authorize_request_retry_and_create_policy(
    create_user_policy,
    get_username,
    get_user_id,
    _get_token,
    arborist,
    monkeypatch
):
    monkeypatch.setattr("gen3userdatalibrary.auth.config.DEBUG_SKIP_AUTH", False)
    _get_token.return_value = HTTPAuthorizationCredentials(scheme="Bearer", credentials="mock-token")
    arborist.auth_request.return_value = False
    get_user_id.return_value = "foo"
    get_username.return_value = "bar"

    with pytest.raises(HTTPException) as exc_info:
        await authorize_request(authz_resources=["/example"])

    assert exc_info.value.status_code == 403
    _get_token.assert_called_once()
    get_user_id.assert_called_once_with(_get_token.return_value, None)
    get_username.assert_called_once_with(_get_token.return_value, None)
    create_user_policy.assert_called_once_with(
        user_id="foo",
        username="bar",
        arborist_client=arborist,
    )
    assert arborist.auth_request.call_count == 2

@pytest.mark.asyncio
@patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth._get_token", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.get_user_id", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.get_username", new_callable=AsyncMock)
@patch("gen3userdatalibrary.auth.create_user_policy", new_callable=AsyncMock)
async def test_authorize_request_retry_and_create_policy_fails(
    create_user_policy,
    get_username,
    get_user_id,
    _get_token,
    arborist,
    monkeypatch
):
    monkeypatch.setattr("gen3userdatalibrary.auth.config.DEBUG_SKIP_AUTH", False)
    _get_token.return_value = HTTPAuthorizationCredentials(scheme="Bearer", credentials="mock-token")
    arborist.auth_request.return_value = False
    get_user_id.return_value = "foo"
    get_username.return_value = "bar"

    with pytest.raises(HTTPException) as exc_info:
        await authorize_request(authz_resources=["/example"])

    assert exc_info.value.status_code == 403
    _get_token.assert_called_once()
    get_user_id.assert_called_once_with(_get_token.return_value, None)
    get_username.assert_called_once_with(_get_token.return_value, None)
    create_user_policy.assert_called_once_with(
        user_id="foo",
        username="bar",
        arborist_client=arborist,
    )
    assert arborist.auth_request.call_count == 2

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
