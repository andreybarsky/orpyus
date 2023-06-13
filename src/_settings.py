############# preference settings:

### DEFAULT_SHARPS controls whether accidental ('black') notes are spelled
### with sharps or flats by default in the absence of other information.
### normally such distinguishing information is available: for example,
### the tonic of a key has an informed sharp/flat preference based on the
### circle of fifths, and the chords of that key inherit this preference, but
### in the simple case of "Note('C') + 1", this setting determines the result.
DEFAULT_SHARPS = False

############# performance settings:

### PRE_CACHE determines whether common Chords/Scales are pre-initialised
### and added to cache when the entire library is imported.
### this adds a small overhead to the time taken to initialise the library,
### but feels a little nicer for interactive use.
PRE_CACHE_CHORDS = True   # applies to both Chords and AbstractChords
PRE_CACHE_SCALES = True   # applies to both Scales and Keys
### Notes and Intervals are always pre-cached, since there are so few, they are
### cheap to init, and they get initialised often inside other class internals.

# DYNAMIC_CACHING determines if Intervals/Chords/Scales etc. continue to be
# actively cached after import, whenever an un-cached object is initialised.
# the difference should be imperceptible for interactive use, but setting to True
# is strongly recommended for any kind of high-throughput musical number crunching,
# and should significantly improve both run-speed and memory efficiency. 
DYNAMIC_CACHING = True
