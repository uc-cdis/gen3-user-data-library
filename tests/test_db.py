import pytest
from fastapi import HTTPException

from gen3userdatalibrary import config
from gen3userdatalibrary.db import DataAccessLayer
from gen3userdatalibrary.models.helpers import create_user_list_instance
from gen3userdatalibrary.models.user_list import ItemToUpdateModel
from gen3userdatalibrary.routes import route_aggregator
from tests.routes.conftest import BaseTestRouter


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):
    router = route_aggregator

    async def test_ensure_user_has_not_reached_max_lists(self, session, monkeypatch):
        previous_config = config.MAX_LISTS
        monkeypatch.setattr(config, "MAX_LISTS", 1)
        dal = DataAccessLayer(session)
        outcome = await dal.ensure_user_has_not_reached_max_lists("1", 1)
        monkeypatch.setattr(config, "MAX_LISTS", 0)
        with pytest.raises(HTTPException):
            outcome = await dal.ensure_user_has_not_reached_max_lists("1", 1)
        monkeypatch.setattr(config, "MAX_LISTS", previous_config)

    async def test_persist_user_list(self, session):
        example_user_list = create_user_list_instance(
            "0",
            ItemToUpdateModel(
                name="fizzbuzz",
                items={},
            ),
        )
        dal = DataAccessLayer(session)
        outcome = await dal.persist_user_list("0", example_user_list)
