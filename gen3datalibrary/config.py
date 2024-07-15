import cdislogging
from starlette.config import Config
from starlette.datastructures import Secret

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
    logging.warning(
        f"DEBUG_SKIP_AUTH is {DEBUG_SKIP_AUTH}. Authorization will be SKIPPED if no token is provided. "
        "FOR NON-PRODUCTION USE ONLY!! USE WITH CAUTION!!"
    )

# postgresql://username:password@hostname:port/database_name
DB_CONNECTION_STRING = config(
    "DB_CONNECTION_STRING",
    cast=Secret,
    default="postgresql://postgres:postgres@localhost:5432/gen3datalibrary",
)

URL_PREFIX = config("URL_PREFIX", default=None)
