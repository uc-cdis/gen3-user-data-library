"""
For any complex tests that seek o test multiple ids together
"""
from unittest.mock import AsyncMock, patch

import pytest

from gen3userdatalibrary.routes import route_aggregator
from tests.data.example_lists import VALID_LIST_A, VALID_LIST_B
from tests.routes.conftest import BaseTestRouter


@pytest.mark.asyncio
class TestUserListsRouter(BaseTestRouter):
    router = route_aggregator

    @pytest.mark.parametrize("user_list", [VALID_LIST_A, VALID_LIST_B])
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_full_successful_walkthrough(self, get_token_claims, arborist, user_list, client):
        assert NotImplemented
        # # delete by id
        # resp1 = requests.put(basic_url, headers=headers, json=make_body(5)),
        # l_id = get_id_from_response(resp1[0])
        # id_url = f"http://0.0.0.0:8000/lists/{l_id}"
        # resp2 = requests.get(id_url, headers=headers),
        # resp3 = requests.patch(id_url, headers=headers, json=patch_body),
        # resp4 = requests.delete(id_url, headers=headers, auth=auth)
        # print(resp4)
        #
        # # delete all
        # resp5 = requests.put(basic_url, headers=headers, json=make_body(1)),
        # resp6 = requests.put(basic_url, headers=headers, json=make_body(2)),
        # l_id = get_id_from_response(resp6[0])
        # id_url = f"http://0.0.0.0:8000/lists/{l_id}"
        # resp7 = requests.get(id_url, headers=headers),
        # resp8 = requests.patch(id_url, headers=headers, json=patch_body),
        # resp9 = requests.delete(basic_url, headers=headers, auth=auth)
        # print(resp9)
