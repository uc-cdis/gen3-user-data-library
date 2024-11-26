from unittest.mock import AsyncMock, patch

import pytest
from tests.data.example_lists import VALID_LIST_A
from tests.routes.conftest import BaseTestRouter

from gen3userdatalibrary.main import route_aggregator
from gen3userdatalibrary.utils.metrics import get_from_cfg_metadata


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):
    router = route_aggregator

    @pytest.mark.parametrize("user_list", [VALID_LIST_A])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_max_limits(self, get_token_claims, arborist, user_list, client):
        assert NotImplemented
        headers = {"Authorization": "Bearer ofa.valid.token"}
        # config.MAX_LISTS = 1
        # config.MAX_LIST_ITEMS = 1
        # arborist.auth_request.return_value = True
        # get_token_claims.return_value = {"sub": "1", "otherstuff": "foobar"}
        # resp1 = await client.put("/lists", headers=headers, json={"lists": [user_list]})
        # assert resp1.status_code == 400 and resp1.text == '{"detail":"Too many items for list: My Saved List 1"}'
        # config.MAX_LIST_ITEMS = 2
        # resp2 = await create_basic_list(arborist, get_token_claims, client, user_list, headers)
        # resp3 = await client.put("/lists", headers=headers, json={"lists": [VALID_LIST_B]})
        # assert resp2.status_code == 201 and resp3.status_code == 400
        # config.MAX_LISTS = 2
        # resp4 = await client.put("/lists", headers=headers, json={"lists": [user_list]})
        # assert resp4.status_code == 507
        # config.MAX_LISTS = 6
        # config.MAX_LIST_ITEMS = 12

    async def test_item_schema_validation(self):
        pass
        # todo

    async def test_metadata_cfg_util(self):
        """
        If it exists, return it
        """
        set_metadata_value = "foobar"
        metadata = {"test_config_value": set_metadata_value}
        retrieved_metadata_value = get_from_cfg_metadata(
            "test_config_value", metadata, default="default-value", type_=str
        )

        assert retrieved_metadata_value == set_metadata_value

    async def test_metadata_cfg_util_doesnt_exist(self):
        """
        If it doesn't exist, return default
        """
        default = "default-value"
        retrieved_metadata_value = get_from_cfg_metadata(
            "this_doesnt_exist",
            {"test_config_value": "foobar"},
            default=default,
            type_=str,
        )
        assert retrieved_metadata_value == default

    async def test_metadata_cfg_util_cant_cast(self):
        """
        If it doesn't exist, return default
        """
        default = "default-value"
        retrieved_metadata_value = get_from_cfg_metadata(
            "this_doesnt_exist",
            {"test_config_value": "foobar"},
            default=default,
            type_=float,
        )
        assert retrieved_metadata_value == default

    @pytest.mark.parametrize("endpoint", ["/docs", "/redoc"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_docs(self, get_token_claims, arborist, endpoint, client):
        """
        Test FastAPI docs endpoints
        """
        arborist.auth_request.return_value = True
        get_token_claims.return_value = {"sub": "1", "otherstuff": "foobar"}
        headers = {"Authorization": "Bearer ofa.valid.token"}
        response = await client.get(endpoint, headers=headers)
        assert response.status_code == 200
