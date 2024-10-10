from unittest.mock import MagicMock

import pytest_asyncio
from httpx import AsyncClient

from gen3userdatalibrary.main import get_app
from gen3userdatalibrary.services.db import DataAccessLayer, get_data_access_layer


class BaseTestRouter:

    @pytest_asyncio.fixture(scope="function")
    async def client(self, session):
        app = get_app()
        # todo (addressed): https://docs.python.org/3/library/abc.html
        # alex: label as abstract base class, should provide a way to define that router is required
        # abstractbaseclass lib
        # find way to define abstract property
        # @property
        # def router(self):
        #     raise NotImplemented()

        # todo later: where does app get state and dep_overrides from?
        app.include_router(self.router)
        app.dependency_overrides[get_data_access_layer] = lambda: DataAccessLayer(session)

        app.state.metrics = MagicMock()
        app.state.arborist_client = MagicMock()

        async with AsyncClient(app=app, base_url="http://test") as test_client:
            yield test_client
