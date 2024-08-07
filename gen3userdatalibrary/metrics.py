from cdispyutils.metrics import BaseMetrics

USER_LIST_COUNTER = {
    "name": "gen3_data_library_user_lists",
    "description": "Gen3 User Data Library User Lists",
}


class Metrics(BaseMetrics):
    def add_user_list_counter(self, info):
        labels = info.get("stuff")
        self.increment_counter(labels=labels, **USER_LIST_COUNTER)
