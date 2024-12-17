"""
This is modeled after docs and articles showing how to properly setup testing
using async sqlalchemy, while properly ensuring isolation between the tests.

Ultimately, these are fixtures used by the tests which handle the isolation behind the scenes,
by using properly scoped fixtures with cleanup/teardown.

More info on how this setup works:

- Creates a session-level, shared event loop
- The "session" uses a fuction-scoped engine + the shared session event loop
    - Function-scoped engine clears out the database at the beginning and end to ensure test isolation
        - This could maybe be set at the class level or higher, but without running into major performance issues,
          I think it's better to ensure a full cleanup between tests
    - session uses a nested transaction, which it starts but then rolls back after the test (meaning that
      any changes should be isolated)
"""

import asyncio
import importlib
import os
from asyncio import current_task

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
    async_scoped_session,
)

from gen3userdatalibrary import config
from gen3userdatalibrary.models.user_list import Base


@pytest.fixture(scope="session", autouse=True)
def ensure_test_config():
    is_test = os.environ.get("ENV", None) == "test" or config.ENV == "test"
    if not is_test:
        os.chdir(os.path.dirname(os.path.abspath(__file__)).rstrip("/"))
        importlib.reload(config)
        assert not config.DEBUG_SKIP_AUTH


@pytest_asyncio.fixture(scope="function")
async def engine():
    """
    Non-session scoped engine which recreates the database, yields, then drops the tables
    """
    engine = create_async_engine(
        str(config.DB_CONNECTION_STRING), echo=False, future=True
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture()
async def session(engine):
    """
    Database session which utilizes the above engine and event loop and sets up a nested transaction before yielding.
    It rolls back the nested transaction after yield.
    """
    event_loop = asyncio.get_running_loop()
    session_maker = async_sessionmaker(
        engine, expire_on_commit=False, autocommit=False, autoflush=False
    )

    async with engine.connect() as conn:
        transaction = await conn.begin()
        async with session_maker(bind=conn) as session:
            yield session

            await transaction.rollback()


@pytest_asyncio.fixture(scope="function")
async def db_session_factory(engine):
    """returns  a sql alchemy scoped session factory"""

    session_maker = async_sessionmaker(
        engine, expire_on_commit=False, autocommit=False, autoflush=False
    )
    scoped_maker = async_scoped_session(session_maker, current_task)
    return scoped_maker


@pytest_asyncio.fixture(scope="function")
async def alt_session(db_session_factory):
    """
    Creates a setup to allow for a basic, direct interface with DAL functions (when passed in to an instance)
    Args:
        db_session_factory: scoped session fixture from above

    Returns:
        yields a session instance
    """
    session_ = db_session_factory()
    yield session_

    await session_.rollback()
    await session_.close()
