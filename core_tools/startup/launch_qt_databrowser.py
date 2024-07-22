from packaging.version import Version

from core_tools.startup.app_launcher import launch_app

module_name = 'core_tools.startup.qt_databrowser'

def launch_qt_databrowser(kill=False, close_at_exit=False):
    try:
        import qt_dataviewer
    except ImportError:
        raise Exception("Missing package qt-dataviewer")
    if Version(qt_dataviewer.__version__) < Version("0.3.0"):
        raise Exception("qt_databrowser requires qt-dataviewer >= v0.3.0")
    launch_app('qt_databrowser', module_name,
               kill=kill, close_at_exit=close_at_exit)
