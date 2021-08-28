"""
Si446x Packet Driver: Native Python implementation for Si446x Radio Device

@author: Dan Maltbie
"""

import os,sys
# If we are running from the source directory, try
# to load the module from there first.
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# zzz print('{} init: argv:{}, basedir:{}'.format(os.path.basename(basedir),
#                                            sys.argv[0],
#                                            basedir,))
if (os.path.exists(basedir)
    and os.path.exists(os.path.join(basedir, 'setup.py'))):
    add_dirs = [os.path.join(basedir, os.path.basename(basedir)),]
    for ndir in add_dirs:
        if (ndir not in sys.path):
            sys.path.insert(0,ndir)
    # zzz print('\n'.join(sys.path))

from si446xvers   import __version__
print('Si446x Driver Version: {}'.format(__version__))

try:
    from si446xcfg    import wds_config_count, wds_config_str, get_name_wds, get_ids_wds, get_config_wds, get_config_device, wds_default_config, set_real_time
except ImportError as e:
    print('ImportError {}'.format(e))
    raise ImportError('si446x radio configuration shared module could not be loaded')

from si446xact    import *
from si446xdef    import *
from si446xradio  import *
from si446xdvr    import *
from si446xFSM    import *
from si446xtrace  import *
