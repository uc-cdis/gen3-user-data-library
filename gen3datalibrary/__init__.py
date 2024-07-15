import cdislogging

from gen3datalibrary import config

logging = cdislogging.get_logger(
    __name__, log_level="debug" if config.DEBUG else "info"
)
