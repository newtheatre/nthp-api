import logging

import coloredlogs

from nthp_build.config import settings


def init():
    nthp_build_logger = logging.getLogger("nthp_build")
    smugmugger_logger = logging.getLogger("smugmugger")
    coloredlogs.install(level=settings.log_level, logger=nthp_build_logger)
    coloredlogs.install(level=settings.log_level, logger=smugmugger_logger)
