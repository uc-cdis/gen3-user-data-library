import pytest

from gen3userdatalibrary.main import route_aggregator
from gen3userdatalibrary.metrics import Metrics
from tests.routes.conftest import BaseTestRouter


@pytest.mark.asyncio
class TestConfigRouter(BaseTestRouter):
    router = route_aggregator


def test_handle_user_lists_gauge():
    """
    Test guages for lists
    """
    metrics = Metrics("/var/tmp/prometheus_metrics", True)
    metrics.handle_user_lists_gauge(1, action="CREATE")
    metrics.handle_user_lists_gauge(1, action="DELETE")


def test_handle_user_items_gauge():
    """
    Test guages for list items
    """
    metrics = Metrics("/var/tmp/prometheus_metrics", True)
    metrics.handle_user_items_gauge(1, action="CREATE")
    metrics.handle_user_items_gauge(1, action="DELETE")


def test_add_user_list_api_interaction():
    """
    Test metrics on api interact
    """
    metrics = Metrics("/var/tmp/prometheus_metrics", True)
    metrics.add_user_list_api_interaction(name="CREATE")
    metrics.add_user_list_api_interaction(name="DELETE")
