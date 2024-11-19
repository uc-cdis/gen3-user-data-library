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

from typing import List, Optional, Tuple, Union
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text, delete, func, tuple_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.future import select
from starlette import status

from gen3userdatalibrary import config
from gen3userdatalibrary.auth import get_list_by_id_endpoint
from gen3userdatalibrary.models.user_list import UserList

engine = create_async_engine(str(config.DB_CONNECTION_STRING), echo=True)

# creates AsyncSession instances
async_sessionmaker = async_sessionmaker(engine, expire_on_commit=False)


class DataAccessLayer:
    """
    Defines an abstract interface to manipulate the database. Instances are given a session to
    act within.
    """

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def ensure_user_has_not_reached_max_lists(self, creator_id, lists_to_add=0):
        """

        Args:
            creator_id: matching name of whoever made the list
            lists_to_add: number of lists to add to existing user's list set
        """
        lists_so_far = await self.get_list_count_for_creator(creator_id)
        total = lists_so_far + lists_to_add
        if total > config.MAX_LISTS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Max number of lists reached!",
            )

    async def persist_user_list(self, user_id, user_list: UserList):
        """
        Save user list to db as well as update authz

        Args:
            user_id: same as creator id
            user_list: data object of the UserList type
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

    async def get_all_lists(self, creator_id) -> List[UserList]:
        """
        Return all known lists

        Args:
            creator_id: matching name of whoever made the list
        """
        query = (
            select(UserList).order_by(UserList.id).where(UserList.creator == creator_id)
        )
        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def get_list(
        self, identifier: Union[UUID, Tuple[str, str]], by="id"
    ) -> Optional[UserList]:
        """
        Get a list by either unique id or unique (creator, name) combo

        Args:
            identifier: this can either be the list UUID, or a tuple in the form (creator id, list name)
            by: how do you want to identify the list? currently only checks for "name"
        """
        if by == "name":  # assume identifier is (creator, name)
            query = select(UserList).filter(
                tuple_(UserList.creator, UserList.name).in_([identifier])
            )
        else:  # by id
            query = select(UserList).where(UserList.id == identifier)
        result = await self.db_session.execute(query)
        user_list = result.scalar_one_or_none()
        return user_list

    async def get_existing_list_or_throw(self, list_id: UUID) -> UserList:
        """
        List SHOULD exist, so throw if it doesn't

        Args:
            list_id: UUID of the list
        """
        existing_record = await self.get_list(list_id)
        if existing_record is None:
            raise ValueError(f"No UserList found with id {list_id}")
        return existing_record

    async def update_and_persist_list(
        self, list_to_update_id, changes_to_make
    ) -> UserList:
        """
        Given an id and list of changes to make, it'll update the list orm with those changes.
        IMPORTANT! Does not check that the attributes are safe to change.
        Refer to the ALLOW_LIST variable in data.py for unsafe properties

        Args:
            list_to_update_id: uuid of list to update
            changes_to_make: contents that go into corresponding UserList properties with their associated names
        """
        db_list_to_update = await self.get_existing_list_or_throw(list_to_update_id)
        changes_that_can_be_made = list(
            filter(
                lambda kvp: hasattr(db_list_to_update, kvp[0]), changes_to_make.items()
            )
        )
        for key, value in changes_that_can_be_made:
            setattr(db_list_to_update, key, value)
        # await self.db_session.commit()
        return db_list_to_update

    async def test_connection(self) -> None:
        """
        Ensure we can actually communicate with the db
        """
        await self.db_session.execute(text("SELECT 1;"))

    async def get_list_count_for_creator(self, creator_id):
        """
        Args:
            creator_id: matching name of whoever made the list

        Returns:
            the number of lists associated with that creator
        """
        query = (
            select(func.count())
            .select_from(UserList)
            .where(UserList.creator == creator_id)
        )
        result = await self.db_session.execute(query)
        count = result.scalar()
        count = count or 0
        return count

    async def delete_all_lists(self, sub_id: str):
        """
        Delete all lists for a given list creator, return how many lists were deleted

        Args:
            sub_id: id of creator
        """
        count = await self.get_list_count_for_creator(sub_id)
        query = delete(UserList).where(UserList.creator == sub_id)
        query.execution_options(synchronize_session="fetch")
        await self.db_session.execute(query)
        return count

    async def delete_list(self, list_id: UUID):
        """
        Delete a specific list given its ID

        Args:
            list_id: id of list
        """
        count_query = (
            select(func.count()).select_from(UserList).where(UserList.id == list_id)
        )
        count_result = await self.db_session.execute(count_query)
        count = count_result.scalar()
        del_query = delete(UserList).where(UserList.id == list_id)
        count_query.execution_options(synchronize_session="fetch")
        await self.db_session.execute(del_query)
        # await self.db_session.commit()
        return count

    async def add_items_to_list(self, list_id: UUID, item_data: dict):
        """
        Gets existing list and adds items to the items property
        # yes, it has automatic sql injection protection

        Args:
            list_id: id of list
            item_data: dict of items to add to item component of list
        """
        user_list = await self.get_existing_list_or_throw(list_id)
        user_list.items.update(item_data)
        return user_list

    async def grab_all_lists_that_exist(
        self,
        by,
        identifier_list: Union[
            List[int],
            List[
                Tuple[
                    str,
                    str,
                ]
            ],
        ],
    ) -> List[UserList]:
        """
        Get all lists that match the identifier list, whether that be the ids or creator/name combo

        Args:
            by: checks only name, but determines how lists are retrieved
            identifier_list: can be either a list of ids or (creator, name) pairs
        """
        if by == "name":  # assume identifier list = [(creator1, name1), ...]
            q = select(UserList).filter(
                tuple_(UserList.creator, UserList.name).in_(identifier_list)
            )
        else:  # assume it's by id
            q = select(UserList).filter(UserList.id.in_(identifier_list))
        query_result = await self.db_session.execute(q)
        existing_user_lists = query_result.all()
        from_sequence_to_list = [row[0] for row in existing_user_lists]
        return from_sequence_to_list

    async def replace_list(self, new_list_as_orm: UserList, existing_obj: UserList):
        """
        Delete the original list, replace it with the new one!
        Does not check that list exists

        """
        await self.db_session.delete(existing_obj)
        await self.db_session.flush()
        self.db_session.add(new_list_as_orm)
        await self.db_session.flush()
        return new_list_as_orm


async def get_data_access_layer() -> DataAccessLayer:
    """
    Create an AsyncSession and yield an instance of the Data Access Layer,
    which acts as an abstract interface to manipulate the database.

    Can be injected as a dependency in FastAPI endpoints.
    """
    async with async_sessionmaker() as session:
        async with session.begin():
            yield DataAccessLayer(session)
