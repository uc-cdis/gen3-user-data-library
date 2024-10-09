import pytest

from unittest.mock import AsyncMock, patch

from gen3userdatalibrary import config
from gen3userdatalibrary.main import route_aggregator
from gen3userdatalibrary.utils import get_from_cfg_metadata
from tests.helpers import create_basic_list
from tests.routes.configs_for_test_routes import BaseTestRouter
from tests.routes.data import VALID_LIST_A


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):
    router = route_aggregator

    @pytest.mark.parametrize("user_list", [VALID_LIST_A])
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_max_limits(self, get_token_claims, arborist, user_list, client):
        headers = {"Authorization": "Bearer ofa.valid.token"}
        config.MAX_LISTS = 1
        config.MAX_LIST_ITEMS = 1
        resp1 = await create_basic_list(arborist, get_token_claims, client, user_list, headers)
        config.MAX_LIST_ITEMS = 2
        assert resp1.status_code == 400
        resp2 = await create_basic_list(arborist, get_token_claims, client, user_list, headers)
        resp3 = await create_basic_list(arborist, get_token_claims, client, user_list, headers)
        assert resp3.status_code == 400

        # assert response.status_code == 404
        assert NotImplemented

    async def test_item_schema_validation(self):

        assert NotImplemented

    async def test_metadata_cfg_util(self):
        """
        If it exists, return it
        """
        set_metadata_value = "foobar"
        metadata = {"test_config_value": set_metadata_value}
        retrieved_metadata_value = get_from_cfg_metadata("test_config_value", metadata, default="default-value",
                                                         type_=str)

        assert retrieved_metadata_value == set_metadata_value

    async def test_metadata_cfg_util_doesnt_exist(self):
        """
        If it doesn't exist, return default
        """
        default = "default-value"
        retrieved_metadata_value = get_from_cfg_metadata("this_doesnt_exist", {"test_config_value": "foobar"},
                                                         default=default, type_=str, )
        assert retrieved_metadata_value == default

    async def test_metadata_cfg_util_cant_cast(self):
        """
        If it doesn't exist, return default
        """
        default = "default-value"
        retrieved_metadata_value = get_from_cfg_metadata("this_doesnt_exist", {"test_config_value": "foobar"},
                                                         default=default, type_=float, )
        assert retrieved_metadata_value == default

    @pytest.mark.parametrize("endpoint", ["/docs", "/redoc"])
    async def test_docs(self, endpoint, client):
        """
        Test FastAPI docs endpoints
        """
        response = await client.get(endpoint)
        assert response.status_code == 200
