import re

import pytest

from unittest.mock import AsyncMock, patch

from gen3userdatalibrary.main import route_aggregator
from gen3userdatalibrary.models.data import uuid4_regex_pattern
from gen3userdatalibrary.routes.middleware import reg_match_key
from tests.routes.conftest import BaseTestRouter
from tests.data.example_lists import VALID_LIST_A


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):
    router = route_aggregator

    async def test_regex_key_matcher(self):
        endpoint_method_to_access_method = {
            "^/lists$": {"GET": "red"},
            rf"^/lists/{uuid4_regex_pattern}$": {"GET": "blue"}}

        matcher = lambda k: re.match(k, "/lists/123e4567-e89b-12d3-a456-426614174000")

        # Test: Should match the UUID pattern
        result = reg_match_key(matcher, endpoint_method_to_access_method)
        assert result[0] == rf"^/lists/{uuid4_regex_pattern}$"
        assert result[1] == {"GET": "blue"}

        # Test: Should not match anything when using an endpoint that doesn't fit
        no_matcher = lambda k: None

        result_no_match = reg_match_key(no_matcher, endpoint_method_to_access_method)
        assert result_no_match is None

        # Test: Direct match with /lists
        matcher_lists = lambda key: re.match(key, "/lists")

        result_lists = reg_match_key(matcher_lists, endpoint_method_to_access_method)
        assert result_lists == ("^/lists$", {"GET": "red"})

        # Test: Edge case with an invalid pattern
        invalid_dict = {"/invalid": {"GET": "red"}}

        result_invalid = reg_match_key(matcher, invalid_dict)
        assert result_invalid is None

    @pytest.mark.parametrize("user_list", [VALID_LIST_A])
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    async def test_middleware_hit(self, get_token_claims, arborist, user_list, client):
        # todo: test that this is called before every endpoint
        headers = {"Authorization": "Bearer ofa.valid.token"}
        assert NotImplemented

    @pytest.mark.parametrize("user_list", [VALID_LIST_A])
    @pytest.mark.parametrize("endpoint", ["/_version", "/_version/",
                                          "/lists", "/lists/",
                                          "/lists/123e4567-e89b-12d3-a456-426614174000",
                                          "/lists/123e4567-e89b-12d3-a456-426614174000/"])
    @patch("gen3userdatalibrary.services.auth.arborist", new_callable=AsyncMock)
    @patch("gen3userdatalibrary.services.auth._get_token_claims")
    @patch("gen3userdatalibrary.routes.middleware.ensure_endpoint_authorized", new_callable=AsyncMock)
    async def test_middleware_get_validated(self, ensure_endpoint_authorized, get_token_claims,
                                            arborist,
                                            user_list,
                                            client,
                                            endpoint):
        # todo: test different endpoints give correct auth structure
        headers = {"Authorization": "Bearer ofa.valid.token"}
        get_token_claims.return_value = {"sub": "1", "otherstuff": "foobar"}
        arborist.auth_request.return_value = True
        result1 = await client.get(endpoint, headers=headers)
        if endpoint in {"/_version", "/_version/", "/lists", "/lists/"}:
            assert result1.status_code == 200
        else:
            assert result1.status_code == 404
        ensure_endpoint_authorized.assert_called_once()
