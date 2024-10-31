import json
from json import JSONDecodeError
from unittest.mock import AsyncMock, patch

import pytest
from black.trans import defaultdict

from gen3userdatalibrary import config
from gen3userdatalibrary.main import route_aggregator
from gen3userdatalibrary.services.auth import get_list_by_id_endpoint
from gen3userdatalibrary.services.helpers.core import map_creator_to_list_ids
from tests.data.example_lists import VALID_LIST_A, VALID_LIST_B, VALID_LIST_C
from tests.helpers import create_basic_list, get_id_from_response
from tests.routes.conftest import BaseTestRouter


@pytest.mark.asyncio
class TestUserListsRouter(BaseTestRouter):
    router = route_aggregator

    # region Auth

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    async def test_lists_no_token(self, endpoint, user_list, client, monkeypatch):
        """
        Test that the lists endpoint returns a 401 with details when no token is provided
        """
        previous_config = config.DEBUG_SKIP_AUTH
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", False)
        valid_single_list_body = {"lists": [user_list]}
        response = await client.put(endpoint, json=valid_single_list_body)
        assert response
        assert response.status_code == 401
        assert response.json().get("detail")
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    async def test_lists_invalid_token(
        self, arborist, endpoint, user_list, client, monkeypatch
    ):
        """
        Test accessing the endpoint when the token provided is invalid
        """
        previous_config = config.DEBUG_SKIP_AUTH
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", False)

        # Simulate an unauthorized request
        arborist.auth_request.return_value = False
        # not a valid token
        headers = {"Authorization": "Bearer ofbadnews"}

        # with pytest.raises(HTTPException) as e:
        response = await client.put(
            endpoint, headers=headers, json={"lists": [user_list]}
        )
        assert response.status_code == 401
        assert (
            "Could not verify, parse, and/or validate scope from provided access token."
            in response.text
        )
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @pytest.mark.parametrize("method", ["put", "get", "delete"])
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_create_lists_unauthorized(
        self,
        get_token_claims,
        arborist,
        method,
        user_list,
        endpoint,
        client,
        monkeypatch,
    ):
        """
        Test accessing the endpoint when unauthorized
        """
        previous_config = config.DEBUG_SKIP_AUTH
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", False)

        # Simulate an unauthorized request but a valid token
        arborist.auth_request.return_value = False
        get_token_claims.return_value = {"sub": "foo"}

        headers = {"Authorization": "Bearer ofa.valid.token"}
        if method == "post":
            response = await client.post(
                endpoint, headers=headers, json={"lists": [user_list]}
            )
        elif method == "get":
            response = await client.get(endpoint, headers=headers)
        elif method == "put":
            response = await client.put(
                endpoint, headers=headers, json={"lists": [user_list]}
            )
        elif method == "delete":
            response = await client.delete(endpoint, headers=headers)
        else:
            response = None
        assert response.status_code == 403
        assert "Forbidden" in response.text
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)

    # endregion

    # region Create Lists

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_create_single_valid_list(
        self, get_token_claims, arborist, endpoint, user_list, client, monkeypatch
    ):
        """
        Test the response for creating a single valid list
        """
        previous_config = config.DEBUG_SKIP_AUTH
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", False)
        # Simulate an authorized request and a valid token
        arborist.auth_request.return_value = True
        user_id = "79"
        get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}

        headers = {"Authorization": "Bearer ofa.valid.token"}
        response = await client.put(
            endpoint, headers=headers, json={"lists": [user_list]}
        )

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
                [get_list_by_id_endpoint(user_id, user_list_id)]
            )

            if user_list["name"] == VALID_LIST_A["name"]:
                assert user_list["items"] == VALID_LIST_A["items"]
            elif user_list["name"] == VALID_LIST_B["name"]:
                assert user_list["items"] == VALID_LIST_B["items"]
            else:
                # fail if the list is neither A or B
                assert False
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)

    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_create_multiple_valid_lists(
        self, get_token_claims, arborist, endpoint, client, monkeypatch
    ):
        previous_config = config.DEBUG_SKIP_AUTH
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", False)
        # Simulate an authorized request and a valid token
        arborist.auth_request.return_value = True
        user_id = "79"
        get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}

        headers = {"Authorization": "Bearer ofa.valid.token"}
        response = await client.put(
            endpoint, headers=headers, json={"lists": [VALID_LIST_A, VALID_LIST_B]}
        )

        assert response.status_code == 201
        assert "lists" in response.json()

        assert len(response.json()["lists"]) == 2

        have_seen_a = False
        have_seen_b = False
        for user_list_id, user_list in response.json()["lists"].items():
            assert user_list["version"] == 0
            assert user_list["created_time"]
            assert user_list["updated_time"]
            assert user_list["creator"] == user_id

            # NOTE: if we change the service to allow multiple diff authz versions,
            #       you should NOT remove this, but instead add more tests for the new
            #       version type
            assert user_list["authz"].get("version", {}) == 0
            assert user_list["authz"].get("authz") == [
                get_list_by_id_endpoint(user_id, user_list_id)
            ]

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
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)

    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_create_list_non_unique_name_diff_user(
        self, get_token_claims, arborist, client, endpoint, monkeypatch
    ):
        """
        Test creating a list with a non-unique name for different user, ensure 200

        :param get_token_claims: for token
        :param arborist: for successful auth
        :param endpoint: which route to hit
        :param client: router
        """
        previous_config = config.DEBUG_SKIP_AUTH
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", False)
        arborist.auth_request.return_value = True
        user_id = "79"
        get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}
        headers = {"Authorization": "Bearer ofa.valid.token"}
        response_1 = await client.put(
            endpoint, headers=headers, json={"lists": [VALID_LIST_A]}
        )
        assert response_1.status_code == 201

        # Simulating second user
        arborist.auth_request.return_value = True
        user_id = "80"
        get_token_claims.return_value = {"sub": user_id}
        headers = {"Authorization": "Bearer ofa.valid.token"}
        response_2 = await client.put(
            endpoint, headers=headers, json={"lists": [VALID_LIST_A]}
        )
        assert response_2.status_code == 201
        assert "lists" in response_2.json()
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)

    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_create_no_lists_provided(
        self, get_token_claims, arborist, endpoint, client
    ):
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
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_create_bad_input_provided(
        self, get_token_claims, arborist, endpoint, input_body, client
    ):
        """
        Ensure 400 with bad input
        """
        # Simulate an authorized request and a valid token
        arborist.auth_request.return_value = True
        user_id = "79"
        get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}

        headers = {"Authorization": "Bearer ofa.valid.token"}
        # with pytest.raises(HTTPException) as e:
        response = await client.put(
            endpoint, headers=headers, json={"lists": [input_body]}
        )
        assert response.status_code == 400

    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_create_no_body_provided(
        self, get_token_claims, arborist, endpoint, client
    ):
        """
        Ensure 422 with no body
        """
        # Simulate an authorized request and a valid token
        arborist.auth_request.return_value = True
        user_id = "79"
        get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}

        headers = {"Authorization": "Bearer ofa.valid.token"}
        with pytest.raises(JSONDecodeError) as e:
            response = await client.put(endpoint, headers=headers)

    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_duplicate_list(self, get_token_claims, arborist, endpoint, client):
        """
        Test creating a list with non-unique name for given user, ensure 400

        :param get_token_claims: for token
        :param arborist: for successful auth
        :param endpoint: which route to hit
        :param client: router
        """
        arborist.auth_request.return_value = True
        user_id = "79"
        get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}
        headers = {"Authorization": "Bearer ofa.valid.token"}
        response_1 = await client.put(
            endpoint, headers=headers, json={"lists": [VALID_LIST_A]}
        )
        response_2 = await client.put(
            endpoint, headers=headers, json={"lists": [VALID_LIST_A]}
        )
        assert response_2.status_code == 400

    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_db_create_lists_other_error(
        self, get_token_claims, arborist, client, endpoint
    ):
        """
        Test db.create_lists raising some error other than unique constraint, ensure 400
        """

        # malformed body

        arborist.auth_request.return_value = True
        user_id = "79"
        get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}
        headers = {"Authorization": "Bearer ofa.valid.token"}
        r1 = await create_basic_list(
            arborist, get_token_claims, client, VALID_LIST_A, headers
        )
        r2 = await client.put("/lists", headers=headers, json={"lists": [VALID_LIST_A]})
        assert r2.status_code == 400
        r3 = await client.put("/lists", headers=headers, json={"lists": []})
        assert r3.status_code == 400

    # endregion

    # region Read Lists

    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_reading_lists_success(
        self, get_token_claims, arborist, client, monkeypatch
    ):
        """
        Test I'm able to get back all lists for a user
        """
        previous_config = config.DEBUG_SKIP_AUTH
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", False)
        arborist.auth_request.return_value = True
        get_token_claims.return_value = {"sub": "foo"}
        headers = {"Authorization": "Bearer ofa.valid.token"}
        response_1 = await client.get("/lists", headers=headers)
        r1 = await create_basic_list(
            arborist, get_token_claims, client, VALID_LIST_A, headers
        )
        r2 = await create_basic_list(
            arborist, get_token_claims, client, VALID_LIST_B, headers
        )
        r3 = await create_basic_list(
            arborist, get_token_claims, client, VALID_LIST_A, headers, "2"
        )
        r4 = await create_basic_list(
            arborist, get_token_claims, client, VALID_LIST_B, headers, "2"
        )
        r5 = await create_basic_list(
            arborist, get_token_claims, client, VALID_LIST_B, headers, "3"
        )
        get_token_claims.return_value = {"sub": "1"}
        response_6 = await client.get("/lists", headers=headers)
        get_token_claims.return_value = {"sub": "2"}
        response_7 = await client.get("/lists", headers=headers)
        get_token_claims.return_value = {"sub": "3"}
        response_8 = await client.get("/lists", headers=headers)

        def get_creator_to_id_from_resp(resp):
            return map_creator_to_list_ids(
                json.loads(resp.content.decode("utf-8")).get("lists", {})
            )

        first_ids = get_creator_to_id_from_resp(response_6)
        second_ids = get_creator_to_id_from_resp(response_7)
        third_ids = get_creator_to_id_from_resp(response_8)
        id_1 = get_id_from_response(r1)
        id_2 = get_id_from_response(r2)
        id_3 = get_id_from_response(r3)
        id_4 = get_id_from_response(r4)
        id_5 = get_id_from_response(r5)
        creator_to_list_ids = defaultdict(set)
        creator_to_list_ids.update(first_ids)
        creator_to_list_ids.update(second_ids)
        creator_to_list_ids.update(third_ids)
        one_matches = creator_to_list_ids["1"] == {id_1, id_2}
        two_matches = creator_to_list_ids["2"] == {id_3, id_4}
        three_matches = creator_to_list_ids["3"] == {id_5}
        assert one_matches and two_matches and three_matches
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)

    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_reading_for_non_existent_user_fails(
        self, get_token_claims, arborist, client
    ):
        arborist.auth_request.return_value = True
        get_token_claims.return_value = {"sub": "foo"}
        headers = {"Authorization": "Bearer ofa.valid.token"}
        await create_basic_list(
            arborist, get_token_claims, client, VALID_LIST_A, headers
        )
        await create_basic_list(
            arborist, get_token_claims, client, VALID_LIST_B, headers
        )
        response_1 = await client.get("/lists", headers=headers)
        get_token_claims.return_value = {"sub": "bar"}
        response_2 = await client.get("/lists", headers=headers)

    # endregion

    # region Update Lists

    @pytest.mark.parametrize("endpoint", ["/lists"])
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_creating_and_updating_lists(
        self, get_token_claims, arborist, endpoint, client, monkeypatch
    ):
        previous_config = config.DEBUG_SKIP_AUTH
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", False)
        # Simulate an authorized request and a valid token
        arborist.auth_request.return_value = True
        user_id = "fsemr"
        get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}
        headers = {"Authorization": "Bearer ofa.valid.token"}
        response_1 = await client.put(
            endpoint, headers=headers, json={"lists": [VALID_LIST_A, VALID_LIST_B]}
        )
        updated_list_a = VALID_LIST_A
        updated_list_a["items"] = VALID_LIST_C["items"]
        response_2 = await client.put(
            endpoint, headers=headers, json={"lists": [VALID_LIST_C, updated_list_a]}
        )

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
                assert user_list["created_time"] != user_list["updated_time"]
                assert user_list["authz"].get("authz") == [
                    get_list_by_id_endpoint(user_id, user_list_id)
                ]
                assert user_list["items"] == VALID_LIST_C["items"]
                if have_seen_update:
                    pytest.fail(
                        "Updated list A found twice, should only have showed up once"
                    )
                have_seen_update = True
            elif user_list["name"] == VALID_LIST_C["name"]:
                assert user_list["created_time"] == user_list["updated_time"]
                assert user_list["authz"].get("authz") == [
                    get_list_by_id_endpoint(user_id, user_list_id)
                ]
                assert user_list["items"] == VALID_LIST_C["items"]
                if have_seen_c:
                    pytest.fail("List C found twice, should only have showed up once")
                have_seen_c = True
            else:
                # fail if the list is neither A nor B
                assert False
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)

    @pytest.mark.parametrize("endpoint", ["/lists"])
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_updating_two_lists_twice(
        self, get_token_claims, arborist, endpoint, client, monkeypatch
    ):
        previous_config = config.DEBUG_SKIP_AUTH
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", False)
        # update one list, update two lists
        # update twice
        headers = {"Authorization": "Bearer ofa.valid.token"}
        await create_basic_list(
            arborist, get_token_claims, client, VALID_LIST_A, headers
        )
        await create_basic_list(
            arborist, get_token_claims, client, VALID_LIST_B, headers
        )
        arborist.auth_request.return_value = True
        user_id = "qqqqqq"
        get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}
        updated_list_a = VALID_LIST_A
        updated_list_a["items"] = VALID_LIST_C["items"]
        updated_list_b = VALID_LIST_B
        updated_list_b["items"] = VALID_LIST_C["items"]
        response_2 = await client.put(
            endpoint, headers=headers, json={"lists": [updated_list_a, updated_list_b]}
        )
        updated_lists = json.loads(response_2.text).get("lists", {})
        has_cf_3 = lambda d: d["items"].get("CF_3", None) is not None
        assert [has_cf_3(user_list) for user_list in list(updated_lists.values())]
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)

    @pytest.mark.parametrize("endpoint", ["/lists"])
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_bad_lists_contents(
        self, get_token_claims, arborist, endpoint, client
    ):
        headers = {"Authorization": "Bearer ofa.valid.token"}
        resp1 = await create_basic_list(
            arborist, get_token_claims, client, VALID_LIST_A, headers
        )
        test_body = {
            "name": "My Saved List 1",
            "creator": "should_not_save",
            "items": {
                "drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a64": {
                    "dataset_guid": "phs000001.v1.p1.c1",
                    "type": "GA4GH_DRS",
                }
            },
        }
        resp2 = await client.put(endpoint, headers=headers, json=test_body)
        assert resp2.status_code == 400

    @pytest.mark.parametrize("endpoint", ["/lists"])
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_update_contents_wrong_type_fails(
        self, get_token_claims, arborist, endpoint, client
    ):
        headers = {"Authorization": "Bearer ofa.valid.token"}
        arborist.auth_request.return_value = True
        get_token_claims.return_value = {"sub": "1", "otherstuff": "foobar"}
        invalid_items = {"name": "foo", "items": {"this is a set not a dict"}}
        with pytest.raises(TypeError):
            response = await client.put(
                "/lists", headers=headers, json={"lists": [invalid_items]}
            )

    # endregion

    # region Delete Lists

    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_deleting_lists_success(self, get_token_claims, arborist, client):
        arborist.auth_request.return_value = True
        get_token_claims.return_value = {"sub": "foo"}
        headers = {"Authorization": "Bearer ofa.valid.token"}
        await create_basic_list(
            arborist, get_token_claims, client, VALID_LIST_A, headers
        )
        await create_basic_list(
            arborist, get_token_claims, client, VALID_LIST_B, headers
        )
        response_1 = await client.get("/lists", headers=headers)
        response_2 = await client.delete("/lists", headers=headers)
        response_3 = await client.get("/lists", headers=headers)
        list_content = json.loads(response_3.text).get("lists", None)
        assert list_content == {}

    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_deleting_lists_failures(
        self, get_token_claims, arborist, client, monkeypatch
    ):
        previous_config = config.DEBUG_SKIP_AUTH
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", False)
        # what should we do if a user X has no lists but requests a delete?
        arborist.auth_request.return_value = True
        headers = {"Authorization": "Bearer ofa.valid.token"}
        await create_basic_list(
            arborist, get_token_claims, client, VALID_LIST_A, headers
        )
        await create_basic_list(
            arborist, get_token_claims, client, VALID_LIST_B, headers
        )
        await create_basic_list(
            arborist, get_token_claims, client, VALID_LIST_B, headers, "2"
        )

        response_1 = await client.get("/lists", headers=headers)
        get_token_claims.return_value = {"sub": "89", "otherstuff": "foobar"}
        response_2 = await client.get("/lists", headers=headers)
        response_3 = await client.delete("/lists", headers=headers)
        response_4 = await client.get("/lists", headers=headers)
        assert response_3.status_code == 204
        assert response_4.status_code == 200
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)

    # endregion
