from unittest.mock import patch, AsyncMock

import pytest

from gen3userdatalibrary.db import DataAccessLayer
from gen3userdatalibrary.main import route_aggregator
from tests.routes.conftest import BaseTestRouter


def raise_exce():
    raise Exception


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):
    router = route_aggregator

    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    @patch.object(
        DataAccessLayer, "test_connection", side_effect=Exception("Connection failed")
    )
    async def test_get_status(
        self,
        test_connection,
        get_token_claims,
        arborist,
        client,
    ):
        arborist.auth_request.return_value = True
        headers = {"Authorization": "Bearer ofa.valid.token"}
        get_token_claims.return_value = {"sub": "1"}
        outcome = await client.get("/_status", headers=headers)
        assert outcome.status_code == 500
