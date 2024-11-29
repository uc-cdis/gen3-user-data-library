import os
from unittest.mock import patch, AsyncMock

import pytest
from fastapi import FastAPI

from gen3userdatalibrary import config
from gen3userdatalibrary.db import DataAccessLayer
from gen3userdatalibrary.main import lifespan, get_app, check_db_connection
from gen3userdatalibrary.routes import route_aggregator
from tests.routes.conftest import BaseTestRouter


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):

    router = route_aggregator

    async def test_lifespan(self, mocker, monkeypatch, app_client_pair):
        previous_config = config.DEBUG_SKIP_AUTH
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", False)

        app = FastAPI(
            title="Gen3 User Data Library Service",
            version="1.0.0",
            description="",
            docs_url="/docs",
            redoc_url="/redoc",
            openapi_url="/openapi.json",
            openapi_version="3.1.0",
            terms_of_service=None,
            contact=None,
            license_info=None,
            debug=False,
            lifespan=lifespan,
        )
        mocker.patch(
            "gen3authz.client.arborist.client.ArboristClient.healthy",
            side_effect=iter([False]),
            return_value=iter([False]),
        )
        # todo: suppress errors
        with pytest.raises(Exception):
            async with lifespan(app) as _:
                assert True
        mocker.patch(
            "gen3userdatalibrary.db.DataAccessLayer.test_connection",
            side_effect=iter([DataAccessLayer("foo")]),
            return_value=iter(["bar"]),
        )
        mocker.patch(
            "gen3authz.client.arborist.client.ArboristClient.healthy",
            side_effect=iter([True]),
            return_value=iter([True]),
        )
        async with lifespan(app) as _:
            assert True
        monkeypatch.setattr(config, "DEBUG_SKIP_AUTH", previous_config)

    async def test_get_app(self, mocker):
        mock_schema = mocker.patch(
            "gen3userdatalibrary.config.ENABLE_PROMETHEUS_METRICS", True
        )
        assert config.ENABLE_PROMETHEUS_METRICS is True
        original_prometheus_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
        original_dir = os.getcwd()

        os.environ["PROMETHEUS_MULTIPROC_DIR"] = "bash"
        current_dir = os.path.dirname(os.path.abspath(__file__))
        current_dir_without_slash = current_dir.rstrip("/")
        parent_dir = os.path.dirname(current_dir_without_slash)
        os.chdir(parent_dir)
        try:
            outcome = get_app()
        finally:
            if original_prometheus_dir is not None:
                os.environ["PROMETHEUS_MULTIPROC_DIR"] = original_prometheus_dir
            else:
                del os.environ["PROMETHEUS_MULTIPROC_DIR"]
            os.chdir(original_dir)
        assert isinstance(outcome, FastAPI)

    async def test_get_app_with_prometheus(self, mocker, monkeypatch):
        previous_config = config.ENABLE_PROMETHEUS_METRICS
        monkeypatch.setattr(config, "ENABLE_PROMETHEUS_METRICS", False)

        mock_schema = mocker.patch(
            "gen3userdatalibrary.config.ENABLE_PROMETHEUS_METRICS", True
        )
        assert config.ENABLE_PROMETHEUS_METRICS is True
        original_prometheus_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
        original_dir = os.getcwd()

        os.environ["PROMETHEUS_MULTIPROC_DIR"] = "bash"
        current_dir = os.path.dirname(os.path.abspath(__file__))
        current_dir_without_slash = current_dir.rstrip("/")
        parent_dir = os.path.dirname(current_dir_without_slash)
        os.chdir(parent_dir)
        try:
            outcome = get_app()
        finally:
            if original_prometheus_dir is not None:
                os.environ["PROMETHEUS_MULTIPROC_DIR"] = original_prometheus_dir
            else:
                del os.environ["PROMETHEUS_MULTIPROC_DIR"]
            os.chdir(original_dir)
        assert isinstance(outcome, FastAPI)
        monkeypatch.setattr(config, "ENABLE_PROMETHEUS_METRICS", previous_config)

    @patch("gen3userdatalibrary.main.get_data_access_layer")
    async def test_check_db_connection(self, mock_get_dal):
        mock_dal = AsyncMock()
        mock_dal.test_connection.return_value = True

        async def mock_dal_context():
            yield mock_dal

        mock_get_dal.return_value = mock_dal_context()
        await check_db_connection()
        mock_dal.test_connection.assert_called_once()
