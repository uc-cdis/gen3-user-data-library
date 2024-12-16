from unittest.mock import patch

import pytest
from fastapi import HTTPException

from gen3userdatalibrary.main import route_aggregator
from gen3userdatalibrary.models.helpers import try_conforming_list
from gen3userdatalibrary.models.user_list import ItemToUpdateModel
from tests.routes.conftest import BaseTestRouter


def raise_exce(exce: Exception, _):
    raise exce


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):
    router = route_aggregator

    @patch(
        "gen3userdatalibrary.models.helpers.create_user_list_instance",
        side_effect=raise_exce,
    )
    async def test_try_conforming_list(self, modeling):
        """
        Test conforming list fails as expected
        Args:
            modeling: mock create instance
        """
        example_list = ItemToUpdateModel(
            name="1", items={"key1": "value1", "key2": 123}
        )

        try:
            outcome = await try_conforming_list(ValueError, example_list)
            assert False
        except HTTPException as e:
            assert e.detail["error"] == "ValueError"

        class CustomError(Exception):
            pass

        try:
            outcome = await try_conforming_list(CustomError, example_list)
            assert False
        except HTTPException as e:
            assert e.detail["error"] == "CustomError"
