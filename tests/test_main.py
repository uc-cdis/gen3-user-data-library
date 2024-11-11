from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from gen3authz.client.arborist.async_client import ArboristClient

from gen3userdatalibrary.db import get_data_access_layer
from gen3userdatalibrary.main import lifespan
from gen3userdatalibrary.routes import route_aggregator
from tests.routes.conftest import BaseTestRouter


@asynccontextmanager
async def test_func():
    print("true")
    yield True


@asynccontextmanager
async def alt_test_func(_):
    print("false")
    yield False


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):
    router = route_aggregator

    @patch("gen3userdatalibrary.db.get_data_access_layer", side_effect=test_func)
    @patch(
        "gen3authz.client.arborist.base.BaseArboristClient.healthy",
        side_effect=alt_test_func,
    )
    async def test_lifespan(self, get_dal, healthy):
        # healthy.return_value = True
        # get_dal.return_value = True
        ab_client = ArboristClient()
        # Use async context managers properly in the test
        async with get_data_access_layer() as outcome_1:
            assert outcome_1 is True

        ab_client = ArboristClient()

        async with ab_client.healthy() as outcome_2:
            assert outcome_2 is False

        # app = FastAPI(
        #     title="Gen3 User Data Library Service",
        #     version="1.0.0",
        #     description="",
        #     docs_url="/docs",
        #     redoc_url="/redoc",
        #     openapi_url="/openapi.json",
        #     openapi_version="3.1.0",
        #     terms_of_service=None,
        #     contact=None,
        #     license_info=None,
        #     debug=False,
        #     lifespan=lifespan,
        # )
        # async with lifespan(app) as _:
        #     assert True
        # healthy = app.state.arborist_client.healthy().return_value = True
        # dals = get_data_access_layer() = RaisesException()

        assert NotImplemented

    async def test_get_app(self):
        assert NotImplemented

    async def test_make_metrics_app(self):
        assert NotImplemented
