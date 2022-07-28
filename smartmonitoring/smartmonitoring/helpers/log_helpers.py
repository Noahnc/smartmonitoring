import logging as lg
import logging.handlers
import os
import socket
import time
from datetime import datetime
import smartmonitoring.const_settings as cs
from smartmonitoring import __version__

start_time = None


def setup_file_logger(file: os.path, level: str = "DEBUG", size: int = 50, count: int = 5) -> None:
    log_file_size = size * 1024 * 1024
    main_logger = lg.getLogger()
    main_logger.setLevel(lg.getLevelName("DEBUG"))
    main_logger.addHandler(
        __get_rotating_file_handler(file, level, size, count))
    lg.debug("Settings for file-logger set - Level: " + level + ", file: " + file +
             ", file-size: " + str(log_file_size) + " byte, backup count: " + str(count))


def update_file_logger(level: str = None, size: int = None, count: int = None):
    main_logger = lg.getLogger()
    message = "Settings for file-logger updated "
    # looking for file handlers
    for handler in main_logger.handlers:
        if isinstance(handler, logging.handlers.RotatingFileHandler):
            if level is not None:
                handler.setLevel(lg.getLevelName(level))
                message += "- Level: " + level + " "
            if size is not None:
                handler.maxBytes = (size * 1024 * 1024)
                message += "- Size: " + str((size * 1024 * 1024)) + " "
            if count is not None:
                handler.backupCount = count
                message += "- backupCount: " + str(count) + " "
    lg.debug(message)


def add_console_logger(debug: bool = False, level: str = "INFO") -> None:
    main_logger = lg.getLogger()
    main_logger.setLevel(lg.getLevelName("DEBUG"))
    if debug:
        level = "DEBUG"
    log_format = '%(levelname)s: %(message)s'
    console_logger = lg.StreamHandler()
    console_logger.setLevel(lg.getLevelName(level))
    console_logger.setFormatter(ColoredLogFormat(log_format))
    main_logger.addHandler(console_logger)
    lg.debug(f'Settings for console-logger set - Level: {level}')


def __get_rotating_file_handler(file: os.path, level: str = "DEBUG", size: int = 50,
                                count: int = 5) -> logging.handlers.RotatingFileHandler:
    log_file_size = size * 1024 * 1024
    format_log = lg.Formatter('%(asctime)s-%(levelname)s %(message)s')
    log_file_handler = logging.handlers.RotatingFileHandler(
        file, maxBytes=1024 * 1024 * size, backupCount=5)
    log_file_handler.setLevel(lg.getLevelName(level))
    log_file_handler.setFormatter(format_log)
    return log_file_handler


def log_start(action: str):
    global start_time
    start_time = time.time()
    date_time = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
    lg.info(f' START AT {date_time} '.center(cs.CLI_WIDTH, '#'))
    lg.info("#")
    lg.info(f'# Action: {action}')
    lg.info(f'# Hostname: {socket.gethostname()}')
    lg.info(f'# Updater Version: {__version__}')
    lg.info("#")


def log_finish():
    lg.info(f' FINISHED AFTER {round(time.time() - start_time, 2)} SECONDS '.center(cs.CLI_WIDTH, '#'))


class ColoredLogFormat(logging.Formatter):
    grey = '\x1b[38;21m'
    blue = '\x1b[38;5;39m'
    yellow = '\x1b[38;5;226m'
    red = '\x1b[38;5;196m'
    bold_red = '\x1b[31;1m'
    reset = '\x1b[0m'

    def __init__(self, fmt):
        super().__init__()
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.grey + self.fmt + self.reset,
            logging.INFO: self.blue + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
