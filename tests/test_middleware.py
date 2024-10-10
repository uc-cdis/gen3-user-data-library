import pytest

from unittest.mock import AsyncMock, patch

from gen3userdatalibrary import config
from gen3userdatalibrary.main import route_aggregator
from gen3userdatalibrary.utils import get_from_cfg_metadata
from tests.helpers import create_basic_list
from tests.routes.conftest import BaseTestRouter
from tests.data.example_lists import VALID_LIST_A


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):
    router = route_aggregator

    @pytest.mark.parametrize("user_list", [VALID_LIST_A])
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_middleware_hit(self, get_token_claims, arborist, user_list, client):
        # todo: test that this is called before every endpoint
        headers = {"Authorization": "Bearer ofa.valid.token"}
        assert NotImplemented

    @pytest.mark.parametrize("user_list", [VALID_LIST_A])
    @pytest.mark.parametrize("endpoint", ["/_version", "/_versions/",
                                          "/lists", "/lists/",
                                          "/lists/123e4567-e89b-12d3-a456-426614174000",
                                          "/lists/123e4567-e89b-12d3-a456-426614174000/"])
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_middleware_validated(self):
        # test _version, /lists, and /lists/id
        # /lists/123e4567-e89b-12d3-a456-426614174000
        assert NotImplemented
