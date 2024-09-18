from unittest.mock import AsyncMock, patch
import ast
import pytest

from gen3userdatalibrary.auth import get_list_by_id_endpoint
from tests.routes.conftest import BaseTestRouter

from gen3userdatalibrary.main import root_router

VALID_LIST_A = {
    "name": "My Saved List 1",
    "items": {
        "drs://dg.4503:943201c3-271d-4a04-a2b6-040272239a64": {
            "dataset_guid": "phs000001.v1.p1.c1",
            "type": "GA4GH_DRS",
        },
        "CF_1": {
            "name": "Cohort Filter 1",
            "type": "Gen3GraphQL",
            "schema_version": "c246d0f",
            "data": {
                "query": "query ($filter: JSON) { _aggregation { subject (filter: $filter) "
                         "{ file_count { histogram { sum } } } } }",
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

VALID_LIST_B = {
    "name": "õ(*&!@#)(*$%)() 2",
    "items": {
        "CF_1": {
            "name": "Some cohort I made with special characters: !@&*(#)%$(*&.?:<>õ",
            "type": "Gen3GraphQL",
            "schema_version": "aacc222",
            "data": {
                "query": "query ($filter: JSON,) {\n"
                         "    subject (accessibility: accessible, offset: 0, first: 20, , filter: $filter,) {\n"
                         "      \n    project_id\n    \n\n    data_format\n    \n\n    race\n    \n\n"
                         "    annotated_sex\n    \n\n    ethnicity\n    \n\n    hdl\n    \n\n    ldl\n    \n    }\n"
                         "    _aggregation {\n      subject (filter: $filter, accessibility: accessible) {\n"
                         "        _totalCount\n      }\n    }\n  }",
                "variables": {
                    "filter": {
                        "AND": [
                            {"IN": {"project_id": ["tutorial-synthetic_data_set_1"]}},
                            {"IN": {"data_type": ["Aligned Reads"]}},
                        ]
                    }
                },
            },
        },
        "drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a64": {
            "dataset_guid": "phs000001.v1.p1.c1",
            "type": "GA4GH_DRS",
        },
        "drs://dg.TEST:3418077e-0779-4715-8195-7b60565172f5": {
            "dataset_guid": "phs000002.v2.p2.c2",
            "type": "GA4GH_DRS",
        },
        "drs://dg.4503:edbb0398-fcff-4c92-b908-9e650e0a6eb5": {
            "dataset_guid": "phs000002.v2.p2.c1",
            "type": "GA4GH_DRS",
        },
    },
}

VALID_MULTI_LIST_BODY = {"lists": [VALID_LIST_A, VALID_LIST_B]}


@pytest.mark.asyncio
class TestUserListsRouter(BaseTestRouter):
    router = root_router

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    async def test_lists_no_token(self, endpoint, user_list, client):
        """
        Test that the lists endpoint returns a 401 with details when no token is provided
        """
        valid_single_list_body = {"lists": [user_list]}
        response = await client.put(endpoint, json=valid_single_list_body)
        assert response
        assert response.status_code == 401
        assert response.json().get("detail")

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    async def test_lists_invalid_token(self, arborist, endpoint, user_list, client):
        """
        Test accessing the endpoint when the token provided is invalid
        """
        # Simulate an unauthorized request
        arborist.auth_request.return_value = False

        # not a valid token
        headers = {"Authorization": "Bearer ofbadnews"}

        response = await client.put(endpoint, headers=headers, json={"lists": [user_list]})
        assert response.status_code == 401
        assert response.json().get("detail")

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @pytest.mark.parametrize("method", ["put", "get", "delete"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_create_lists_unauthorized(self, get_token_claims, arborist,
                                             method, user_list, endpoint, client):
        """
        Test accessing the endpoint when unauthorized
        """
        # Simulate an unauthorized request but a valid token
        arborist.auth_request.return_value = False
        get_token_claims.return_value = 0

        headers = {"Authorization": "Bearer ofa.valid.token"}
        if method == "post":
            response = await client.post(
                endpoint, headers=headers, json={"lists": [user_list]})
        elif method == "get":
            response = await client.get(endpoint, headers=headers)
        elif method == "put":
            response = await client.put(
                endpoint, headers=headers, json={"lists": [user_list]})
        elif method == "delete":
            response = await client.delete(endpoint, headers=headers)
        else:
            response = None

        assert response
        assert response.status_code == 403
        assert response.json().get("detail")

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_create_single_valid_list(self, get_token_claims, arborist,
                                            endpoint, user_list, client, session):
        """
        Test the response for creating a single valid list
        """
        # Simulate an authorized request and a valid token
        arborist.auth_request.return_value = True
        user_id = {"name": "example_user", "id": 79}
        get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}

        headers = {"Authorization": "Bearer ofa.valid.token"}
        response = await client.put(
            endpoint, headers=headers, json={"lists": [user_list]})

        assert response.status_code == 201
        assert "lists" in response.json()

        for user_list_id, user_list in response.json()["lists"].items():
            assert user_list["version"] == 0
            assert user_list["created_time"]
            assert user_list["updated_time"]
            assert user_list["created_time"] == user_list["updated_time"]
            assert user_list["creator"] == user_id

            # NOTE: if we change the service to allow multiple diff authz versions,
            #       you should NOT remove this, but instead add more tests for the new
            #       version type
            assert user_list["authz"].get("version", {}) == 0
            assert user_list["authz"].get("authz") == (
                [get_list_by_id_endpoint(user_id, user_list_id)])

            if user_list["name"] == VALID_LIST_A["name"]:
                assert user_list["items"] == VALID_LIST_A["items"]
            elif user_list["name"] == VALID_LIST_B["name"]:
                assert user_list["items"] == VALID_LIST_B["items"]
            else:
                # fail if the list is neither A or B
                assert False

    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_create_multiple_valid_lists(self, get_token_claims, arborist,
                                               endpoint, client):
        # Simulate an authorized request and a valid token
        arborist.auth_request.return_value = True
        user_id = "79"
        get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}

        headers = {"Authorization": "Bearer ofa.valid.token"}
        response = await client.put(endpoint, headers=headers, json={"lists": [VALID_LIST_A, VALID_LIST_B]})

        assert response.status_code == 201
        assert "lists" in response.json()

        assert len(response.json()["lists"]) == 2

        have_seen_a = False
        have_seen_b = False
        for user_list_id, user_list in response.json()["lists"].items():
            assert user_list["version"] == 0
            assert user_list["created_time"]
            assert user_list["updated_time"]
            assert user_list["created_time"] == user_list["updated_time"]
            assert user_list["creator"] == user_id

            # NOTE: if we change the service to allow multiple diff authz versions,
            #       you should NOT remove this, but instead add more tests for the new
            #       version type
            assert user_list["authz"].get("version", {}) == 0
            assert user_list["authz"].get("authz") == [get_list_by_id_endpoint(user_id, user_list_id)]

            if user_list["name"] == VALID_LIST_A["name"]:
                assert user_list["items"] == VALID_LIST_A["items"]
                if have_seen_a:
                    pytest.fail("List A found twice, should only have showed up once")
                have_seen_a = True
            elif user_list["name"] == VALID_LIST_B["name"]:
                assert user_list["items"] == VALID_LIST_B["items"]
                if have_seen_b:
                    pytest.fail("List B found twice, should only have showed up once")
                have_seen_b = True
            else:
                # fail if the list is neither A or B
                assert False

    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_create_no_lists_provided(self, get_token_claims, arborist,
                                            endpoint, client):
        """
        Ensure 400 when no list is provided
        """
        # Simulate an authorized request and a valid token
        arborist.auth_request.return_value = True
        user_id = "79"
        get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}

        headers = {"Authorization": "Bearer ofa.valid.token"}
        response = await client.put(endpoint, headers=headers, json={"lists": []})

        assert response
        assert response.status_code == 400
        assert response.json().get("detail")

    @pytest.mark.parametrize(
        "input_body", [{}, {"foo": "bar"}, {"foo": {"foo": {"foo": "bar"}}}]
    )
    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_create_bad_input_provided(self, get_token_claims, arborist,
                                             endpoint, input_body, client):
        """
        Ensure 400 with bad input
        """
        # Simulate an authorized request and a valid token
        arborist.auth_request.return_value = True
        user_id = "79"
        get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}

        headers = {"Authorization": "Bearer ofa.valid.token"}
        response = await client.put(endpoint, headers=headers, json=input_body)

        assert response
        assert response.status_code == 400
        assert response.json().get("detail")

    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_create_no_body_provided(self, get_token_claims, arborist, endpoint, client):
        """
        Ensure 422 with no body
        """
        # Simulate an authorized request and a valid token
        arborist.auth_request.return_value = True
        user_id = "79"
        get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}

        headers = {"Authorization": "Bearer ofa.valid.token"}
        response = await client.put(endpoint, headers=headers)

        assert response
        assert response.status_code == 422
        assert response.json().get("detail")

# TODO: test db.create_lists raising some error other than unique constraint, ensure 400
# TODO: test creating a list with non unique name for given user, ensure 400
# TODO: test creating a list with non unique name for diff user, ensure 200

#
# @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
# @patch("gen3userdatalibrary.auth._get_token_claims")
# @patch("gen3userdatalibrary.routes.create_list.data_access_layer.create_user_lists")
# def test_db_create_lists_other_error(
#     mock_create_user_lists, get_token_claims, arborist, client
# ):
#     """
#     Test db.create_lists raising some error other than unique constraint, ensure 400
#     """
#     mock_create_user_lists.side_effect = Exception("Some DB error")
#     arborist.auth_request.return_value = True
#     user_id = "79"
#     get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}
#
#     headers = {"Authorization": "Bearer ofa.valid.token"}
#     response = client.post("/lists", headers=headers, json={"lists": [VALID_LIST_A]})
#
#     assert response.status_code == 400
#     assert response.json()["detail"] == "Invalid list information provided"
#
#
# @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
# @patch("gen3userdatalibrary.auth._get_token_claims")
# @patch("gen3userdatalibrary.routes.create_list.data_access_layer.create_user_lists")
# def test_create_list_non_unique_name_same_user(
#     mock_create_user_lists, get_token_claims, arborist, client
# ):
#     """
#     Test creating a list with a non-unique name for given user, ensure 400
#     """
#     mock_create_user_lists.side_effect = IntegrityError("UNIQUE constraint failed")
#     arborist.auth_request.return_value = True
#     user_id = "79"
#     get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}
#
#     headers = {"Authorization": "Bearer ofa.valid.token"}
#     response = client.post(
#         "/lists", headers=headers, json={"lists": [VALID_LIST_A, VALID_LIST_A]}
#     )
#
#     assert response.status_code == 400
#     assert response.json()["detail"] == "must provide a unique name"
#
#
# @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
# @patch("gen3userdatalibrary.auth._get_token_claims")
# def test_create_list_non_unique_name_diff_user(get_token_claims, arborist, client):
#     """
#     Test creating a list with a non-unique name for different user, ensure 200
#     """
#     arborist.auth_request.return_value = True
#
#     # Simulating first user
#     user_id_1 = "79"
#     get_token_claims.return_value = {"sub": user_id_1, "otherstuff": "foobar"}
#     headers = {"Authorization": "Bearer ofa.valid.token"}
#     response_1 = client.post("/lists", headers=headers, json={"lists": [VALID_LIST_A]})
#     assert response_1.status_code == 201
#
#     # Simulating second user
#     user_id_2 = "80"
#     get_token_claims.return_value = {"sub": user_id_2, "otherstuff": "foobar"}
#     headers = {"Authorization": "Bearer another.valid.token"}
#     response_2 = client.post("/lists", headers=headers, json={"lists": [VALID_LIST_A]})
#     assert response_2.status_code == 201
#     assert "lists" in response_2.json()
