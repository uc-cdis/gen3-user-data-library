import pytest
from fastapi import FastAPI

from gen3userdatalibrary.main import lifespan, get_app, make_metrics_app
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
            "gen3userdatalibrary.db.get_data_access_layer",
            side_effect=mock_get_data_access_layer,
            return_value=iter(["foo"]),
        )

    async def test_get_app(self):
        outcome = get_app()
        assert NotImplemented

    async def test_make_metrics_app(self):
        outcome = make_metrics_app()
        assert NotImplemented
