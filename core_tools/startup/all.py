import logging
import os
import re
from datetime import datetime, timedelta

from .config import load_configuration
from .db_connection import (
        connect_local_db,
        connect_remote_db,
        connect_local_and_remote_db)
from .sample_info import set_sample_info

logger = logging.getLogger(__name__)


def configure(filename):
    cfg = load_configuration(filename)
    _configure_logging(cfg)
    _configure_sample(cfg)
    _connect_to_db(cfg)


def _configure_sample(cfg):
    project = cfg['project']
    setup = cfg['setup']
    sample = cfg['sample']
    set_sample_info(project, setup, sample)


def _connect_to_db(cfg):
    use_local = cfg.get('local_database') is not None
    use_remote = cfg.get('remote_database') is not None

    if use_local and use_remote:
        connect_local_and_remote_db()
    elif use_local:
        connect_local_db()
    elif use_remote:
        connect_remote_db()
    else:
        logger.warning('No database configured')


def _generate_log_file_name():
    pid = os.getpid()
    now = datetime.now()
    return f"{now:%Y-%m-%d}({pid:06d}).log"


def _configure_logging(cfg):
    if cfg.get('logging.disabled', False):
        return
    path = cfg.get('logging.file_location', '~/.core_tools')
    file_level = cfg.get('logging.file_level', 'INFO')
    console_level = cfg.get('logging.console_level', 'WARNING')
    logger_levels = cfg.get('logging.logger_levels', {})
    max_age = cfg.get('logging.max_age', 90)

    name = _generate_log_file_name()
    file_format = '%(asctime)s | %(name)s | %(levelname)s | %(module)s | %(funcName)s:%(lineno)d | %(message)s'
    console_format = '%(levelname)s %(module)s: %(message)s'

    path = os.path.expanduser(path)
    os.makedirs(path, exist_ok=True)
    filename = os.path.join(path, name)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    for handler in root_logger.handlers:
        handler.close()
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(logging.Formatter(console_format))
    root_logger.addHandler(console_handler)

    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename, when="midnight", encoding="utf-8"
    )

    file_handler.setLevel(file_level)
    file_handler.setFormatter(logging.Formatter(file_format))
    root_logger.addHandler(file_handler)

    logger.info('Start logging')

    old_files = []
    pattern = re.compile(r"\d{4}-\d{2}-\d{2}\(\d{6,}\)\.log(\.\d{4}-\d{2}-\d{2})?")
    expiry_time = (datetime.now() - timedelta(max_age)).timestamp()
    for entry in os.scandir(path):
        if (entry.is_file()
            and pattern.match(entry.name)
            and entry.stat().st_mtime < expiry_time):
                old_files.append(entry.name)

    if old_files:
        print(f"Deleting {len(old_files)} log files older than {max_age} days")
        logger.info(f"Deleting {len(old_files)} log files older than {max_age} days")
    for name in old_files:
        try:
            os.remove(os.path.join(path, name))
            logging.debug(f"Removed {name}")
        except Exception as ex:
            logging.info(f"Failed to removed {name}: {type(ex)}:{ex}")

    print(f'Logging to: "{filename}" with level {file_level}')

    for name, level in logger_levels.items():
        logging.getLogger(name).setLevel(level)
