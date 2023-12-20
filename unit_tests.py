
import ipdb, cProfile, pstats

PROFILE_INIT = True
if PROFILE_INIT:
    profiler = cProfile.Profile()
    profiler.enable()
from src.intervals import *
from src.notes import Note, OctaveNote, NoteList
from src.chords import AbstractChord, Chord, ChordList
from src.numerals import RomanNumeral, Roman, RN
from src.scales import Scale, ScaleFactors, ScaleDegree, ScaleChord
from src.keys import Key, KeyChord
from src.progressions import Progression, ChordProgression
from src.guitar import Guitar, standard
from src.matching import matching_chords, matching_scales, matching_keys

# individual test modules:
from src.test import test_util, test_parsing, test_qualities, test_intervals, test_notes
from src.test import test_chords, test_numerals, test_scales, test_keys, test_guitar, test_display
from src.test import test_progressions, test_matching

from src import util
if PROFILE_INIT:

    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('cumtime')
    stats.print_stats(20)

    stats.print_callers('progressions')

util.log.verbose = False

PROFILE_EACH = False
DECIMAL_PRECISION = 4

modules_to_test = [
                  test_util,
                  test_parsing,
                  test_qualities,
                  test_display,
                  test_guitar,
                  test_intervals,
                  test_notes,
                  test_chords,
                  test_numerals,
                  test_scales,
                  test_keys,
                  test_progressions,
                  test_matching,
                  ]

def run_all_tests(profile_each_test = True):
    for module in modules_to_test:

        @profile
        def module_test():
            print(f'Testing {module.__name__}')
            module.unit_test()
            print(f' + {module.__name__} test passed + ')

        module_test()
    print(f'+++ All tests passed +++')

def profile(func):
    def wrapper():
        if PROFILE_EACH:
            profiler = cProfile.Profile()
            profiler.enable()
            func()
            profiler.disable()
            stats = pstats.Stats(profiler).sort_stats('cumtime')
            stats.print_stats(6)
            # ipdb.set_trace()
        else:
            func()
    return wrapper

# def profile_all_tests():
#     for module in [test_util, test_parsing, test_qualities, test_display, test_guitar,
#                   test_intervals, test_notes, test_chords, test_scales, test_keys, test_progressions]:
#         print(f'Running tests for module: {module}')
#         profiler = cProfile.Profile()
#         profiler.enable()
#         module.unit_test()
#         profiler.disable()
#         stats = pstats.Stats(profiler).sort_stats('tottime')
#         stats.print_stats(10)
#         ipdb.set_trace()

# cProfile kludge to show higher time precision:
# def precise_time(x):
#     return f"%14.{DECIMAL_PRECISION}f" % x
# pstats.f8 = precise_time

if PROFILE_EACH:
    run_all_tests()
else:
    # profile them all together:
    profiler = cProfile.Profile()
    profiler.enable()

    run_all_tests()

    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('tottime')
    print('='*20 + '\nPROFILING:\n' + '='*20)
    stats.print_stats(20)
