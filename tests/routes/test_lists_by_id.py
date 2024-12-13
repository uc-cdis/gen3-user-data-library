import json
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import UUID

import pytest
from starlette.datastructures import Headers
from starlette.requests import Request

from gen3userdatalibrary.db import DataAccessLayer
from gen3userdatalibrary.models.user_list import ItemToUpdateModel
from gen3userdatalibrary.routes import route_aggregator
from gen3userdatalibrary.routes.lists_by_id import (
    get_list_by_id,
    update_list_by_id,
    append_items_to_list,
    delete_list_by_id,
)
from tests.data.example_lists import (
    VALID_LIST_A,
    VALID_LIST_B,
    VALID_LIST_D,
    VALID_LIST_E,
    VALID_REPLACEMENT_LIST,
)
from tests.helpers import create_basic_list, get_id_from_response
from tests.routes.conftest import BaseTestRouter
from tests.test_db import EXAMPLE_USER_LIST


@pytest.mark.asyncio
class TestUserListsRouter(BaseTestRouter):
    router = route_aggregator

    @pytest.mark.parametrize(
        "endpoint", [lambda l_id: f"/lists/{l_id}", lambda l_id: f"/lists/{l_id}/"]
    )
    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_getting_id_success(
        self, get_token_claims, arborist, user_list, endpoint, app_client_pair
    ):
        """
        If I create a list, I should be able to access it without issue if I have the correct auth

        Args:
            get_token_claims: a general handler for authenticating a user's token
            arborist: async instance of our access control policy engine
            user_list: example user lists
        """
        app, test_client = app_client_pair
        app.state.arborist_client = AsyncMock()

        headers = {"Authorization": "Bearer ofa.valid.token"}
        resp1 = await create_basic_list(
            arborist, get_token_claims, test_client, user_list, headers
        )
        l_id = get_id_from_response(resp1)
        response = await test_client.get(endpoint(l_id), headers=headers)
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "endpoint", [lambda l_id: f"/lists/{l_id}", lambda l_id: f"/lists/{l_id}/"]
    )
    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_getting_id_failure(
        self, get_token_claims, arborist, user_list, endpoint, app_client_pair
    ):
        """
        Ensure asking for a list with unused id returns 404
        """
        app, test_client = app_client_pair
        app.state.arborist_client = AsyncMock()
        get_token_claims.return_value = {"sub": "0"}
        l_id = "550e8400-e29b-41d4-a716-446655440000"
        headers = {"Authorization": "Bearer ofa.valid.token"}
        no_data_resp = await test_client.get(endpoint(l_id), headers=headers)
        assert no_data_resp.status_code == 404
        create_outcome = await create_basic_list(
            arborist, get_token_claims, test_client, user_list, headers
        )
        l_id = get_id_from_response(create_outcome)
        response = await test_client.get(endpoint(l_id), headers=headers)
        assert response.status_code == 200
        l_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await test_client.get(endpoint(l_id), headers=headers)
        assert response.status_code == 404

    @pytest.mark.parametrize(
        "endpoint", [lambda l_id: f"/lists/{l_id}", lambda l_id: f"/lists/{l_id}/"]
    )
    @pytest.mark.parametrize("user_list", [VALID_LIST_A])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_updating_by_id_success(
        self, get_token_claims, arborist, user_list, endpoint, app_client_pair
    ):
        """
        Test we can update a specific list correctly

        """
        app, test_client = app_client_pair
        app.state.arborist_client = AsyncMock()

        headers = {"Authorization": "Bearer ofa.valid.token"}
        create_outcome = await create_basic_list(
            arborist, get_token_claims, test_client, user_list, headers
        )
        ul_id = get_id_from_response(create_outcome)
        put_response = await test_client.put(
            endpoint(ul_id), headers=headers, json=VALID_REPLACEMENT_LIST
        )
        get_updated_list_response = await test_client.get(
            endpoint(ul_id), headers=headers
        )
        updated_list = get_updated_list_response.json()
        assert updated_list["id"] == next(iter(create_outcome.json()["lists"].keys()))
        assert put_response.status_code == 200
        assert updated_list is not None
        assert updated_list["id"] == ul_id
        assert updated_list["name"] == "My Saved List 1"
        assert updated_list["items"].get("CF_2", None) is not None
        assert (
            updated_list["items"].get(
                "drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a65", None
            )
            is not None
        )
        empty_put_response = await test_client.put(
            endpoint(ul_id),
            headers=headers,
            json={"name": "My Saved List 1", "items": {}},
        )
        assert empty_put_response.status_code == 200
        assert empty_put_response.json().get("id", None) == ul_id
        get_empty_list_resp = await test_client.get(endpoint(ul_id), headers=headers)
        assert get_empty_list_resp.status_code == 200
        assert get_empty_list_resp.json().get("id", None) == ul_id

    @pytest.mark.parametrize(
        "endpoint", [lambda l_id: f"/lists/{l_id}", lambda l_id: f"/lists/{l_id}/"]
    )
    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_updating_by_id_failures(
        self, get_token_claims, arborist, user_list, endpoint, app_client_pair
    ):
        """
        Test updating non-existent list fails
        """
        app, test_client = app_client_pair
        app.state.arborist_client = AsyncMock()

        headers = {"Authorization": "Bearer ofa.valid.token"}
        create_outcome = await create_basic_list(
            arborist, get_token_claims, test_client, user_list, headers
        )
        ul_id = "d94ddbcc-6ef5-4a38-bc9f-95b3ef58e274"
        response = await test_client.put(
            endpoint(ul_id), headers=headers, json=VALID_REPLACEMENT_LIST
        )
        assert response.status_code == 404

    @pytest.mark.parametrize(
        "endpoint",
        [
            lambda resp: f"/lists/{get_id_from_response(resp)}",
            lambda resp: f"/lists/{get_id_from_response(resp)}/",
        ],
    )
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_appending_by_id_success(
        self, get_token_claims, arborist, endpoint, app_client_pair
    ):
        """
        Test we can append to a specific list correctly
        note: getting weird test behavior if I try to use valid lists, so keeping local until that is resolved
        """
        app, test_client = app_client_pair
        app.state.arborist_client = AsyncMock()

        headers = {"Authorization": "Bearer ofa.valid.token"}
        outcome_D = await create_basic_list(
            arborist, get_token_claims, test_client, VALID_LIST_D, headers
        )
        outcome_E = await create_basic_list(
            arborist, get_token_claims, test_client, VALID_LIST_E, headers
        )

        body = {
            "drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a99": {
                "dataset_guid": "phs000001.v1.p1.c1",
                "type": "GA4GH_DRS",
            },
            "CF_2": {
                "name": "Cohort Filter 1",
                "type": "Gen3GraphQL",
                "schema_version": "c246d0f",
                "data": {
                    "query": """query ($filter: JSON) { _aggregation { subject (filter: $filter) { file_count {
                histogram { sum } } } } }""",
                    "variables": {
                        "filter": {
                            "AND": [
                                {"IN": {"annotated_sex": ["male"]}},
                                {"IN": {"data_type": ["Aligned Reads"]}},
                                {"IN": {"data_format": ["CRAM"]}},
                                {"IN": {"race": ['["hispanic"]']}},
                            ]
                        }
                    },
                },
            },
        }

        response_one = await test_client.patch(
            endpoint(outcome_D), headers=headers, json=body
        )
        response_two = await test_client.patch(
            endpoint(outcome_E), headers=headers, json=body
        )
        for response in [response_one]:
            updated_list = response.json()
            items = updated_list.get("items", None)
            assert response.status_code == 200
            assert items is not None
            if updated_list["name"] == "My Saved List D":
                assert (
                    items.get(
                        "drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a04", None
                    )
                    is not None
                )
            else:
                assert (
                    items.get(
                        "drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a05", None
                    )
                    is not None
                )
            assert (
                items.get("drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a99", None)
                is not None
            )
            if updated_list.get("name", None) == "õ(*&!@#)(*$%)() 2":
                assert len(items) == 6

    @pytest.mark.parametrize(
        "endpoint", [lambda l_id: f"/lists/{l_id}", lambda l_id: f"/lists/{l_id}/"]
    )
    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_appending_by_id_failures(
        self, get_token_claims, arborist, user_list, endpoint, app_client_pair
    ):
        """
        Test that appending to non-existent list fails

        """
        app, test_client = app_client_pair
        app.state.arborist_client = AsyncMock()

        headers = {"Authorization": "Bearer ofa.valid.token"}
        create_outcome = await create_basic_list(
            arborist, get_token_claims, test_client, user_list, headers
        )
        ul_id = get_id_from_response(create_outcome)
        response = await test_client.patch(f"/lists/{ul_id}", headers=headers, json={})
        assert response.status_code == 409
        body = {
            "drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a65": {
                "dataset_guid": "phs000001.v1.p1.c1",
                "type": "GA4GH_DRS",
            },
            "CF_2": {
                "name": "Cohort Filter 1",
                "type": "Gen3GraphQL",
                "schema_version": "c246d0f",
                "data": {
                    "query": """query ($filter: JSON) { _aggregation { subject (filter: $filter) { file_count {
                histogram { sum } } } } }""",
                    "variables": {
                        "filter": {
                            "AND": [
                                {"IN": {"annotated_sex": ["male"]}},
                                {"IN": {"data_type": ["Aligned Reads"]}},
                                {"IN": {"data_format": ["CRAM"]}},
                                {"IN": {"race": ['["hispanic"]']}},
                            ]
                        }
                    },
                },
            },
        }
        ul_id = "d94ddbcc-6ef5-4a38-bc9f-95b3ef58e274"
        response = await test_client.patch(endpoint(ul_id), headers=headers, json=body)
        assert response.status_code == 404

    @pytest.mark.parametrize(
        "endpoint", [lambda l_id: f"/lists/{l_id}", lambda l_id: f"/lists/{l_id}/"]
    )
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_deleting_by_id_success(
        self, get_token_claims, arborist, endpoint, app_client_pair
    ):
        """
        Test that we can't get data after it has been deleted

        """
        app, test_client = app_client_pair
        app.state.arborist_client = AsyncMock()

        headers = {"Authorization": "Bearer ofa.valid.token"}
        resp1 = await create_basic_list(
            arborist, get_token_claims, test_client, VALID_LIST_A, headers
        )
        first_id = get_id_from_response(resp1)
        sanity_get_check = await test_client.get(endpoint(first_id), headers=headers)
        assert sanity_get_check.status_code == 200
        first_delete = await test_client.delete(endpoint(first_id), headers=headers)
        first_get_outcome = await test_client.get(endpoint(first_id), headers=headers)
        resp2 = await create_basic_list(
            arborist, get_token_claims, test_client, VALID_LIST_B, headers
        )
        second_id = get_id_from_response(resp2)
        second_delete = await test_client.delete(endpoint(second_id), headers=headers)
        second_get_outcome = await test_client.get(endpoint(second_id), headers=headers)
        assert first_delete.status_code == 204
        assert first_get_outcome.status_code == 404
        assert second_delete.status_code == 204
        assert second_get_outcome.status_code == 404

    @pytest.mark.parametrize(
        "endpoint", [lambda l_id: f"/lists/{l_id}", lambda l_id: f"/lists/{l_id}/"]
    )
    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_deleting_by_id_failures(
        self, get_token_claims, arborist, user_list, endpoint, app_client_pair
    ):
        """
        Test we can't delete a non-existent list

        """
        app, test_client = app_client_pair
        app.state.arborist_client = AsyncMock()

        headers = {"Authorization": "Bearer ofa.valid.token"}

        resp1 = await create_basic_list(
            arborist, get_token_claims, test_client, VALID_LIST_A, headers
        )
        ul_id = get_id_from_response(resp1)
        sanity_get_check_1 = await test_client.get(endpoint(ul_id), headers=headers)
        assert sanity_get_check_1.status_code == 200

        first_delete_attempt_2 = await test_client.delete(
            endpoint(ul_id), headers=headers
        )
        assert first_delete_attempt_2.status_code == 204

        first_delete_attempt_3 = await test_client.delete(
            endpoint(ul_id), headers=headers
        )
        assert first_delete_attempt_3.status_code == 404

        resp2 = await create_basic_list(
            arborist, get_token_claims, test_client, VALID_LIST_B, headers
        )
        ul_id_2 = get_id_from_response(resp2)
        sanity_get_check_2 = await test_client.get(endpoint(ul_id_2), headers=headers)
        assert sanity_get_check_2.status_code == 200

        second_delete_attempt_1 = await test_client.delete(
            endpoint(ul_id_2), headers=headers
        )
        assert second_delete_attempt_1.status_code == 204

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_get_by_id_list_not_exist(
        self, get_token_claims, arborist, user_list, client
    ):
        headers = {"Authorization": "Bearer ofa.valid.token"}
        l_id = "550e8400-e29b-41d4-a716-446655440000"
        get_token_claims.return_value = {"sub": "0"}
        outcome = await client.get(f"/lists/{l_id}", headers=headers)
        assert outcome.status_code == 404

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_update_by_id_list_not_exist(
        self, get_token_claims, arborist, user_list, client
    ):
        headers = {"Authorization": "Bearer ofa.valid.token"}
        l_id = "550e8400-e29b-41d4-a716-446655440000"
        get_token_claims.return_value = {"sub": "0"}
        outcome = await client.put(
            f"/lists/{l_id}", headers=headers, json={"name": "fizz", "items": {}}
        )
        assert outcome.status_code == 404

    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_get_list_by_id_directly(
        self, arborist, get_token_claims, alt_session, client
    ):
        l_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        EXAMPLE_REQUEST = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/example",
                "headers": Headers({"host": "127.0.0.1:8000"}).raw,
                "query_string": b"name=example",
                "client": ("127.0.0.1", 8000),
            }
        )
        outcome = await get_list_by_id(
            l_id, EXAMPLE_REQUEST, DataAccessLayer(alt_session)
        )
        assert outcome.status_code == 404

        arborist.auth_request.return_value = True
        get_token_claims.return_value = {"sub": "0", "otherstuff": "foobar"}
        headers = {"Authorization": "Bearer ofa.valid.token"}
        dal = DataAccessLayer(alt_session)
        r1 = await dal.persist_user_list("0", EXAMPLE_USER_LIST())
        outcome = await get_list_by_id(r1.id, EXAMPLE_REQUEST, dal)
        assert outcome.status_code == 200
        assert json.loads(outcome.body).get("id", None) == str(r1.id)

    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_update_list_by_id_directly(
        self, get_token_claims, arborist, alt_session
    ):
        arborist.auth_request.return_value = True
        get_token_claims.return_value = {"sub": "0"}
        headers = {"Authorization": "Bearer ofa.valid.token"}
        dal = DataAccessLayer(alt_session)
        r1 = await dal.persist_user_list("0", EXAMPLE_USER_LIST())
        l_id = r1.id
        info_to_update_with = (
            ItemToUpdateModel(
                name="bim bam",
                items={"bug": "bear"},
            ),
        )
        update_outcome = await update_list_by_id(
            EXAMPLE_ENDPOINT_REQUEST, l_id, info_to_update_with[0], dal
        )
        assert update_outcome.status_code == 200
        assert json.loads(update_outcome.body).get("items", {}) == {"bug": "bear"}

    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_append_items_to_list_directly(
        self, get_token_claims, arborist, alt_session
    ):
        arborist.auth_request.return_value = True
        get_token_claims.return_value = {"sub": "0", "otherstuff": "foobar"}
        dal = DataAccessLayer(alt_session)
        r1 = await dal.persist_user_list("0", EXAMPLE_USER_LIST())
        l_id = r1.id
        append_outcome = await append_items_to_list(
            EXAMPLE_ENDPOINT_REQUEST, l_id, {"bug": "bear"}, dal
        )
        assert append_outcome.status_code == 200
        assert json.loads(append_outcome.body).get("items", {}) == {
            "fizz": "buzz",
            "bug": "bear",
        }

    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_delete_list_by_id_directly(
        self, get_token_claims, arborist, alt_session
    ):
        arborist.auth_request.return_value = True
        get_token_claims.return_value = {"sub": "0"}
        dal = DataAccessLayer(alt_session)
        r1 = await dal.persist_user_list("0", EXAMPLE_USER_LIST())
        l_id = r1.id
        delete_outcome = await delete_list_by_id(l_id, EXAMPLE_ENDPOINT_REQUEST, dal)
        assert delete_outcome.status_code == 204
        get_by_id_outcome = await get_list_by_id(l_id, EXAMPLE_ENDPOINT_REQUEST, dal)
        assert get_by_id_outcome.status_code == 404


EXAMPLE_ENDPOINT_REQUEST = Request(
    {
        "type": "http",
        "method": "PUT",
        "path": "/example",
        "headers": Headers({"host": "127.0.0.1:8000"}).raw,
        "query_string": b"name=example",
        "client": ("127.0.0.1", 8000),
        "app": MagicMock(),
    }
)
