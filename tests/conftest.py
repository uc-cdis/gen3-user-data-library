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

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from gen3userdatalibrary import config
from gen3userdatalibrary.models import Base


@pytest.fixture(scope="session", autouse=True)
def ensure_test_config():
    os.chdir(os.path.dirname(os.path.abspath(__file__)).rstrip("/"))
    importlib.reload(config)
    assert not config.DEBUG_SKIP_AUTH


@pytest_asyncio.fixture(scope="function")
async def engine():
    """
    Non-session scoped engine which recreates the database, yields, then drops the tables
    """
    engine = create_async_engine(str(config.DB_CONNECTION_STRING), echo=False, future=True)

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
    session_maker = async_sessionmaker(engine, expire_on_commit=False,
                                       autocommit=False, autoflush=False)

    async with engine.connect() as conn:
        tsx = await conn.begin()
        async with session_maker(bind=conn) as session:
            yield session

            await tsx.rollback()
