from unittest.mock import AsyncMock, patch
from venv import create

import pytest

from gen3userdatalibrary.routes import root_router
from tests.routes.conftest import BaseTestRouter
from tests.routes.data import VALID_LIST_A, VALID_LIST_B


async def create_basic_list(arborist, get_token_claims, client, user_list, headers):
    arborist.auth_request.return_value = True
    user_id = "79"
    get_token_claims.return_value = {"sub": user_id, "otherstuff": "foobar"}
    response = await client.put("/lists", headers=headers, json={"lists": [user_list]})
    assert response.status_code == 201


@pytest.mark.asyncio
class TestUserListsRouter(BaseTestRouter):
    router = root_router

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @pytest.mark.parametrize("endpoint", ["/lists/1", "/lists/1"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_getting_id_success(self, get_token_claims, arborist,
                                      endpoint, user_list, client, session):
        """

        :param endpoint:
        :param user_list:
        :param client:
        :return:
        """
        headers = {"Authorization": "Bearer ofa.valid.token"}
        await create_basic_list(arborist, get_token_claims, client, user_list, headers)
        response = await client.get(endpoint, headers=headers)
        assert response.status_code == 200

    async def test_getting_id_failure(self):
        pass

    async def test_updating_by_id_success(self):
        pass

    async def test_updating_by_id_failures(self):
        pass

    async def test_appending_by_id_success(self):
        pass

    async def test_appending_by_id_failures(self):
        pass

    async def test_deleting_by_id_success(self):
        pass

    async def test_deleting_by_id_failures(self):
        pass
