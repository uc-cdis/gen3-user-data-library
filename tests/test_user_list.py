import pytest

from gen3userdatalibrary.models.user_list import is_dict, is_nonempty
from gen3userdatalibrary.routes import route_aggregator
from tests.routes.conftest import BaseTestRouter


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):
    router = route_aggregator

    def test_is_dict(self):
        outcome = is_dict(dict())

    def test_is_nonempty(self):
        outcome = is_nonempty("aaa")
