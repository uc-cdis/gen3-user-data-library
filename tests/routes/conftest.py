from abc import abstractmethod
from unittest.mock import MagicMock

import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from gen3userdatalibrary.db import DataAccessLayer, get_data_access_layer
from gen3userdatalibrary.main import get_app


class BaseTestRouter:
    @property
    @abstractmethod
    def router(self):
        """Router should be defined for all children classes"""
        raise NotImplemented()

    @pytest_asyncio.fixture(scope="function")
    async def client(self, session):
        app = get_app()
        app.include_router(self.router)
        app.dependency_overrides[get_data_access_layer] = lambda: DataAccessLayer(
            session
        )

        app.state.metrics = MagicMock()
        app.state.arborist_client = MagicMock()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as test_client:
            yield test_client

    @pytest_asyncio.fixture(scope="function")
    async def app_client_pair(self, session):
        app = get_app()
        app.include_router(self.router)
        app.dependency_overrides[get_data_access_layer] = lambda: DataAccessLayer(
            session
        )

        app.state.metrics = MagicMock()
        app.state.arborist_client = MagicMock()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as test_client:
            yield app, test_client
