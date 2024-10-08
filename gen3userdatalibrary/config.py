import cdislogging
from fastapi import Path
from starlette.config import Config
from starlette.datastructures import Secret

from gen3userdatalibrary.utils import read_json_if_exists

config = Config(".env")
if not config.file_values:
    config = Config("env")

DEBUG = config("DEBUG", cast=bool, default=False)
VERBOSE_LLM_LOGS = config("VERBOSE_LLM_LOGS", cast=bool, default=False)

logging = cdislogging.get_logger(__name__, log_level="debug" if DEBUG else "info")

# will skip authorization when a token is not provided. note that if a token is provided, then
# auth will still occur
DEBUG_SKIP_AUTH = config("DEBUG_SKIP_AUTH", cast=bool, default=False)

if DEBUG:
    logging.info(f"DEBUG is {DEBUG}")
if VERBOSE_LLM_LOGS:
    logging.info(f"VERBOSE_LLM_LOGS is {VERBOSE_LLM_LOGS}")
if DEBUG_SKIP_AUTH:
    logging.warning(f"DEBUG_SKIP_AUTH is {DEBUG_SKIP_AUTH}. Authorization will be SKIPPED if no token is provided. "
                    "FOR NON-PRODUCTION USE ONLY!! USE WITH CAUTION!!")

# postgresql://username:password@hostname:port/database_name
DB_CONNECTION_STRING = config("DB_CONNECTION_STRING", cast=Secret,
                              default="postgresql+asyncpg://postgres:postgres@localhost:5432/testgen3datalibrary", )

URL_PREFIX = config("URL_PREFIX", default=None)

# enable Prometheus Metrics for observability purposes
#
# WARNING: Any counters, gauges, histograms, etc. should be carefully
# reviewed to make sure its labels do not contain any PII / PHI. T
#
# IMPORTANT: This enables a /metrics endpoint which is OPEN TO ALL TRAFFIC, unless controlled upstream
ENABLE_PROMETHEUS_METRICS = config("ENABLE_PROMETHEUS_METRICS", default=False)

PROMETHEUS_MULTIPROC_DIR = config("PROMETHEUS_MULTIPROC_DIR", default="/var/tmp/prometheus_metrics")

# Location of the policy engine service, Arborist
# Defaults to the default service name in k8s magic DNS setup
ARBORIST_URL = config("ARBORIST_URL", default="http://arborist-service")

ITEM_SCHEMAS = read_json_if_exists(Path("./item_schemas.json"))
if ITEM_SCHEMAS is None:
    raise OSError("No item schema json file found!")
