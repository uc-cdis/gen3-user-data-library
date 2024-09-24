from unittest.mock import AsyncMock, patch

import pytest

from gen3userdatalibrary.routes import root_router
from tests.routes.conftest import BaseTestRouter
from tests.routes.data import VALID_LIST_A, VALID_LIST_B, VALID_LIST_C


async def create_basic_list(arborist, get_token_claims, client, user_list, headers):
    arborist.auth_request.return_value = True
    user_id = "79"
    get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}
    response = await client.put("/lists", headers=headers, json={"lists": [user_list]})
    assert response.status_code == 201
    return response


@pytest.mark.asyncio
class TestUserListsRouter(BaseTestRouter):
    router = root_router

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @pytest.mark.parametrize("endpoint", ["/lists/1"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_getting_id_success(self, get_token_claims, arborist,
                                      endpoint, user_list, client, session):
        """
        If I create a list, I should be able to access it without issue if I have the correct auth

        :param endpoint: route we want to hit
        :param user_list: user list object we're working with
        :param client: route handler
        :param get_token_claims: ?
        :param arborist: ?
        :param session: ?

        """
        headers = {"Authorization": "Bearer ofa.valid.token"}
        await create_basic_list(arborist, get_token_claims, client, user_list, headers)
        response = await client.get("/lists", headers=headers)
        assert response.status_code == 200

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @pytest.mark.parametrize("endpoint", ["/lists/2", "/lists/2"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_getting_id_failure(self, get_token_claims, arborist,
                                      endpoint, user_list, client, session):
        """
        Ensure asking for a list with unused id returns 404

        :param get_token_claims:
        :param arborist:
        :param endpoint:
        :param user_list:
        :param client:
        :param session:
        :return:
        """
        headers = {"Authorization": "Bearer ofa.valid.token"}
        create_outcome = await create_basic_list(arborist, get_token_claims, client, user_list, headers)
        response = await client.get(endpoint, headers=headers)
        assert response.status_code == 404

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @pytest.mark.parametrize("endpoint", ["/lists/1", "/lists/1"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_updating_by_id_success(self, get_token_claims, arborist,
                                          endpoint, user_list, client, session):
        """
        Test we can update a specific list correctly

        :param get_token_claims:
        :param arborist:
        :param endpoint:
        :param user_list:
        :param client:
        :param session:
        :return:
        """
        headers = {"Authorization": "Bearer ofa.valid.token"}
        create_outcome = await create_basic_list(arborist, get_token_claims, client, user_list, headers)
        body = {
            "name": "example 2",
            "items": {
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
        }

        response = await client.put("/lists/1", headers=headers, json=body)
        updated_list = response.json().get("updated_list", None)
        assert response.status_code == 200
        assert updated_list is not None
        assert updated_list["name"] == "example 2"
        assert updated_list["items"].get("CF_2", None) is not None
        assert updated_list["items"].get('drs://dg.4503:943200c3-271d-4a04-a2b6-040272239a65', None) is not None

    async def test_updating_by_id_failures(self):
        pass

    async def test_appending_by_id_success(self):
        # todo: what kind of data is coming into a patch?
        pass

    async def test_appending_by_id_failures(self):
        pass

    @pytest.mark.parametrize("endpoint", ["/lists/1"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_deleting_by_id_success(self, get_token_claims, arborist,
                                          endpoint, client, session):
        """
        Test that we can't get data after it has been deleted

        :param get_token_claims:
        :param arborist:
        :param endpoint:
        :param client:
        :param session:
        :return:
        """
        headers = {"Authorization": "Bearer ofa.valid.token"}
        await create_basic_list(arborist, get_token_claims, client, VALID_LIST_A, headers)
        sanity_get_check = await client.get("lists/1", headers=headers)
        assert sanity_get_check.status_code == 200
        first_delete = await client.delete("/lists/1", headers=headers)
        first_get_outcome = await client.get("lists/1", headers=headers)
        await create_basic_list(arborist, get_token_claims, client, VALID_LIST_B, headers)
        second_delete = await client.delete("/lists/2", headers=headers)
        second_get_outcome = await client.get("list/1", headers=headers)
        assert first_delete.status_code == 200
        assert first_get_outcome.status_code == 404
        assert second_delete.status_code == 200
        assert second_get_outcome.status_code == 404

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @pytest.mark.parametrize("endpoint", ["/lists/1"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_deleting_by_id_failures(self, get_token_claims, arborist,
                                           endpoint, user_list, client, session):
        """
        Test unsuccessful deletes behave correctly

        :param get_token_claims:
        :param arborist:
        :param endpoint:
        :param user_list:
        :param client:
        :param session:

        """
        headers = {"Authorization": "Bearer ofa.valid.token"}
        first_delete_attempt_1 = await client.delete("/lists/1", headers=headers)
        await create_basic_list(arborist, get_token_claims, client, VALID_LIST_A, headers)
        first_delete_attempt_2 = await client.delete("/lists/1", headers=headers)
        await create_basic_list(arborist, get_token_claims, client, VALID_LIST_B, headers)
        second_delete_attempt_1 = await client.delete("/lists/1", headers=headers)
        assert first_delete_attempt_1.status_code == 404
        assert first_delete_attempt_2.status_code == 200
        assert second_delete_attempt_1.status_code == 404
