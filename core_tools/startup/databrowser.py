from core_tools.startup.config import get_configuration
from core_tools.startup.db_connection import connect_local_db, connect_remote_db
from core_tools.startup.sample_info import set_sample_info
from core_tools.startup.app_wrapper import run_app
from core_tools.GUI.qt_util import qt_init, qt_create_app, qt_run_app, qt_set_darkstyle


# reference to running data_browser to avoid diposal and garbage collection
_browser_instance = None


def databrowser_init():
    cfg = get_configuration()
    _configure_sample(cfg)
    _connect_to_db(cfg)
    print('Starting GUI...', flush=True)


def databrowser_main():
    # this import takes some time...
    from core_tools.data.gui.qml.data_browser import data_browser

    global _browser_instance
    cfg = get_configuration()
    location = cfg.get('databrowser.location')
    size = cfg.get('databrowser.size')
    live_plotting = cfg.get('databrowser.live_plotting', True)

    qt_app_started = qt_init()

    if not qt_app_started:
        _app = qt_create_app()
    _browser_instance = data_browser(
            window_location=location,
            window_size=size,
            live_plotting_enabled=live_plotting)
    if cfg.get('gui.style') == "dark":
        qt_set_darkstyle()
    if not qt_app_started:
        qt_run_app(_app)


def _configure_sample(cfg):
    project = cfg['project']
    setup = cfg['setup']
    sample = cfg['sample']
    set_sample_info(project, setup, sample)


def _connect_to_db(cfg):
    datasource = cfg['databrowser.datasource']

    if datasource == 'remote':
        connect_remote_db()
    elif datasource == 'local':
        connect_local_db()
    else:
        raise Exception('datasource must be remote or local')


if __name__ == '__main__':
    run_app('databrowser', databrowser_init, databrowser_main)
