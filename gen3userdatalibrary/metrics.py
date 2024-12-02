from typing import Any, Dict

from cdispyutils.metrics import BaseMetrics

from gen3userdatalibrary import config

TOTAL_USER_LISTS_GAUGE = {
    "name": "gen3_user_data_library_user_lists",
    "description": "Gen3 User Data Library User Lists. Does NOT count the items within the list, just the lists themselves.",
}

TOTAL_USER_ITEMS_GAUGE = {
    "name": "gen3_user_data_library_user_items",
    "description": "Gen3 User Data Library User Items (within Lists). This counts the amount of items WITHIN lists, rather than the lists themselves.",
}

API_REQUESTS_COUNTER = {
    "name": "gen3_user_data_library_api_requests",
    "description": "API requests for modifying Gen3 User Data Library User Lists. This includes "
    "all CRUD actions.",
}


class Metrics(BaseMetrics):
    def __init__(self, prometheus_dir: str, enabled: bool = True) -> None:
        super().__init__(
            prometheus_dir=config.PROMETHEUS_MULTIPROC_DIR, enabled=enabled
        )

    def handle_user_lists_gauge(self, value: float, **kwargs: Dict[str, Any]) -> None:
        """
        Update the gauge for total User Lists.
        This expects the provided keyword arguments to provide information about
        the action taken

        Args:
            value (float): amount to inc/dec/set
            **kwargs: Arbitrary keyword arguments used as labels for the counter.
                must contain action: string representing what CRUD action was taken,
                    CREATE and DELETE are the only ones
                    that prompt action on updating the gauge
        """
        if not self.enabled:
            return

        if kwargs.get("action") == "CREATE":
            self.inc_gauge(labels=kwargs, value=value, **TOTAL_USER_LISTS_GAUGE)
        elif kwargs.get("action") == "DELETE":
            self.dec_gauge(labels=kwargs, value=value, **TOTAL_USER_LISTS_GAUGE)

    def handle_user_items_gauge(self, value: float, **kwargs: Dict[str, Any]) -> None:
        """
        Update the gauge for total User ITEMS (e.g. the number of things contained in lists).
        This expects the provided keyword arguments to provide information about
        the action taken

        Args:
            value (float): amount to inc/dec/set
            **kwargs: Arbitrary keyword arguments used as labels for the counter.
                must contain action: string representing what CRUD action was taken,
                    CREATE and DELETE are the only ones
                    that prompt action on updating the gauge
        """
        if not self.enabled:
            return

        if kwargs.get("action") == "CREATE":
            self.inc_gauge(labels=kwargs, value=value, **TOTAL_USER_ITEMS_GAUGE)
        elif kwargs.get("action") == "DELETE":
            self.dec_gauge(labels=kwargs, value=value, **TOTAL_USER_ITEMS_GAUGE)

    def add_user_list_api_interaction(self, **kwargs: Dict[str, Any]) -> None:
        """
        Increment the counter for API requests related to user lists,
        this uses the provided keyword arguments as labels for the counter.

        Args:
            **kwargs: Arbitrary keyword arguments used as labels for the counter.
        """
        if not self.enabled:
            return

        self.increment_counter(labels=kwargs, **API_REQUESTS_COUNTER)
