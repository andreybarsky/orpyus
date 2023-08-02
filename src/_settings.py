
############# tuning settings:

### TUNING_MODE controls which system of tuning is used to
### calculate note/interval pitches. must be one of 'JUST' or 'EQUAL':
TUNING_MODE = 'JUST'

# under JUST-intonation tuning, intervals are built from clean integer ratios.
# (in this case, restricted to ratios allowed by 5-limit tuning, i.e. powers of 2*3*5 )
# under EQUAL-temperament tuning, semitones are spaced equally on a log scale.


############# preference settings:

### DEFAULT_SHARPS controls whether accidental ('black') notes are spelled
### with sharps or flats by default in the absence of other information.
### normally such distinguishing information is available: for example,
### the tonic of a key has an informed sharp/flat preference based on the
### circle of fifths, and the chords of that key inherit this preference, but
### in the simple case of "Note('C') + 1", this setting determines the result.
DEFAULT_SHARPS = False

# orpyus musical objects use little unicode MARKERS in their string methods
# to identify them at a glance. the default markers are defined here, so you
# can change them if you don't like them:
MARKERS = { # class markers used to identify musical object types:
            'Note': '♩',
      'OctaveNote': '♪',
   'AbstractChord': '♫ ',
           'Chord': '♬ ',
           'Scale': '𝄢 ',
             'Key': '𝄞 ',

             # chord-movement markers used in progression analysis:
             'right': '⇾ ', # '>',
             'up': '↿', #'↑' # '⇧'
             'down': '⇃', # '↓' # '⇩'
            }



### BRACKETS are used similarly to markers, but placed around the objects they contain:
BRACKETS = { 'Interval': ['‹', '›'],
         'IntervalList': ['𝄁', ' 𝄁'],
             'NoteList': ['𝄃', ' 𝄂'],
              'Quality': ['~', '~'],
       'ChordModifier' : ['≈', '≈'],
         'ChordFactors': ['¦ ', ' ¦'],
            'ChordList': ['𝄃 ', ' 𝄂'],
          'Progression': ['𝄆 ', ' 𝄇'],    #['𝄃 ', ' 𝄂'],
     'ChordProgression': ['𝄆 ', ' 𝄇'],    # ['╟', '╢'],
               'Guitar': ['〚', ' 〛'],
  'chromatic_intervals': ['[', ']'],
            }

### CHARACTERS are used in lists to compactly denote certain traits
CHARACTERS = { 'true': '+',    # e.g. displayed in 'Tertian' column if a chord is tertian
           'somewhat': '~',    # e.g. displayed in 'Tertian' column if inverted-tertian
   'chromatic_degree': 'c',    # displayed instead of integer ScaleDegree for a non-degree (chromatic) interval
             }

############# performance settings:

### PRE_CACHE determines whether common Chords/Scales are pre-initialised
### and added to cache when the entire library is imported.
### this adds a small overhead to the time taken to initialise the library,
### but feels a little nicer for interactive use.
PRE_CACHE_CHORDS = True   # applies to both Chords and AbstractChords
PRE_CACHE_SCALES = True   # applies to both Scales and Keys
# Notes and Intervals are always pre-cached, since there are so few, they are
# cheap to init, and they get initialised often inside other class internals.

# DYNAMIC_CACHING determines if Intervals/Chords/Scales etc. continue to be
# actively cached after import, whenever an un-cached object is initialised.
# the difference should be imperceptible for interactive use, but setting to True
# is strongly recommended for any kind of high-throughput musical number crunching,
# and should significantly improve both run-speed and memory efficiency.
DYNAMIC_CACHING = True
