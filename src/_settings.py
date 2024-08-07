
############# preference settings:

### DEFAULT_SHARPS controls whether accidental ('black') notes are spelled
### with sharps or flats by default in the absence of other information.
### normally such distinguishing information is available: for example,
### the tonic of a key has an informed sharp/flat preference based on the
### circle of fifths, and the chords of that key inherit this preference, but
### in the simple case of "Note('C') + 1", this setting determines the result.
DEFAULT_SHARPS = True

### PREFER_UNICODE_ACCIDENTALS controls whether the default behaviour
### when printing sharp and flat signs are the normal keyboard-typable
### characters '#' and 'b' (if False)
### or the unicode characters '♯' and '♭' (if True)
PREFER_UNICODE_ACCIDENTALS = True
### both are treated as valid input options in either case,
### this only affects what the program outputs to screen

### DEFAULT_PROGRESSION_DIACRITICS controls whether Progressions are
### displayed with informative marks underneath chords that are out-of-scale,
### or that are borrowed from a related scale.
### e.g. the progression ii-V-i in major would show a diacritic
### under the i chord, to show that it is not in the major scale.
DEFAULT_PROGRESSION_DIACRITICS = True
### DEFAULT_PROGRESSION_MARKERS is related, and controls whether
### chords in progressions are shown with informative prefix markers
### that indicate *which* related scale a chord is borrowed from.
### e.g. the progression ii-V-i in minor would be shown: ᴹii ᴴV i
### with 'M' to indicate the ii chord is from melodic minor,
### and 'H' to indicate the V chord is from harmonic minor
DEFAULT_PROGRESSION_MARKERS = False


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
BRACKETS = {  # class-identifying brackets used for different music objects:
             'Interval': ['‹', '›'],
         'IntervalList': ['𝄁', ' 𝄁'],
             'NoteList': ['𝄃', ' 𝄂'],
              'Quality': ['~', '~'],
       'ChordModifier' : ['≈', '≈'],
         'ChordFactors': ['¦ ', ' ¦'],
         'ScaleFactors': ['¦ ', ' ¦'],
            'ChordList': ['𝄃 ', ' 𝄂'],
          'Progression': ['𝄆 ', ' 𝄇'],    #['𝄃 ', ' 𝄂'],
     'ChordProgression': ['𝄆 ', ' 𝄇'],    # ['╟', '╢'],
               'Guitar': ['〚', ' 〛'],
         'RomanNumeral': ['<', '>'],

             # brackets used in chord, key display methods:
  'chromatic_intervals': ['[', ']'],  # displayed around chromatic intervals / scale factors
   'non_key_chord_root': ['<', '>'],  # displayed around KeyChords whose root is not in the key

             # brackets used on instrument displays, e.g. guitar fretboards:
       'fret_highlight': ['⟦', '⟧'], # used to highlight chord roots etc. on guitar fretboard
            }

### DIACRITICS are used to mark certain chord and note names like brackets, but more compactly
DIACRITICS = { 'ScaleDegree': '\u0311', # caret above integer (a common convention)

               ### displayed in the notelists of chords:
               'octave_above': '\u0307', # dot above
               'octave_below': '\u0323', # dot below
               '2_octaves_above': '\u0308', # 2 dots above (diaresis)
               '2_octaves_below': '\u0324', # 2 dots below

               ### displayed in matching_keys and similar functions:
               'note_not_in_input': '\u0332', # underline
               'interval_not_in_input': '\u0332',  # underline
               'chord_in_related_scale': '\u0323', # dot below
               'chord_not_in_scale': '\u0332', # underline

               'chromatic': '\u0368', # diacritic 'c' above
               }

SCALE_MARKS = { # near natural major:
             'natural minor': '', # i.e. parallel minor
             'harmonic major': 'ᴴ',
             'melodic major':  'ᴹ',
             'lydian':        'ᴸʸ',
             'mixolydian':    'ᴹˣ',

             # near natural minor:
             'natural minor': '', # i.e. parallel minor
             'harmonic minor': 'ᴴ',
             'melodic minor':  'ᴹ',
             'dorian': 'ᴰᵒ',
             'phrygian': 'ᴾʰ',

             'parallel': 'ᵖ', # parallel scale generally
             }


### CHARACTERS are used in lists to compactly denote certain traits
CHARACTERS = {   'true': '+',    # e.g. displayed in 'Tertian' column if a chord is tertian
             'somewhat': '~',    # e.g. displayed in 'Tertian' column if inverted-tertian
     'chromatic_degree': 'c',    # displayed instead of integer ScaleDegree for a non-degree (chromatic) interval
        'unknown_chord': '?',    # displayed after root for a chord of unknown type, e.g. C? chord
  'unknown_superscript': 'ˀ',    # as unknown_chord, but used where superscripts are used (e.g. progressions)
 'compound_slash_chord': '!',    # displayed after compound slash chords like Am/G
       'extended_chord': 'ˣ',    # displayed after unnamed extended chords, i.e. CGE as compound Cmaj
                   }



############# tuning settings:

### A4_PITCH is the reference pitch from which all other notes' pitches are defined.
### in traditional 'concert tuning' this is 440 Hz, but other standards exist,
### such as 'baroque tuning' where A4 is 415 Hz
### or the 'theoretically perfect' tuning where A4 is 432Hz
A4_PITCH = 440.0

### TEMPERAMENT controls which system of tuning is used to
### calculate note/interval pitches. must be one of 'JUST', 'EQUAL', or 'RATIONAL'
# these are separated for PLAYBACK (i.e. audio production)
# and for CONSONANCE (i.e. the calculation that decides how consonant intervals are)
# since it seems to work out better to use just intonation to theoretically rank scales/chords
# but to actually hear them under equal temperament
PLAYBACK_TEMPERAMENT = 'EQUAL'
CONSONANCE_TEMPERAMENT = 'JUST'

# under JUST-intonation tuning, intervals are built from clean integer ratios.
# (in this case, restricted to ratios allowed by 5-limit tuning, i.e. powers of 2*3*5 )
# under EQUAL-temperament tuning, semitones are spaced equally on a log scale.
# under RATIONAL tuning, semitones are spaced as close as possible to equal-temperament
# while maintaining rational side lengths within certain constraints. this is the
# recommended default, as a good numerical compromise between the other two systems.

### NOTE_RANGE is the range of notes (by keyboard value) for which pitches
### are calculated and defined according to specified tuning.
### the default range 1-101 (exclusive) goes from A0 to C9, which is one octave more
### than the traditional 88-key piano, but if you need notes beyond this range
### you can expand the limits here.
NOTE_RANGE = (1, 101)

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
