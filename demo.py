### this demo script just imports the entire orpyus namespace for easy access.
### it's intended to be used interactively without the need to install the package properly, e.g.
### e.g.:  $ ipython -i demo.py

import ipdb

from src import util
from src import parsing
from src import conversion
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
