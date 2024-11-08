import pytest
from gen3userdatalibrary.routes import route_aggregator
from tests.routes.conftest import BaseTestRouter


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):
    router = route_aggregator

    async def test_add_user_list_counter(self):
        assert NotImplemented

    async def test_add_user_list_item_counter(self):
        assert NotImplemented
