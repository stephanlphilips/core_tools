try:
    from pkg_resources import get_distribution
    from .keysightSD1 import *

    __version__ = get_distribution('keysightSD1').version

except:
    # import the patched core_tools version of keysightSD1 v3.1
    from .keysightSD1_31 import *

    __version__ = '3.1'
