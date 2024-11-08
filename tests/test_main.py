from fastapi import FastAPI

from gen3userdatalibrary import main


def test_lifespan():
    app = FastAPI(
        title="Gen3 User Data Library Service",
        version="1.0.0",
        description="",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_version="3.1.0",
        terms_of_service=None,
        contact=None,
        license_info=None,
        debug=False,
    )

    outcome = main.lifespan(app)
    assert NotImplemented
    assert False


def test_get_app():
    assert False


def test_make_metrics_app():
    assert False
