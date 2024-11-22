import re

import pytest

from gen3userdatalibrary.main import route_aggregator
from gen3userdatalibrary.utils.core import reg_match_key
from tests.routes.conftest import BaseTestRouter


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):
    router = route_aggregator

    async def test_regex_key_matcher(self):
        """
        Only necessary if we go back to regex endpoint testing
        """
        endpoint_method_to_access_method = {
            "^/lists$": {"GET": "red"},
            rf"^/lists/{UUID4_REGEX_PATTERN}$": {"GET": "blue"},
        }

        matcher = lambda k: re.match(k, "/lists/123e4567-e89b-12d3-a456-426614174000")

        # Test: Should match the UUID pattern
        result = reg_match_key(matcher, endpoint_method_to_access_method)
        assert result[0] == rf"^/lists/{UUID4_REGEX_PATTERN}$"
        assert result[1] == {"GET": "blue"}

        # Test: Should not match anything when using an endpoint that doesn't fit
        no_matcher = lambda k: None

        result_no_match = reg_match_key(no_matcher, endpoint_method_to_access_method)
        assert result_no_match == (None, {})

        # Test: Direct match with /lists
        matcher_lists = lambda key: re.match(key, "/lists")

        result_lists = reg_match_key(matcher_lists, endpoint_method_to_access_method)
        assert result_lists == ("^/lists$", {"GET": "red"})

        # Test: Edge case with an invalid pattern
        invalid_dict = {"/invalid": {"GET": "red"}}

        result_invalid = reg_match_key(matcher, invalid_dict)
        assert result_invalid == (None, {})


UUID4_REGEX_PATTERN = (
    "([0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})"
)
