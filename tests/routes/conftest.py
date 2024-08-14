from httpx import AsyncClient
import pytest_asyncio

from gen3userdatalibrary.db import get_data_access_layer, DataAccessLayer
from gen3userdatalibrary.main import get_app


class BaseTestRouter:
    @pytest_asyncio.fixture(scope="function")
    async def client(self, session):
        app = get_app()
        app.include_router(self.router)
        app.dependency_overrides[get_data_access_layer] = lambda: DataAccessLayer(
            session
        )
        async with AsyncClient(app=app, base_url="http://test") as test_client:
            yield test_client
