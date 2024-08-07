import importlib
import os

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from gen3userdatalibrary.models import Base
from gen3userdatalibrary import config
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


# https://medium.com/@lawsontaylor/the-ultimate-fastapi-project-setup-fastapi-async-postgres-sqlmodel-pytest-and-docker-ed0c6afea11b
import asyncio

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


@pytest.fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def engine():
    engine = create_async_engine(
        str(config.DB_CONNECTION_STRING),
        echo=False,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()  # Ensure proper disposal of the engine


@pytest_asyncio.fixture()
async def session(engine, event_loop):
    session_maker = async_sessionmaker(
        engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with engine.connect() as conn:
        tsx = await conn.begin()
        async with session_maker(bind=conn) as session:
            nested_tsx = await conn.begin_nested()
            yield session

            if nested_tsx.is_active:
                await nested_tsx.rollback()
            await tsx.rollback()
