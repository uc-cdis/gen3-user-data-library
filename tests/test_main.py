import pytest
from fastapi import FastAPI

from gen3userdatalibrary import main
from gen3userdatalibrary.routes import route_aggregator
from tests.routes.conftest import BaseTestRouter


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):
    router = route_aggregator

    async def test_lifespan(self):
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
        )

        outcome = main.lifespan(app)
        assert NotImplemented
        assert NotImplemented

    async def test_get_app(self):
        assert NotImplemented

    async def test_make_metrics_app(self):
        assert NotImplemented
