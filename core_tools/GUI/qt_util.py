import logging
import threading

from PyQt5 import QtCore, QtWidgets

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
                logging.error('Exception in GUI', exc_info=True)
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
    _qt_app = QtCore.QCoreApplication.instance()
    if _qt_app is None:
        logging.info('Create Qt application')
        _qt_app = QtWidgets.QApplication([])
    else:
        logging.debug('Qt application already created')
