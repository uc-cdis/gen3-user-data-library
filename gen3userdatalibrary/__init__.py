import cdislogging

from gen3userdatalibrary import config

logging = cdislogging.get_logger(
    __name__, log_level="debug" if config.DEBUG else "info"
)
