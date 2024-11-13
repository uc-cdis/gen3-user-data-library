import pytest
from fastapi import FastAPI

from gen3userdatalibrary.db import DataAccessLayer
from gen3userdatalibrary.main import lifespan, get_app
from gen3userdatalibrary.routes import route_aggregator
from tests.routes.conftest import BaseTestRouter


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):
    router = route_aggregator

    async def test_lifespan(self, mocker):
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
        with pytest.raises(Exception):
            async with lifespan(app) as _:
                assert True
        mocker.patch(
            "gen3userdatalibrary.main.lifespan",
            side_effect=iter([DataAccessLayer("foo")]),
            return_value=iter(["foo"]),
        )
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

    async def test_get_app(self, mocker):
        mock_schema = mocker.patch(
            "gen3userdatalibrary.config.ENABLE_PROMETHEUS_METRICS", True
        )
        with pytest.raises(ValueError):
            outcome = get_app()
