from unittest.mock import AsyncMock, patch

import pytest

VALID_SINGLE_LIST_BODY = {
    "lists": [
        {
            "name": "My Saved List 1",
            "items": {
                "drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a64": {
                    "dataset_guid": "phs000001.v1.p1.c1"
                },
                "CF_1": {
                    "name": "Cohort Filter 1",
                    "type": "Gen3GraphQL",
                    "schema_version": "c246d0f",
                    "data": {
                        "query": "query ($filter: JSON) { _aggregation { subject (filter: $filter) { file_count { histogram { sum } } } } }",
                        "variables": {
                            "filter": {
                                "AND": [
                                    {"IN": {"annotated_sex": ["male"]}},
                                    {"IN": {"data_type": ["Aligned Reads"]}},
                                    {"IN": {"data_format": ["CRAM"]}},
                                ]
                            }
                        },
                    },
                },
            },
        }
    ]
}


@pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
def test_lists_no_token(endpoint, client):
    """
    Test that the lists endpoint returns a 401 with details when no token is provided
    """
    response = client.post(endpoint, json=VALID_SINGLE_LIST_BODY)
    assert response
    assert response.status_code == 401
    assert response.json().get("detail")


@pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
@patch("gen3datalibrary.auth.arborist", new_callable=AsyncMock)
def test_lists_invalid_token(arborist, endpoint, client):
    """
    Test accessing the endpoint when the token provided is invalid
    """
    # Simulate an unauthorized request
    arborist.auth_request.return_value = False

    # not a valid token
    headers = {"Authorization": "Bearer ofbadnews"}

    response = client.post(endpoint, headers=headers, json=VALID_SINGLE_LIST_BODY)
    assert response.status_code == 401
    assert response.json().get("detail")


@pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
@patch("gen3datalibrary.auth.arborist", new_callable=AsyncMock)
@patch("gen3datalibrary.auth._get_token_claims")
def test_lists_unauthorized(get_token_claims, arborist, endpoint, client):
    """
    Test accessing the endpoint when unauthorized
    """
    # Simulate an unauthorized request but a valid token
    arborist.auth_request.return_value = False
    get_token_claims.return_value = {"sub": "foo"}

    headers = {"Authorization": "Bearer ofa.valid.token"}
    response = client.post(endpoint, headers=headers, json=VALID_SINGLE_LIST_BODY)
    assert response.status_code == 403
    assert response.json().get("detail")


@pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
@patch("gen3datalibrary.auth.arborist", new_callable=AsyncMock)
@patch("gen3datalibrary.auth._get_token_claims")
def test_create_single_valid_list(get_token_claims, arborist, endpoint, client):
    """
    Test FastAPI docs endpoints
    """
    # Simulate an authorized request and a valid token
    arborist.auth_request.return_value = True
    get_token_claims.return_value = {"sub": "foo", "otherstuff": "foobar"}

    headers = {"Authorization": "Bearer ofa.valid.token"}
    response = client.post(endpoint, headers=headers, json=VALID_SINGLE_LIST_BODY)

    assert response.status_code == 200
    assert "lists" in response.json()

    for user_list_id, user_list in response.json()["lists"].items():
        assert user_list["version"] == 0
        assert user_list["created_time"]
        assert user_list["updated_time"]
        assert user_list["created_time"] == user_list["updated_time"]
        # TODO more asserts