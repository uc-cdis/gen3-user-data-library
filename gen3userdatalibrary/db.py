"""
This file houses the database logic.
For schema/model of particular tables, go to `models.py`

OVERVIEW
--------

We're using SQLAlchemy's async support alongside FastAPI's dependency injection.

This file contains the logic for database manipulation in a "data access layer"
class, such that other areas of the code have simple `.create_list()` calls which
won't require knowledge on how to manage the session or interact with the db.
The session will be managed by dep injection of FastAPI's endpoints.
The logic that sets up the sessions is in this file.


DETAILS
-------
What do we do in this file?

- We create a sqlalchemy engine and session maker factory as globals
    - This reads in the db URL from config
- We define a data access layer class here which isolates the database manipulations
    - All CRUD operations go through this interface instead of bleeding specific database
      manipulations into the higher level web app endpoint code
- We create a function which yields an instance of the data access layer class with
  a fresh session from the session maker factory
    - This is what gets injected into endpoint code using FastAPI's dep injections
"""

import datetime
from typing import Dict, List, Optional

from fastapi import HTTPException
from jsonschema import ValidationError, validate
from sqlalchemy import text, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.future import select

from gen3userdatalibrary import config, logging
from gen3userdatalibrary.auth import get_user_id
from gen3userdatalibrary.models import (
    ITEMS_JSON_SCHEMA_DRS,
    ITEMS_JSON_SCHEMA_GEN3_GRAPHQL,
    ITEMS_JSON_SCHEMA_GENERIC,
    UserList,
)

engine = create_async_engine(str(config.DB_CONNECTION_STRING), echo=True)

# creates AsyncSession instances
async_sessionmaker = async_sessionmaker(engine, expire_on_commit=False)


async def create_user_list_instance(user_list: dict, user_id):
    now = datetime.datetime.now(datetime.timezone.utc)
    name = user_list.get("name", f"Saved List {now}")
    user_list_items = user_list.get("items", {})

    for _, item_contents in user_list_items.items():
        # TODO THIS NEEDS TO BE CFG
        if item_contents.get("type") == "GA4GH_DRS":
            try:
                validate(instance=item_contents, schema=ITEMS_JSON_SCHEMA_DRS)
            except ValidationError as e:
                logging.debug(f"User-provided JSON is invalid: {e.message}")
                raise
        elif item_contents.get("type") == "Gen3GraphQL":
            try:
                validate(
                    instance=item_contents,
                    schema=ITEMS_JSON_SCHEMA_GEN3_GRAPHQL,
                )
            except ValidationError as e:
                logging.debug(f"User-provided JSON is invalid: {e.message}")
                raise
        else:
            try:
                validate(
                    instance=item_contents,
                    schema=ITEMS_JSON_SCHEMA_GENERIC,
                )
            except ValidationError as e:
                logging.debug(f"User-provided JSON is invalid: {e.message}")
                raise

            logging.warning(
                "User-provided JSON is an unknown type. Creating anyway..."
            )

    if user_id is None:
        # TODO make this a reasonable error type
        raise Exception()
    new_list = UserList(
        version=0,
        creator=str(user_id),
        # temporarily set authz without the list ID since we haven't created the list in the db yet
        authz={
            "version": 0,
            "authz": [f"/users/{user_id}/user-data-library/lists"],
        },
        name=name,
        created_time=now,
        updated_time=now,
        items=user_list_items)
    return new_list


class DataAccessLayer():
    """
    Defines an abstract interface to manipulate the database. Instances are given a session to
    act within.
    """

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_user_list(self, user_list) -> UserList:
        user_id = await get_user_id()
        new_list = await create_user_list_instance(user_list, user_id)
        self.db_session.add(new_list)

        # correct authz with id, but flush to get the autoincrement id
        await self.db_session.flush()

        authz = {
            "version": 0,
            "authz": [f"/users/{user_id}/user-data-library/lists/{new_list.id}"],
        }
        new_list.authz = authz
        return new_list

    async def create_user_lists(self, user_lists: List[dict]) -> Dict[int, UserList]:
        """

        Note: if any items in any list fail, or any list fails to get created, no lists are created.
        """
        new_user_lists = {}

        # Validate the JSON objects
        for user_list in user_lists:
            new_list = await self.create_user_list(user_list)
            new_user_lists[new_list.id] = new_list
        return new_user_lists

    async def get_all_lists(self) -> List[UserList]:
        query = await self.db_session.execute(select(UserList).order_by(UserList.id))
        return list(query.scalars().all())

    async def update_list(
            self,
            list_id: int,
            user_list: UserList) -> UserList:
        q = select(UserList).where(UserList.id == list_id)
        result = await self.db_session.execute(q)
        existing_record = result.scalar_one_or_none()
        if existing_record is None:
            raise ValueError(f"No UserList found with id {list_id}")
        for attr in dir(user_list):
            if not attr.startswith('_') and hasattr(existing_record, attr):
                setattr(existing_record, attr, getattr(user_list, attr))
        existing_record.id = list_id
        await self.db_session.commit()
        return existing_record

    async def test_connection(self) -> None:
        await self.db_session.execute(text("SELECT 1;"))

    async def delete_all_lists(self, sub_id: str):
        query = select(func.count()).select_from(UserList).where(UserList.creator == sub_id)
        query.execution_options(synchronize_session="fetch")
        result = await self.db_session.execute(query)
        count = result.scalar()
        await self.db_session.execute(delete(UserList).where(UserList.creator == sub_id))
        await self.db_session.commit()
        return count

    async def get_list(self, list_id: int) -> UserList:
        query = select(UserList).where(UserList.id == list_id)
        result = await self.db_session.execute(query)
        user_list = result.scalar_one_or_none()  # Returns the first row or None if no match
        return user_list

    async def delete_list(self, list_id: int):
        count_query = select(func.count()).select_from(UserList).where(UserList.id == list_id)
        count_result = await self.db_session.execute(count_query)
        count = count_result.scalar()
        del_query = delete(UserList).where(UserList.id == list_id)
        count_query.execution_options(synchronize_session="fetch")
        await self.db_session.execute(del_query)
        await self.db_session.commit()
        return count

    async def get_list(self, list_id: int) -> UserList:
        query = select(UserList).where(UserList.id == list_id)
        result = await self.db_session.execute(query)
        user_list = result.scalar_one_or_none()  # Returns the first row or None if no match
        return user_list

    async def delete_list(self, list_id: int):
        count_query = select(func.count()).select_from(UserList).where(UserList.id == list_id)
        count_result = await self.db_session.execute(count_query)
        count = count_result.scalar()
        del_query = delete(UserList).where(UserList.id == list_id)
        count_query.execution_options(synchronize_session="fetch")
        await self.db_session.execute(del_query)
        await self.db_session.commit()
        return count


async def get_data_access_layer() -> DataAccessLayer:
    """
    Create an AsyncSession and yield an instance of the Data Access Layer,
    which acts as an abstract interface to manipulate the database.

    Can be injected as a dependency in FastAPI endpoints.
    """
    async with async_sessionmaker() as session:
        async with session.begin():
            yield DataAccessLayer(session)
