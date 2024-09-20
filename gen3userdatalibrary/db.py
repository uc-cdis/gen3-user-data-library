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
from functools import reduce
from typing import Dict, List, Optional, Tuple, Union
from fastapi import HTTPException
from jsonschema import ValidationError, validate
from sqlalchemy import text, delete, func, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import make_transient
from starlette import status
from sqlalchemy import inspect

from gen3userdatalibrary import config, logging
from gen3userdatalibrary.auth import get_lists_endpoint, get_list_by_id_endpoint
from gen3userdatalibrary.models import (
    ITEMS_JSON_SCHEMA_DRS,
    ITEMS_JSON_SCHEMA_GEN3_GRAPHQL,
    ITEMS_JSON_SCHEMA_GENERIC,
    UserList, BLACKLIST,
)

engine = create_async_engine(str(config.DB_CONNECTION_STRING), echo=True)

# creates AsyncSession instances
async_sessionmaker = async_sessionmaker(engine, expire_on_commit=False)


def remove_keys(d: dict, keys: list):
    return {k: v for k, v in d.items() if k not in keys}


async def try_conforming_list(user_id, user_list: dict) -> UserList:
    """
    Handler for modeling endpoint data into orm
    :param user_list:
    :param user_id: id of the list owner
    :return: dict that maps id -> user list
    """
    try:
        list_as_orm = await create_user_list_instance(user_id, user_list)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="must provide a unique name")
    except ValidationError as exc:
        logging.debug(f"Invalid user-provided data when trying to create lists for user {user_id}.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid list information provided", )
    except Exception as exc:
        logging.exception(f"Unknown exception {type(exc)} when trying to create lists for user {user_id}.")
        logging.debug(f"Details: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid list information provided")
    return list_as_orm


async def create_user_list_instance(user_id, user_list: dict):
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
                validate(instance=item_contents, schema=ITEMS_JSON_SCHEMA_GEN3_GRAPHQL,)
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
            "authz": [get_lists_endpoint(user_id)],
        },
        name=name,
        created_time=now,
        updated_time=now,
        items=user_list_items)
    return new_list


def find_differences(list_to_update, new_list):
    """Finds differences in attributes between two SQLAlchemy ORM objects of the same type."""
    mapper = inspect(list_to_update).mapper

    def add_difference(differences, attribute):
        attr_name = attribute.key
        value1 = getattr(list_to_update, attr_name)
        value2 = getattr(new_list, attr_name)
        if value1 != value2:
            differences[attr_name] = (value1, value2)
        return differences

    differences_between_lists = reduce(add_difference, mapper.attrs, {})
    return differences_between_lists


class DataAccessLayer:
    """
    Defines an abstract interface to manipulate the database. Instances are given a session to
    act within.
    """

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_user_list(self, user_id, user_list: dict) -> UserList:
        new_list = await try_conforming_list(user_id, user_list)
        return await self.persist_user_list(new_list, user_id)

    # todo bonus: we should have a way to ensure we are not doing multiple
    # updates to the db. ideally, each endpoint should query the db once.
    # less than ideally, it only writes to the db once
    async def persist_user_list(self, user_list: UserList, user_id):
        """

        :param user_list:
        :param user_id: user's id
        :return:
        """
        self.db_session.add(user_list)
        # correct authz with id, but flush to get the autoincrement id
        await self.db_session.flush()

        authz = {
            "version": 0,
            "authz": [get_list_by_id_endpoint(user_id, user_list.id)],
        }
        user_list.authz = authz
        return user_list

    async def create_user_lists(self, user_id, user_lists: List[dict]) -> Dict[int, UserList]:
        """

        Note: if any items in any list fail, or any list fails to get created, no lists are created.
        """
        new_user_lists = {}

        # Validate the JSON objects
        for user_list in user_lists:
            new_list = await self.create_user_list(user_id, user_list)
            new_user_lists[new_list.id] = new_list
        return new_user_lists

    async def get_all_lists(self) -> List[UserList]:
        query = await self.db_session.execute(select(UserList).order_by(UserList.id))
        return list(query.scalars().all())

    async def get_list(self, identifier: Union[int, Tuple[str, str]], by="id") -> Optional[UserList]:
        if by == "name":  # assume identifier is (creator, name)
            query = select(UserList).filter(tuple_(UserList.creator, UserList.name).in_([identifier]))
        else:  # by id
            query = select(UserList).where(UserList.id == identifier)
        result = await self.db_session.execute(query)
        user_list = result.scalar_one_or_none()
        return user_list

    async def get_existing_list_or_throw(self, list_id: int) -> UserList:
        existing_record = await self.get_list(list_id)
        if existing_record is None:
            raise ValueError(f"No UserList found with id {list_id}")
        return existing_record

    async def update_and_persist_list(self, list_to_update: UserList, new_list: UserList) -> UserList:
        differences = find_differences(list_to_update, new_list)
        relevant_differences = remove_keys(differences, BLACKLIST)
        has_no_relevant_differences = not relevant_differences or (len(relevant_differences) == 1 and
                                                                   relevant_differences.__contains__("updated_time"))
        if has_no_relevant_differences:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing to update!")
        changes_to_make = {k: diff_tuple[1] for k, diff_tuple in relevant_differences.items()}
        db_list_to_update = await self.get_existing_list_or_throw(list_to_update.id)
        for key, value in changes_to_make.items():
            if hasattr(db_list_to_update, key):
                setattr(db_list_to_update, key, value)
        await self.db_session.commit()
        return db_list_to_update

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

    async def delete_list(self, list_id: int):
        count_query = select(func.count()).select_from(UserList).where(UserList.id == list_id)
        count_result = await self.db_session.execute(count_query)
        count = count_result.scalar()
        del_query = delete(UserList).where(UserList.id == list_id)
        count_query.execution_options(synchronize_session="fetch")
        await self.db_session.execute(del_query)
        await self.db_session.commit()
        return count

    async def replace_list(self, original_list_id, list_as_orm: UserList):
        """

        :param original_list_id:
        :param list_as_orm:
        :return:
        """
        existing_obj = await self.get_existing_list_or_throw(original_list_id)

        await self.db_session.delete(existing_obj)
        await self.db_session.commit()

        make_transient(list_as_orm)
        list_as_orm.id = None
        self.db_session.add(list_as_orm)
        await self.db_session.commit()
        return list_as_orm

    async def add_items_to_list(self, list_id: int, list_as_orm: UserList):
        user_list = await self.get_existing_list_or_throw(list_id)
        user_list.items.extend(list_as_orm.items)
        await self.db_session.commit()

    async def grab_all_lists_that_exist(self, by, identifier_list: Union[List[int], List[Tuple[str, str,]]]) \
            -> List[UserList]:
        if by == "name":  # assume identifier list = [(creator1, name1), ...]
            q = select(UserList).filter(tuple_(UserList.creator, UserList.name).in_(identifier_list))
        else:  # assume it's by id
            q = select(UserList).filter(UserList.id.in_(identifier_list))
        query_result = await self.db_session.execute(q)
        existing_user_lists = query_result.all()
        from_sequence_to_list = [row[0] for row in existing_user_lists]
        return from_sequence_to_list


async def get_data_access_layer() -> DataAccessLayer:
    """
    Create an AsyncSession and yield an instance of the Data Access Layer,
    which acts as an abstract interface to manipulate the database.

    Can be injected as a dependency in FastAPI endpoints.
    """
    async with async_sessionmaker() as session:
        async with session.begin():
            yield DataAccessLayer(session)
