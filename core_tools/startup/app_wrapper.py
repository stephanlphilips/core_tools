import logging
import os
import sys

from core_tools.startup.config import load_configuration

logger = logging.getLogger(__name__)

# reference to running data_browser to avoid diposal and garbage collection
_browser_instance = None


def run_app(name, app_init, app_main):
    '''
    Starts databrowser.

    config_file is the core_tools configuration file to use for the databrowser
    '''
    nargs = len(sys.argv)
    if nargs < 2:
        print('usage: <app> config-file [--detached]')

    config_file = sys.argv[1]
    if nargs > 2:
        detached = sys.argv[2] == '--detached'
    else:
        detached = False
    cfg = load_configuration(config_file)

    _configure_logging(cfg, name)

    app_init()
    sys.stderr.flush()
    sys.stdout.flush()
    if detached:
        _stop_console_output()
    try:
        app_main()
        logger.info("Exit")
    except:
        logger.error("Fatal exception", exc_info=True)
        raise


def _stop_console_output():
    '''
    Stops console output by redirecting to devnull.
    Signals end of output before redirecting.
    This method is used to disconnect stdout and stderr
    after being launched as child process.
    '''
    sys.stderr.flush()
    sys.stdout.flush()
    print('DISCONNECT', flush=True)
    sys.stdout.close()
    sys.stderr.close()

    f = open(os.devnull, 'w')
    sys.stdout = f
    sys.stderr = f


def _configure_logging(cfg, app_name):
    path = cfg.get(f'{app_name}.logging.file_location', '~/.core_tools/logs')
    path = os.path.expanduser(path)
    filename = cfg.get(f'{app_name}.logging.file_name', f'{app_name}.log')
    file_level = cfg.get(f'{app_name}.logging.file_level', 'INFO')
    file_format = '%(asctime)s | %(name)s | %(levelname)s | %(module)s | %(funcName)s:%(lineno)d | %(message)s'
    os.makedirs(path, exist_ok=True)
    file = os.path.join(path, filename)
    print('Logging to: ', file)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    for handler in root_logger.handlers:
        handler.close()
        root_logger.removeHandler(handler)

    file_handler = logging.handlers.TimedRotatingFileHandler(
        file,
        when="midnight",
        backupCount=15,
        encoding="utf-8"
    )

    file_handler.setLevel(file_level)
    file_handler.setFormatter(logging.Formatter(file_format))
    root_logger.addHandler(file_handler)

    logger.info(f'Start {app_name} logging')

    for name in ['matplotlib', 'h5py', 'qcodes']:
        logging.getLogger(name).setLevel(logging.INFO)
