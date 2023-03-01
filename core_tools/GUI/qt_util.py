import logging
import threading

from PyQt5 import QtCore, QtWidgets

try:
    import IPython.lib.guisupport as gs
    from IPython import get_ipython
except:
    get_ipython = lambda x:None

logger = logging.getLogger(__name__)

is_wrapped = threading.local()
is_wrapped.val = False

def qt_log_exception(func):
    ''' Decorator to log exceptions.
    Exceptions are logged and raised again.
    Decorator is designed to be used around functions being called as
    QT event handlers, because QT doesn't report the exceptions.
    Note:
        The decorated method/function cannot be used with
        functools.partial.
    '''

    def wrapped(*args, **kwargs):
        if is_wrapped.val:
            return func(*args, **kwargs)
        else:
            is_wrapped.val = True
            try:
                return func(*args, **kwargs)
            except:
                logger.error('Exception in GUI', exc_info=True)
                raise
            finally:
                is_wrapped.val = False

    return wrapped


_qt_app = None

def qt_init():
    '''Starts the QT application if not yet started.
    Most of the cases the QT backend is already started
    by IPython, but sometimes it is not.
    '''
    # application reference must be held in global scope
    global _qt_app

#    print(QtCore.QCoreApplication.testAttribute(QtCore.Qt.AA_EnableHighDpiScaling))
#    print(QtCore.QCoreApplication.testAttribute(QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough))

    # Set attributes for proper scaling when display scaling is not equal to 100%
    # This should be done before QApplication is started.
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    ipython = get_ipython()

    if ipython:
        if not gs.is_event_loop_running_qt4():
            # print('Warning Qt5 not configured for IPython console. Activating it now.')
            # ipython.run_line_magic('gui','qt5')
            raise Exception('Configure QT5 in Spyder -> Preferences -> IPython Console -> Graphics -> Backend')

        _qt_app = QtCore.QCoreApplication.instance()
        if _qt_app is None:
            logger.debug('Create Qt application')
            _qt_app = QtWidgets.QApplication([])
        else:
            logger.debug('Qt application already created')


_qt_message_handler_installed = False

def _qt_message_handler(level, context, message):
    if message.startswith('QSocketNotifier: Multiple socket notifiers for same socket'):
        # ignore ipython warning
        return
    if level == QtCore.QtInfoMsg:
        log_level = logging.INFO
    elif level == QtCore.QtWarningMsg:
        log_level = logging.WARNING
    elif level == QtCore.QtCriticalMsg:
        log_level = logging.CRITICAL
    elif level == QtCore.QtFatalMsg:
        log_level = logging.FATAL
    else:
        log_level = logging.DEBUG
    logger.log(log_level, message)

def install_qt_message_handler():
    global _qt_message_handler_installed

    if not _qt_message_handler_installed:
        QtCore.qInstallMessageHandler(_qt_message_handler)
        _qt_message_handler_installed = True
