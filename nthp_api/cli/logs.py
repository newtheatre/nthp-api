import logging
from os import environ

import coloredlogs


def init():
    nthp_build_logger = logging.getLogger("nthp_api.nthp_build")
    smugmugger_logger = logging.getLogger("nthp_api.smugmugger")

    log_level = environ.get("LOG_LEVEL", "INFO")
    coloredlogs.install(level=log_level, logger=nthp_build_logger)
    coloredlogs.install(level=log_level, logger=smugmugger_logger)
