import sys
import logging
from logging.handlers import RotatingFileHandler


def init_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s: %(levelname)s: %(message)s', '%Y-%m-%d %H:%M:%S')

    file_handler = RotatingFileHandler("my_log.log", maxBytes=10 * 1000 * 1000, backupCount=10)
    stdoutHandler = logging.StreamHandler(sys.stdout)
    file_handler.setFormatter(formatter)
    stdoutHandler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(stdoutHandler)
