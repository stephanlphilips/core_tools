import logging
import psutil
import sys
import atexit
import subprocess
import platform
from threading import Thread

from core_tools.startup.config import get_configuration

logger = logging.getLogger(__name__)

def launch_app(name, module_name, kill=False, close_at_exit=False):
    if not _is_running(name, module_name, kill):
        cfg = get_configuration()
        config_file = cfg.filename
        cmd = [sys.executable,
               '-m', module_name,
               config_file,
               '--detached'
               ]
        print('Launching', name, flush=True)
        if platform.system() == 'Windows':
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            creationflags = 0
        proc = subprocess.Popen(
                cmd,
                creationflags=creationflags,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True)

        thread = Thread(target=_echo_output, args=(proc, name))
        thread.start()

        if close_at_exit:
            atexit.register(proc.terminate)


def _is_running(name, module_name, kill=False):
    for pid in psutil.pids():
        try:
            p = psutil.Process(pid)
            if p.name().startswith('python'):
                if module_name in p.cmdline():
                    if kill:
                        logger.warning(f'Stopping active {name}')
                        p.kill()
                        return False
                    else:
                        print(f'{name} already running')
                        return True
        except Exception as ex:
            print(ex)
    return False


def _echo_output(proc, name):
    '''
    Echos the output of proc to stdout.
    Stops echoing output when proc terminates or when it sends
    'DISCONNECT'.
    '''
    inp = proc.stdout
    while True:
        d = inp.readline()
        if d == 'DISCONNECT\n':
            inp.close()
            break
        if len(d) == 0:
            break
        print(f'{name}: ', d[:-1])

