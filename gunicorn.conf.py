import logging
import multiprocessing

import cdislogging
import gunicorn.glogging
from prometheus_client import multiprocess

import gen3userdatalibrary.config


def child_exit(server, worker):
    """
    Required for Prometheus multiprocess setup
    See: https://prometheus.github.io/client_python/multiprocess/
    """
    multiprocess.mark_process_dead(worker.pid)


class CustomLogger(gunicorn.glogging.Logger):
    """
    Initialize root and gunicorn loggers with cdislogging configuration.
    """

    @staticmethod
    def _remove_handlers(logger):
        """
        Use Python's built-in logging module to remove all handlers associated
        with logger (logging.Logger).
        """
        while logger.handlers:
            logger.removeHandler(logger.handlers[0])

    def __init__(self, cfg):
        """
        Apply cdislogging configuration after gunicorn has set up it's loggers.
        """
        super().__init__(cfg)

        self._remove_handlers(logging.getLogger())
        cdislogging.get_logger(None, log_level="debug" if gen3userdatalibrary.config.DEBUG else "warn")
        for logger_name in ["gunicorn", "gunicorn.error", "gunicorn.access"]:
            self._remove_handlers(logging.getLogger(logger_name))
            cdislogging.get_logger(logger_name, log_level="debug" if gen3userdatalibrary.config.DEBUG else "info", )


logger_class = CustomLogger

wsgi_app = "gen3userdatalibrary.main:app"
bind = "0.0.0.0:8000"

# NOTE: This is always more than 2
workers = multiprocessing.cpu_count() * 2 + 1

# default was `30` for the 2 below
timeout = 90
graceful_timeout = 90
