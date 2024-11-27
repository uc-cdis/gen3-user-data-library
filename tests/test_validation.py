from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from gen3userdatalibrary.routes import route_aggregator
from tests.data.example_lists import INVALID_LIST_A
from tests.routes.conftest import BaseTestRouter


@pytest.mark.asyncio
class TestAuthRouter(BaseTestRouter):
    router = route_aggregator

    @pytest.mark.parametrize("endpoint", ["/lists", "/lists/"])
    @patch("gen3userdatalibrary.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.auth._get_token_claims")
    async def test_mismatched_type_to_endpoint_fails(
        self, get_token_claims, arborist, endpoint, client
    ):
        """
        Test that for an endpoint X with parameter P of type T,
        if data is not in shape T it fails
        """
        arborist.auth_request.return_value = True
        headers = {"Authorization": "Bearer ofa.valid.token"}
        get_token_claims.return_value = {"sub": "1", "otherstuff": "foobar"}
        with pytest.raises(ValidationError) as e:
            response = await client.put(
                endpoint, headers=headers, json={"lists": [INVALID_LIST_A]}
            )
