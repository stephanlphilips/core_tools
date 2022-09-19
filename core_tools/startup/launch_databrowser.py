from core_tools.startup.app_launcher import launch_app

module_name = 'core_tools.startup.databrowser'

def launch_databrowser(kill=False, close_at_exit=False):
    launch_app('databrowser', module_name,
               kill=kill, close_at_exit=close_at_exit)
