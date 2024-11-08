import pytest
from gen3userdatalibrary.routes import route_aggregator
from tests.routes.conftest import BaseTestRouter


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):
    router = route_aggregator

    def test_is_dict(self):
        assert NotImplemented

    def test_is_nonempty(self):
        assert NotImplemented
