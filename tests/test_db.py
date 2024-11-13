import pytest
from fastapi import Depends

from gen3userdatalibrary.db import get_data_access_layer, DataAccessLayer
from gen3userdatalibrary.routes import route_aggregator
from tests.routes.conftest import BaseTestRouter


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):
    router = route_aggregator

    async def test_ensure_user_has_not_reached_max_lists(
        self,
        data_access_layer: DataAccessLayer = Depends(get_data_access_layer),
    ):
        assert NotImplemented
        # How do I test the DAL functions?
        # async for e in get_data_access_layer():
        #     outcome = await data_access_layer.ensure_user_has_not_reached_max_lists(
        #         "foo", 1
        #     )
        #     assert outcome == 1
