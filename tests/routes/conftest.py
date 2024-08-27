from unittest.mock import MagicMock

import pytest_asyncio
from httpx import AsyncClient

from gen3userdatalibrary.db import DataAccessLayer, get_data_access_layer
from gen3userdatalibrary.main import get_app


class BaseTestRouter:
    @pytest_asyncio.fixture(scope="function")
    async def client(self, session):
        app = get_app()
        app.include_router(self.router)
        app.dependency_overrides[get_data_access_layer] = lambda: DataAccessLayer(
            session
        )

        app.state.metrics = MagicMock()
        app.state.arborist_client = MagicMock()

        async with AsyncClient(app=app, base_url="http://test") as test_client:
            yield test_client
