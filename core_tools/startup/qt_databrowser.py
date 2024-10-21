import logging

from core_tools.startup.config import get_configuration
from core_tools.startup.db_connection import connect_local_db, connect_remote_db
from core_tools.startup.sample_info import set_sample_info
from core_tools.startup.app_wrapper import run_app
from core_tools.GUI.qt_util import qt_init, qt_create_app, qt_run_app, qt_set_darkstyle


logger = logging.getLogger(__name__)

# reference to running data_browser to avoid disposal and garbage collection
_browser_instance = None


def databrowser_init():
    cfg = get_configuration()
    _configure_sample(cfg)
    _connect_to_db(cfg)
    print('Starting GUI...', flush=True)


def databrowser_main():
    # this import takes some time...
    from qt_dataviewer.core_tools.data_browser import CoreToolsDataBrowser

    global _browser_instance

    cfg = get_configuration()
    qt_app_started = qt_init()

    if not qt_app_started:
        _app = qt_create_app()

    if cfg.get('gui.style') == "dark":
        qt_set_darkstyle()

    # @@@ TODO
    # location = cfg.get('qt_databrowser.location')
    # size = cfg.get('qt_databrowser.size')
    # live_plotting = cfg.get('qt_databrowser.live_plotting', True)

    _browser_instance = CoreToolsDataBrowser()
    if not qt_app_started:
        qt_run_app(_app)


def _configure_sample(cfg):
    project = cfg['project']
    setup = cfg['setup']
    sample = cfg['sample']
    set_sample_info(project, setup, sample)


def _connect_to_db(cfg):
    datasource = cfg['qt_databrowser.datasource']

    if datasource == 'remote':
        connect_remote_db()
    elif datasource == 'local':
        connect_local_db()
    else:
        raise Exception('datasource must be remote or local')


if __name__ == '__main__':
    run_app('qt_databrowser', databrowser_init, databrowser_main)
