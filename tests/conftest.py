import importlib
import os
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from gen3userdatalibrary import config
from gen3userdatalibrary.main import get_app


@pytest.fixture(scope="session")
def client():
    """
    Set up and yield a test client to send HTTP requests.
    """
    # change dir to the tests, so it loads the test .env
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    importlib.reload(config)

    with TestClient(get_app()) as test_client:
        yield test_client
