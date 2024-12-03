from unittest.mock import AsyncMock, patch

import pytest

from gen3userdatalibrary.routes import route_aggregator
from tests.data.example_lists import (
    VALID_LIST_A,
    VALID_LIST_B,
    VALID_REPLACEMENT_LIST,
    VALID_LIST_D,
    VALID_LIST_E,
)
from tests.helpers import create_basic_list, get_id_from_response
from tests.routes.conftest import BaseTestRouter


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
            client: route handler
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

        headers = {"Authorization": "Bearer ofa.valid.token"}
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
        response = await test_client.put(
            endpoint(ul_id), headers=headers, json=VALID_REPLACEMENT_LIST
        )
        updated_list = response.json()
        assert response.status_code == 200
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
