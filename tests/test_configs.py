import importlib
import os
from json import JSONDecodeError
from unittest.mock import AsyncMock, patch

import pytest

from gen3userdatalibrary import config
from gen3userdatalibrary.main import route_aggregator
from gen3userdatalibrary.utils.metrics import get_from_cfg_metadata
from tests.data.example_lists import VALID_LIST_A
from tests.routes.conftest import BaseTestRouter


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):
    router = route_aggregator

    async def test_item_schema_validation(self):
        with pytest.raises(ValidationError):
            outcome = validate_user_list_item(VALID_LIST_A)

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

    async def test_config(self, mocker):
        old_env = os.environ.get("ENV", "test")
        os.environ["ENV"] = "foo"
        importlib.reload(config)
        test_dir = os.path.dirname(os.path.realpath(__file__))
        test_path = os.path.abspath(f"{test_dir}/../.env")
        assert config.PATH == test_path
        os.environ["ENV"] = old_env
        # ---

        mock_schema = mocker.patch(
            "gen3userdatalibrary.config.ITEM_SCHEMAS", return_value={"None": "bah"}
        )
        importlib.reload(config)
        item_schema = config.ITEM_SCHEMAS
        assert None in item_schema
        mock_file = mocker.patch("os.path.isfile", return_value=False)
        with pytest.raises(OSError):
            importlib.reload(config)
        assert config.ITEM_SCHEMAS is None

        mock_file = mocker.patch("os.path.isfile", return_value=True)
        mock_load = mocker.patch("json.load")
        mock_load.side_effect = JSONDecodeError("msg", "doc", 0)
        with pytest.raises(OSError):
            importlib.reload(config)
