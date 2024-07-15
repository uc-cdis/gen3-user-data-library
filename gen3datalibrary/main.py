import os
from importlib.metadata import version

import fastapi
import yaml
from fastapi import FastAPI

from gen3datalibrary import config, logging
from gen3datalibrary.routes import root_router


def get_app() -> fastapi.FastAPI:
    """
    Return the web framework app object after adding routes

    Returns:
        fastapi.FastAPI: The FastAPI app object
    """

    fastapi_app = FastAPI(
        title="Gen3 Data Library Service",
        version=version("gen3datalibrary"),
        debug=config.DEBUG,
        root_path=config.URL_PREFIX,
    )
    fastapi_app.include_router(root_router)

    # this makes the docs at /doc and /redoc the same openapi docs in the docs folder
    # instead of the default behavior of generating openapi spec based from FastAPI
    fastapi_app.openapi = _override_generated_openapi_spec

    return fastapi_app


def _override_generated_openapi_spec():
    json_data = None
    try:
        openapi_filepath = os.path.abspath("./docs/openapi.yaml")
        with open(openapi_filepath, "r", encoding="utf-8") as yaml_in:
            json_data = yaml.safe_load(yaml_in)
    except FileNotFoundError:
        logging.warning(
            "could not find custom openapi at `docs/openapi.yaml`, using default generated one"
        )

    return json_data


app = get_app()
