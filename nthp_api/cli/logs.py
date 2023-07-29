import logging
from os import environ

import coloredlogs

LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"
DATE_FORMAT = "%H:%M:%S"


def init():
    nthp_build_logger = logging.getLogger("nthp_api.nthp_build")
    smugmugger_logger = logging.getLogger("nthp_api.smugmugger")

    log_level = environ.get("LOG_LEVEL", "INFO")
    coloredlogs.install(
        level=log_level, logger=nthp_build_logger, fmt=LOG_FORMAT, datefmt=DATE_FORMAT
    )
    coloredlogs.install(
        level=log_level, logger=smugmugger_logger, fmt=LOG_FORMAT, datefmt=DATE_FORMAT
    )
