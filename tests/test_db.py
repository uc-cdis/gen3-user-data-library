from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.sql.functions import now

from gen3userdatalibrary import config
from gen3userdatalibrary.auth import get_lists_endpoint
from gen3userdatalibrary.db import DataAccessLayer
from gen3userdatalibrary.models.helpers import create_user_list_instance
from gen3userdatalibrary.models.user_list import ItemToUpdateModel, UserList
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

    async def test_get_list_or_none(self, session):
        dal = DataAccessLayer(session)
        l_id = "550e8400-e29b-41d4-a716-446655440000"
        outcome = await dal.get_list_or_none(
            select(UserList).where(UserList.id == UUID(l_id))
        )

    async def test_get_list_by_name_and_creator(self, session):
        dal = DataAccessLayer(session)
        outcome = await dal.get_list_by_name_and_creator(("", ""))

    async def test_get_existing_list_or_throw(self, session):
        dal = DataAccessLayer(session)
        l_id = "550e8400-e29b-41d4-a716-446655440000"
        with pytest.raises(ValueError):
            outcome = await dal.get_existing_list_or_throw(UUID(l_id))

    async def test_update_and_persist_list(self, session):
        dal = DataAccessLayer(session)
        new_list = UserList(
            version=0,
            creator=str("1"),
            # temporarily set authz without the list list_id since we haven't created the list in the db yet
            authz={"version": 0, "authz": [get_lists_endpoint("1")]},
            name="aaa",
            created_time=now,
            updated_time=now,
            items={"foo": "bar"},
        )
        outcome = await dal.update_and_persist_list(new_list, {"name": "abcd"})

    async def test_delete_all_lists(self, session):
        dal = DataAccessLayer(session)
        outcome = await dal.delete_all_lists("1")

    async def test_delete_list(self, session):
        dal = DataAccessLayer(session)
        l_id = "550e8400-e29b-41d4-a716-446655440000"
        outcome = await dal.delete_list(UUID(l_id))

    async def test_add_items_to_list(self, session):
        dal = DataAccessLayer(session)
        l_id = "550e8400-e29b-41d4-a716-446655440000"
        outcome = await dal.add_items_to_list(UUID(l_id), {})

    async def test_grab_all_lists_that_exist(self, session):
        dal = DataAccessLayer(session)
        outcome = await dal.grab_all_lists_that_exist("id", [1])

    async def test_replace_list(self, session):
        dal = DataAccessLayer(session)
        outcome = await dal.replace_list(UserList(), UserList())
