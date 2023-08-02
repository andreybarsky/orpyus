from ..keys import Key, matching_keys
from ..scales import Scale
from ..chords import Chord
from .testing_tools import compare

def unit_test():
    # 3 types of initialisation:
    compare(Key(intervals=[2,3,5,7,8,10], tonic='B'), Key('Bm'))
    compare(Key(intervals=[2,4,5,7,9,11], tonic='C'), Key(notes='CDEFGAB'))
    compare(Key('Cm').intervals, Scale('natural minor').intervals)

    # and by import from Scale class:
    compare(Scale('dorian').on_tonic('D'), Key('D dorian'))


    print('Test Key __contains__:')
    # normal scale-degree triads/tetrads:
    compare(Chord('Dm') in Key('C'), True)
    compare(Chord('D') in Key('C'), False)
    compare(Chord('G7') in Key('C'), True)
    compare(Chord('Bdim') in Key('C'), True)
    compare(Chord('Fdim7') in Key('C'), False)

    # disqualification by non-matching root:
    compare(Chord('D#') in Key('C'), False)


    # non-triadic chords that are still valid:
    compare(Chord('D13sus4') in Key('C'), True)
    # or not:
    compare(Chord('Fmmaj11') in Key('C'), False)

    # test key equivalence across enharmonic tonics:
    compare(Key('F#') == Key('Gb'), True)
    compare(Key('F#') == Key('G'), False)

    # test utility methods:
    compare(Key('C').mode(2), Key('D dorian'))
    compare(Key('C').pentatonic, Key('C pentatonic'))

    matching_keys(['C', Chord('F'), 'G7', 'Bdim'], upweight_pentatonics=False)

    matching_keys(['Dm', 'Dsus4', 'Am', 'Asus4', 'E', 'E7', 'Asus4', 'Am7'], upweight_pentatonics=True)
