from src.intervals import Interval, IntervalList
from src.notes import Note, OctaveNote, NoteList
from src.chords import AbstractChord, Chord, matching_chords
from src.scales import Scale, Subscale
from src.keys import Key, Subkey, matching_keys
from src.progressions import ChordList, Progression, ChordProgression
from src.guitar import Guitar, standard

from src.test import test_util, test_parsing, test_qualities, test_intervals, test_notes, test_chords, test_scales, test_keys, test_guitar, test_display, test_progressions
from src import util
import ipdb, cProfile

util.log.verbose = True

for module in [test_util, test_parsing, test_qualities, test_display, test_guitar,
              test_intervals, test_notes, test_chords, test_scales, test_keys, test_progressions]:

    module.unit_test()

print(f'All tests passed')
