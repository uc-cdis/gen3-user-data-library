from unittest.mock import AsyncMock, patch
import pytest

from gen3userdatalibrary.auth import get_list_by_id_endpoint
from tests.routes.conftest import BaseTestRouter

from gen3userdatalibrary.main import root_router
from tests.routes.data import VALID_LIST_A, VALID_LIST_B, VALID_LIST_C


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
        get_token_claims.return_value = {"sub": "foo"}

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
        user_id = "79"
        get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}

        headers = {"Authorization": "Bearer ofa.valid.token"}
        response = await client.put(endpoint, headers=headers, json={"lists": [user_list]})

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

    @pytest.mark.parametrize("endpoint", ["/lists"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_creating_and_updating_lists(self, get_token_claims, arborist,
                                               endpoint, client):
        # Simulate an authorized request and a valid token
        arborist.auth_request.return_value = True
        user_id = "79"
        get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}

        headers = {"Authorization": "Bearer ofa.valid.token"}

        response_1 = await client.put(endpoint, headers=headers, json={"lists": [VALID_LIST_A, VALID_LIST_B]})
        updated_list_a = VALID_LIST_A
        updated_list_a["items"] = VALID_LIST_C["items"]
        response_2 = await client.put(endpoint, headers=headers, json={"lists": [VALID_LIST_C, updated_list_a]})

        assert response_2.status_code == 201
        assert "lists" in response_2.json()

        assert len(response_2.json()["lists"]) == 2

        have_seen_c = False
        have_seen_update = False
        for user_list_id, user_list in response_2.json()["lists"].items():
            assert user_list["version"] == 0
            assert user_list["created_time"]
            assert user_list["updated_time"]
            assert user_list["creator"] == user_id

            # NOTE: if we change the service to allow multiple diff authz versions,
            #       you should NOT remove this, but instead add more tests for the new
            #       version type
            assert user_list["authz"].get("version", {}) == 0

            if user_list["name"] == VALID_LIST_A["name"]:
                # todo: currently, when we update lists the authz endpoint becomes `/lists` instead of
                # `/lists/{ID}`, will this be a problem? If so, we should fix
                assert user_list["created_time"] != user_list["updated_time"]
                assert user_list["authz"].get("authz") == [get_list_by_id_endpoint(user_id, user_list_id)]
                assert user_list["items"] == VALID_LIST_C["items"]
                if have_seen_update:
                    pytest.fail("Updated list A found twice, should only have showed up once")
                have_seen_update = True
            elif user_list["name"] == VALID_LIST_C["name"]:
                assert user_list["created_time"] == user_list["updated_time"]
                assert user_list["authz"].get("authz") == [get_list_by_id_endpoint(user_id, user_list_id)]
                assert user_list["items"] == VALID_LIST_C["items"]
                if have_seen_c:
                    pytest.fail("List C found twice, should only have showed up once")
                have_seen_c = True
            else:
                # fail if the list is neither A or B
                assert False

    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_duplicate_list(self, get_token_claims, arborist, endpoint, client):
        """
        test creating a list with non unique name for given user, ensure 400

        :param get_token_claims: for token
        :param arborist: for successful auth
        :param endpoint: which route to hit
        :param client: router
        :return: pass/fail based on assert
        """

        arborist.auth_request.return_value = True
        user_id = "79"
        get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}
        headers = {"Authorization": "Bearer ofa.valid.token"}
        response_1 = await client.put(endpoint, headers=headers, json={"lists": [VALID_LIST_A]})
        response_2 = await client.put(endpoint, headers=headers, json={"lists": [VALID_LIST_A]})

        assert response_2.status_code == 400

    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_db_create_lists_other_error(self, get_token_claims, arborist, client, endpoint):
        """
        Test db.create_lists raising some error other than unique constraint, ensure 400
        todo: ask for clarity
        """
        arborist.auth_request.return_value = True
        user_id = "79"
        get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}

        headers = {"Authorization": "Bearer ofa.valid.token"}
        response = await client.put(endpoint, headers=headers, json={"lists": [VALID_LIST_A]})
        assert NotImplemented

        # assert response.status_code == 400
        # assert response.json()["detail"] == "Invalid list information provided"

    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_create_list_non_unique_name_diff_user(self, get_token_claims, arborist, client, endpoint):
        """
        Test creating a list with a non-unique name for different user, ensure 200

        :param get_token_claims: for token
        :param arborist: for successful auth
        :param endpoint: which route to hit
        :param client: router
        :return: pass/fail based on assert
        """
        arborist.auth_request.return_value = True
        user_id = "79"
        get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}
        headers = {"Authorization": "Bearer ofa.valid.token"}
        response_1 = await client.put(endpoint, headers=headers, json={"lists": [VALID_LIST_A]})
        assert response_1.status_code == 201

        # Simulating second user
        arborist.auth_request.return_value = True
        user_id = "80"
        get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}
        headers = {"Authorization": "Bearer ofa.valid.token"}
        response_2 = await client.put(endpoint, headers=headers, json={"lists": [VALID_LIST_A]})
        assert response_2.status_code == 201
        assert "lists" in response_2.json()
