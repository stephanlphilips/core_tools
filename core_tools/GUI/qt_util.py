import logging
import threading

is_wrapped = threading.local()
is_wrapped.val = False

def qt_log_exception(func):
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