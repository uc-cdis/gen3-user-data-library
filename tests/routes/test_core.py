"""
For any complex tests that seek to test multiple ids together
"""

from unittest.mock import AsyncMock, patch

import pytest

from gen3userdatalibrary.main import route_aggregator
from tests.data.example_lists import (
    VALID_LIST_A,
    VALID_LIST_B,
    VALID_PATCH_BODY,
)
from tests.helpers import get_id_from_response
from tests.routes.conftest import BaseTestRouter


@pytest.mark.asyncio
class TestUserListsRouter(BaseTestRouter):
    router = route_aggregator

    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    async def test_full_successful_walkthrough(
        self, get_token_claims, arborist, client, endpoint
    ):
        """
        General tests off all the endpoints together
        Args:
            get_token_claims: mock token
            arborist: bypass auth
            client: endpoint interface
            endpoint: endpoints to hit
        """
        get_token_claims.return_value = {"sub": "1"}
        arborist.auth_request.return_value = True
        headers = {"Authorization": "Bearer ofa.valid.token"}
        resp1 = (
            await client.put(endpoint, headers=headers, json={"lists": [VALID_LIST_A]}),
        )
        l_id = get_id_from_response(resp1[0])
        id_url = f"/lists/{l_id}"
        resp2 = (await client.get(id_url, headers=headers),)
        resp3 = (await client.patch(id_url, headers=headers, json=VALID_PATCH_BODY),)
        resp4 = await client.delete(id_url, headers=headers)
        get_token_claims.return_value = {"sub": "2"}
        resp5 = (
            await client.put(endpoint, headers=headers, json={"lists": [VALID_LIST_A]}),
        )
        resp6 = (
            await client.put(endpoint, headers=headers, json={"lists": [VALID_LIST_B]}),
        )
        l_id = get_id_from_response(resp6[0])
        id_url = f"http://0.0.0.0:8000/lists/{l_id}"
        resp7 = (await client.get(id_url, headers=headers),)
        resp8 = (await client.patch(id_url, headers=headers, json=VALID_PATCH_BODY),)
        resp9 = await client.delete(endpoint, headers=headers)
        get_code = lambda r: r[0].status_code
        two_hundred_codes = set(map(get_code, [resp2, resp3, resp7, resp8])).union({})
        two_o_one_codes = set(map(get_code, [resp1, resp5, resp6]))
        two_o_four = {resp4.status_code, resp9.status_code}
        assert (
            two_hundred_codes == {200}
            and two_o_one_codes == {201}
            and two_o_four == {204}
        )
