from unittest.mock import AsyncMock, patch

import pytest

from gen3userdatalibrary.routes import route_aggregator
from tests.helpers import create_basic_list
from tests.routes.conftest import BaseTestRouter
from tests.routes.data import VALID_LIST_A, VALID_LIST_B, VALID_REPLACEMENT_LIST


@pytest.mark.asyncio
class TestUserListsRouter(BaseTestRouter):
    router = route_aggregator

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @pytest.mark.parametrize("endpoint", ["/lists/1"])
    @patch("gen3userdatalibrary.services.auth", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_getting_id_success(self, get_token_claims, arborist, endpoint, user_list, client):
        """
        If I create a list, I should be able to access it without issue if I have the correct auth

        :param endpoint: route we want to hit
        :param user_list: user list sample object
        :param client: route handler
        :param get_token_claims: todo: define
        :param arborist: todo: define
        """
        headers = {"Authorization": "Bearer ofa.valid.token"}
        await create_basic_list(arborist, get_token_claims, client, user_list, headers)
        response = await client.get("/lists", headers=headers)
        assert response.status_code == 200

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @pytest.mark.parametrize("endpoint", ["/lists/2"])
    @patch("gen3userdatalibrary.services.auth", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_getting_id_failure(self, get_token_claims, arborist, endpoint, user_list, client):
        """
        Ensure asking for a list with unused id returns 404
        """
        headers = {"Authorization": "Bearer ofa.valid.token"}
        create_outcome = await create_basic_list(arborist, get_token_claims, client, user_list, headers)
        response = await client.get(endpoint, headers=headers)
        assert response.status_code == 404

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @pytest.mark.parametrize("endpoint", ["/lists/1"])
    @patch("gen3userdatalibrary.services.auth", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_updating_by_id_success(self, get_token_claims, arborist, endpoint, user_list, client):
        """
        Test we can update a specific list correctly

        """
        headers = {"Authorization": "Bearer ofa.valid.token"}
        create_outcome = await create_basic_list(arborist, get_token_claims, client, user_list, headers)
        response = await client.put("/lists/1", headers=headers, json=VALID_REPLACEMENT_LIST)
        updated_list = response.json().get("updated_list", None)
        assert response.status_code == 200
        assert updated_list is not None
        assert updated_list["name"] == "example 2"
        assert updated_list["items"].get("CF_2", None) is not None
        assert updated_list["items"].get('drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a65', None) is not None

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @pytest.mark.parametrize("endpoint", ["/lists/1"])
    @patch("gen3userdatalibrary.services.auth", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_updating_by_id_failures(self, get_token_claims, arborist, endpoint, user_list, client):
        """
        Test updating non-existent list fails

        """
        headers = {"Authorization": "Bearer ofa.valid.token"}
        create_outcome = await create_basic_list(arborist, get_token_claims, client, user_list, headers)
        # todo: is there anything we should be worried about users trying to append? e.g. malicious or bad data?
        response = await client.put("/lists/2", headers=headers, json=VALID_REPLACEMENT_LIST)
        assert response.status_code == 404

    @pytest.mark.parametrize("endpoint", ["/lists/1"])
    @patch("gen3userdatalibrary.services.auth", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_appending_by_id_success(self, get_token_claims, arborist, endpoint, client):
        """
        Test we can append to a specific list correctly
        note: getting weird test behavior if I try to use valid lists, so keeping local until that is resolved
        """
        headers = {"Authorization": "Bearer ofa.valid.token"}
        special_list_a = {
            "name": "My Saved List 1",
            "items": {
                "drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a64": {
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
                }}}
        special_list_b = {
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
        create_outcomes = [await create_basic_list(arborist, get_token_claims, client, user_list, headers)
                           for user_list in [special_list_a, special_list_b]]
        body = {
            "drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a65": {
                "dataset_guid": "phs000001.v1.p1.c1",
                "type": "GA4GH_DRS"
            },
            "CF_2": {
                "name": "Cohort Filter 1",
                "type": "Gen3GraphQL",
                "schema_version": "c246d0f",
                "data": {
                    "query": """query ($filter: JSON) { _aggregation { subject (filter: $filter) { file_count { 
                histogram { sum } } } } }""",
                    "variables": {"filter": {
                        "AND": [{"IN": {"annotated_sex": ["male"]}}, {"IN": {"data_type": ["Aligned Reads"]}},
                                {"IN": {"data_format": ["CRAM"]}}, {"IN": {"race": ["[\"hispanic\"]"]}}]}}}
            }
        }

        response_one = await client.patch("/lists/1", headers=headers, json=body)
        response_two = await client.patch("/lists/2", headers=headers, json=body)
        for response in [response_one, response_two]:
            updated_list = response.json().get("updated_list", None)
            items = updated_list.get("items", None)
            assert response.status_code == 200
            assert items is not None
            assert items.get("CF_1", None) is not None
            assert items.get("CF_2", None) is not None
            assert items.get('drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a64', None) is not None
            assert items.get('drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a65', None) is not None
            if updated_list.get("name", None) == 'õ(*&!@#)(*$%)() 2':
                assert len(items) == 6

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @pytest.mark.parametrize("endpoint", ["/lists/1"])
    @patch("gen3userdatalibrary.services.auth", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_appending_by_id_failures(self, get_token_claims, arborist, endpoint, user_list, client):
        """
        Test that appending to non-existent list fails

        """
        headers = {"Authorization": "Bearer ofa.valid.token"}
        create_outcome = await create_basic_list(arborist, get_token_claims, client, user_list, headers)
        body = {
            "drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a65": {
                "dataset_guid": "phs000001.v1.p1.c1",
                "type": "GA4GH_DRS"
            },
            "CF_2": {
                "name": "Cohort Filter 1",
                "type": "Gen3GraphQL",
                "schema_version": "c246d0f",
                "data": {
                    "query": """query ($filter: JSON) { _aggregation { subject (filter: $filter) { file_count { 
                histogram { sum } } } } }""",
                    "variables": {"filter": {
                        "AND": [{"IN": {"annotated_sex": ["male"]}}, {"IN": {"data_type": ["Aligned Reads"]}},
                                {"IN": {"data_format": ["CRAM"]}}, {"IN": {"race": ["[\"hispanic\"]"]}}]}}}
            }
        }
        # todo: is there anything we should be worried about users trying to append? e.g. malicious or bad data?
        response = await client.patch("/lists/2", headers=headers, json=body)
        assert response.status_code == 404

    @pytest.mark.parametrize("endpoint", ["/lists/1"])
    @patch("gen3userdatalibrary.services.auth", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_deleting_by_id_success(self, get_token_claims, arborist, endpoint, client):
        """
        Test that we can't get data after it has been deleted

        """
        headers = {"Authorization": "Bearer ofa.valid.token"}
        await create_basic_list(arborist, get_token_claims, client, VALID_LIST_A, headers)
        sanity_get_check = await client.get("lists/1", headers=headers)
        assert sanity_get_check.status_code == 200
        first_delete = await client.delete("/lists/1", headers=headers)
        first_get_outcome = await client.get("lists/1", headers=headers)
        await create_basic_list(arborist, get_token_claims, client, VALID_LIST_B, headers)
        second_delete = await client.delete("/lists/2", headers=headers)
        second_get_outcome = await client.get("list/2", headers=headers)
        assert first_delete.status_code == 200
        assert first_get_outcome.status_code == 404
        assert second_delete.status_code == 200
        assert second_get_outcome.status_code == 404

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @pytest.mark.parametrize("endpoint", ["/lists/1"])
    @patch("gen3userdatalibrary.services.auth", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_deleting_by_id_failures(self, get_token_claims, arborist, endpoint, user_list, client):
        """
        Test we can't delete a non-existent list

        """
        headers = {"Authorization": "Bearer ofa.valid.token"}
        first_delete_attempt_1 = await client.delete("/lists/1", headers=headers)
        assert first_delete_attempt_1.status_code == 404

        await create_basic_list(arborist, get_token_claims, client, VALID_LIST_A, headers)
        sanity_get_check_1 = await client.get("lists/1", headers=headers)
        assert sanity_get_check_1.status_code == 200

        first_delete_attempt_2 = await client.delete("/lists/1", headers=headers)
        assert first_delete_attempt_2.status_code == 200

        first_delete_attempt_3 = await client.delete("/lists/1", headers=headers)
        assert first_delete_attempt_3.status_code == 404

        await create_basic_list(arborist, get_token_claims, client, VALID_LIST_B, headers)
        sanity_get_check_2 = await client.get("lists/2", headers=headers)
        assert sanity_get_check_2.status_code == 200

        second_delete_attempt_1 = await client.delete("/lists/2", headers=headers)
        assert second_delete_attempt_1.status_code == 200
