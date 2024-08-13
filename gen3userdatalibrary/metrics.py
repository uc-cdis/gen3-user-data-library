from cdispyutils.metrics import BaseMetrics

USER_LIST_GAUGE= {
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
    def add_user_list_counter(self, **kwargs):
        self.increment_counter(labels=kwargs, **API_USER_LIST_COUNTER)

    def add_user_list_item_counter(self, **kwargs):
        self.increment_counter(labels=kwargs, **API_USER_LIST_ITEM_COUNTER)
