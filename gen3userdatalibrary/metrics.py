from typing import Any, Dict

from cdispyutils.metrics import BaseMetrics

from gen3userdatalibrary import config

# TODO: meant to track overall number of user lists over time, can increase/decrease as they get created/deleted
TOTAL_USER_LIST_GAUGE = {
    "name": "gen3_data_library_user_lists",
    "description": "Gen3 User Data Library User Lists",
}

API_USER_LIST_COUNTER = {
    "name": "gen3_data_library_api_user_lists",
    "description": "API requests for modifying Gen3 User Data Library User Lists. This includes all CRUD actions.",
}

API_USER_LIST_ITEM_COUNTER = {
    "name": "gen3_data_library_user_api_list_items",
    "description": "API requests for modifying Items within Gen3 User Data Library User Lists. This includes all CRUD actions.",
}


class Metrics(BaseMetrics):
    def __init__(self, prometheus_dir: str, enabled: bool = True) -> None:
        super().__init__(
            prometheus_dir=config.PROMETHEUS_MULTIPROC_DIR, enabled=enabled
        )


    def add_user_list_counter(self, **kwargs: Dict[str, Any]) -> None:
        """
        Increment the counter for API requests related to user lists,
        this uses the provided keyword arguments as labels for the counter.

        Args:
            **kwargs: Arbitrary keyword arguments used as labels for the counter.
        """
        if not self.enabled:
            return

        self.increment_counter(labels=kwargs, **API_USER_LIST_COUNTER)

    def add_user_list_item_counter(self, **kwargs: Dict[str, Any]) -> None:
        """
        Increment the counter for API requests related to items within user lists,
        this uses the provided keyword arguments as labels for the counter.

        Args:
            **kwargs: Arbitrary keyword arguments used as labels for the counter.
        """
        if not self.enabled:
            return

        self.increment_counter(labels=kwargs, **API_USER_LIST_ITEM_COUNTER)
