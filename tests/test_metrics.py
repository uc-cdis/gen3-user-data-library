import pytest

from gen3userdatalibrary.metrics import Metrics
from gen3userdatalibrary.routes import route_aggregator
from tests.routes.conftest import BaseTestRouter


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):
    router = route_aggregator

    async def test_add_user_list_counter(self):
        metrics_disabled = Metrics("/foo", False)
        metrics_disabled.add_user_list_counter()
        metrics_enabled = Metrics("/bar", True)
        with pytest.raises(ValueError):
            metrics_enabled.add_user_list_counter()

    async def test_add_user_list_item_counter(self):
        metrics_disabled = Metrics("/foo", False)
        metrics_disabled.add_user_list_item_counter()
        metrics_enabled = Metrics("/bar", True)
        with pytest.raises(ValueError):
            metrics_enabled.add_user_list_item_counter()
