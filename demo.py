### this demo script just imports the entire orpyus namespace for easy access.
### it's intended to be used interactively without the need to install the package properly, e.g.
### e.g.:  $ ipython -i demo.py

import ipdb, time

# time how long init takes for debugging purposes:
init_start_time = time.time()

from src import util, parsing, tuning, conversion, display, _settings
from src.qualities import *
from src.intervals import *
from src.notes import *
from src.chords import *
from src.scales import *
from src.keys import *
from src.guitar import *
from src.progressions import *
from src.harmony import *
from src.audio import *
from src.rhythm import *
#from src.test.test_matching import * # for song progressions

init_end_time = time.time()
init_time = init_end_time - init_start_time
print(f'orpyus library initialised in {init_time:.2} seconds')
