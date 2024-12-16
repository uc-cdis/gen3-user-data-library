from datetime import datetime
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from gen3userdatalibrary import config
from gen3userdatalibrary.auth import get_lists_endpoint
from gen3userdatalibrary.db import DataAccessLayer
from gen3userdatalibrary.main import route_aggregator
from gen3userdatalibrary.models.helpers import create_user_list_instance
from gen3userdatalibrary.models.user_list import ItemToUpdateModel, UserList
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

    async def test_persist_user_list(self, alt_session):
        dal = DataAccessLayer(alt_session)
        outcome = await dal.persist_user_list("0", EXAMPLE_USER_LIST())
        assert outcome.id is not None

    async def test_get_list_or_none(self, alt_session):
        dal = DataAccessLayer(alt_session)
        l_id = "550e8400-e29b-41d4-a716-446655440000"
        get_before_create_outcome = await dal.get_list_or_none(
            select(UserList).where(UserList.id == UUID(l_id))
        )
        assert get_before_create_outcome is None

        create_outcome = await dal.persist_user_list("0", EXAMPLE_USER_LIST())
        l_id = create_outcome.id
        get_after_create_outcome = await dal.get_list_or_none(
            select(UserList).where(UserList.id == l_id)
        )
        assert get_after_create_outcome is not None

    async def test_get_list_by_name_and_creator(self, alt_session):
        dal = DataAccessLayer(alt_session)
        get_before_create_outcome = await dal.get_list_by_name_and_creator(
            ("foo", "bar")
        )
        assert get_before_create_outcome is None

        create_outcome = await dal.persist_user_list("0", EXAMPLE_USER_LIST())
        get_after_create_outcome = await dal.get_list_by_name_and_creator(
            ("0", "fizzbuzz")
        )
        assert get_after_create_outcome is not None

    async def test_get_existing_list_or_throw(self, alt_session):
        dal = DataAccessLayer(alt_session)
        l_id = "550e8400-e29b-41d4-a716-446655440000"
        with pytest.raises(ValueError):
            fail_outcome = await dal.get_existing_list_or_throw(UUID(l_id))
        create_outcome = await dal.persist_user_list("0", EXAMPLE_USER_LIST())
        success_outcome = await dal.get_existing_list_or_throw(create_outcome.id)

    async def test_update_and_persist_list(self, alt_session):
        dal = DataAccessLayer(alt_session)
        l_id = "550e8400-e29b-41d4-a716-446655440000"
        with pytest.raises(ValueError):
            outcome1 = await dal.update_and_persist_list(UUID(l_id), {"name": "abcd"})
        example = UserList(
            version=0,
            creator=str("1"),
            # temporarily set authz without the list list_id since we haven't created the list in the db yet
            authz={"version": 0, "authz": [get_lists_endpoint("1")]},
            name="aaa",
            created_time=datetime.now(),
            updated_time=datetime.now(),
            items={"foo": "bar"},
        )
        outcome2 = await dal.persist_user_list("1", example)
        outcome3 = await dal.update_and_persist_list(outcome2.id, {"name": "abcd"})
        outcome4 = await dal.get_user_list_by_list_id(outcome3.id)
        assert outcome4.name == "abcd"

    async def test_delete_all_lists(self, alt_session):
        dal = DataAccessLayer(alt_session)
        create_outcome = await dal.persist_user_list("1", EXAMPLE_USER_LIST())
        get_before_delete_outcome = await dal.get_user_list_by_list_id(
            create_outcome.id
        )
        assert get_before_delete_outcome.id is not None
        delete_outcome = await dal.delete_all_lists("1")
        get_after_delete_outcome = await dal.get_all_lists("1")
        assert get_after_delete_outcome == []

    async def test_delete_list(self, alt_session):
        dal = DataAccessLayer(alt_session)
        create_outcome = await dal.persist_user_list("1", EXAMPLE_USER_LIST())
        get_before_delete_outcome = await dal.get_user_list_by_list_id(
            create_outcome.id
        )
        assert get_before_delete_outcome.id is not None
        outcome = await dal.delete_list(create_outcome.id)
        get_after_delete_outcome = await dal.get_user_list_by_list_id(create_outcome.id)
        assert get_after_delete_outcome is None

    async def test_add_items_to_list(self, alt_session):
        dal = DataAccessLayer(alt_session)
        l_id = "550e8400-e29b-41d4-a716-446655440000"
        with pytest.raises(ValueError):
            add_fail_outcome = await dal.add_items_to_list(UUID(l_id), {})
        create_outcome = await dal.persist_user_list("1", EXAMPLE_USER_LIST())
        add_success_outcome = await dal.add_items_to_list(
            create_outcome.id, {"foo": "bar"}
        )
        get_outcome = await dal.get_user_list_by_list_id(create_outcome.id)
        assert get_outcome.items.get("foo", None) is not None

    async def test_grab_all_lists_that_exist(self, alt_session):
        dal = DataAccessLayer(alt_session)
        l_id = "550e8400-e29b-41d4-a716-446655440000"
        grab_before_create_outcome = await dal.grab_all_lists_that_exist(
            "id", [UUID(l_id)]
        )
        assert grab_before_create_outcome == []

        create_outcome_1 = await dal.persist_user_list("0", EXAMPLE_USER_LIST())
        alt_example_list = EXAMPLE_USER_LIST()
        alt_example_list.name = "other list"
        alt_example_list.items = {"random": "text"}
        create_outcome_2 = await dal.persist_user_list("0", alt_example_list)
        grab_before_create_outcome = await dal.grab_all_lists_that_exist(
            "id", [create_outcome_1.id, create_outcome_2.id]
        )
        list_ids = set(map(lambda ul: ul.id, grab_before_create_outcome))
        assert list_ids == {create_outcome_1.id, create_outcome_2.id}

    async def test_replace_list(self, alt_session):
        dal = DataAccessLayer(alt_session)
        old_list = UserList(
            version=0,
            creator=str("1"),
            authz={"version": 0, "authz": [get_lists_endpoint("1")]},
            name="aaa",
            created_time=datetime.now(),
            updated_time=datetime.now(),
            items={"foo": "bar"},
        )
        create_outcome = await dal.persist_user_list("1", old_list)
        new_list = UserList(
            version=0,
            creator=str("1"),
            authz={"version": 0, "authz": [get_lists_endpoint("1")]},
            name="bbb",
            created_time=datetime.now(),
            updated_time=datetime.now(),
            items={"fizz": "buzz"},
        )
        replace_outcome = await dal.change_list_contents(new_list, old_list)
        get_outcome = await dal.get_user_list_by_list_id(replace_outcome[0].id)
        assert get_outcome is not None


EXAMPLE_USER_LIST = lambda: create_user_list_instance(
    "0",
    ItemToUpdateModel(
        name="fizzbuzz",
        items={"fizz": "buzz"},
    ),
)
