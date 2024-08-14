import importlib
import os
from unittest.mock import patch

import pytest
from tests.routes.conftest import BaseTestRouter

from gen3userdatalibrary import config
from gen3userdatalibrary.main import root_router
from gen3userdatalibrary.utils import get_from_cfg_metadata


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):
    router = root_router

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
    async def test_docs(self, endpoint, client):
        """
        Test FastAPI docs endpoints
        """
        response = await client.get(endpoint)
        assert response.status_code == 200
