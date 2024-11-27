import pytest
from fastapi import Depends

from gen3userdatalibrary.db import get_data_access_layer, DataAccessLayer
from gen3userdatalibrary.models.helpers import create_user_list_instance
from gen3userdatalibrary.models.user_list import ItemToUpdateModel
from gen3userdatalibrary.routes import route_aggregator
from tests.routes.conftest import BaseTestRouter


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):
    router = route_aggregator

    @pytest.mark.skip(reason="Test not implemented yet.")
    async def test_ensure_user_has_not_reached_max_lists(
        self,
        data_access_layer: DataAccessLayer = Depends(get_data_access_layer),
    ):
        pass

    # How do I test the DAL functions?
    # async for e in get_data_access_layer():
    #     outcome = await data_access_layer.ensure_user_has_not_reached_max_lists(
    #         "foo", 1
    #     )
    #     assert outcome == 1
    async def test_persist_user_list(self):
        dals = get_data_access_layer()
        example_user_list = create_user_list_instance(
            "0",
            ItemToUpdateModel(
                name="fizzbuzz",
                items={},
            ),
        )
        async for data_access_layer in dals:
            with pytest.raises(Exception):
                outcome = await data_access_layer.persist_user_list(
                    "0", example_user_list
                )
