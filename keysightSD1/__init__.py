try:
    from pkg_resources import get_distribution
    from .keysightSD1 import *

    __version__ = get_distribution('keysightSD1').version

except:
    # import the patched core_tools version of keysightSD1 v3.1
    import sys
    if sys.version_info.minor > 7:
        raise Exception("Please install official KeysightSD1 driver. "
                        "Core-tools driver does not support Python > 3.7")
    from .keysightSD1_31 import *

    __version__ = '3.1'
