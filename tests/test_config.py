import importlib
import os
from unittest.mock import patch

import pytest

from gen3userdatalibrary import config
from gen3userdatalibrary.main import _override_generated_openapi_spec
from gen3userdatalibrary.utils import get_from_cfg_metadata
from gen3userdatalibrary.main import root_router
from tests.routes.conftest import BaseTestRouter


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):
    router = root_router

    async def test_bad_config_metadata(self):
        """
        Test when invalid config is provided, an exception is raised
        """
        # change dir to the tests, so it loads the test .env
        os.chdir(os.path.dirname(os.path.abspath(__file__)).rstrip("/") + "/badcfg")

        with pytest.raises(Exception):
            importlib.reload(config)

        os.chdir(os.path.dirname(os.path.abspath(__file__)).rstrip("/") + "/..")

    async def test_metadata_cfg_util(self):
        """
        If it exists, return it
        """
        set_metadata_value = "foobar"
        metadata = {"model_name": set_metadata_value}
        retrieved_metadata_value = get_from_cfg_metadata(
            "model_name", metadata, default="chat-bison", type_=str
        )

        assert retrieved_metadata_value == set_metadata_value

    async def test_metadata_cfg_util_doesnt_exist(self):
        """
        If it doesn't exist, return default
        """
        default = "chat-bison"
        retrieved_metadata_value = get_from_cfg_metadata(
            "this_doesnt_exist", {"model_name": "foobar"}, default=default, type_=str
        )
        assert retrieved_metadata_value == default

    async def test_metadata_cfg_util_cant_cast(self):
        """
        If it doesn't exist, return default
        """
        default = "chat-bison"
        retrieved_metadata_value = get_from_cfg_metadata(
            "this_doesnt_exist", {"model_name": "foobar"}, default=default, type_=float
        )
        assert retrieved_metadata_value == default

    @pytest.mark.parametrize("endpoint", ["/docs", "/redoc"])
    async def test_docs(self, endpoint, client):
        """
        Test FastAPI docs endpoints
        """
        assert await client.get(endpoint).status_code == 200

    async def test_openapi(self):
        """
        Test our override of FastAPI's default openAPI
        """
        # change dir so the oldopenapi.yaml is available
        current_dir = os.path.dirname(os.path.abspath(__file__)).rstrip("/")
        os.chdir(current_dir + "/..")

        json_data = _override_generated_openapi_spec()
        assert json_data

        # change dir so the oldopenapi.yaml CANNOT be found
        os.chdir("./tests")

        json_data = _override_generated_openapi_spec()
        assert not json_data
