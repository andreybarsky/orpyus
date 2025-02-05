### tests of matching algorithms to ensure that
###

from ..qualities import Major, Minor
from ..matching import matching_chords, matching_scales, matching_keys, match_tonal_dist_to_intervals
from ..progressions import *
from .testing_tools import compare
from ..scales import MajorScale, MinorScale

def unit_test():

    ### first: check that quality distributions map on to what they should
    compare(match_tonal_dist_to_intervals(Scale('harmonic major').intervals), Major)
    compare(match_tonal_dist_to_intervals(Scale('melodic major').intervals), Major)
    compare(match_tonal_dist_to_intervals(Scale('lydian').intervals), Major)
    compare(match_tonal_dist_to_intervals(Scale('mixolydian').intervals), Major)

    compare(match_tonal_dist_to_intervals(Scale('double harmonic').intervals), Major)


    compare(match_tonal_dist_to_intervals(Scale('harmonic minor').intervals), Minor)
    compare(match_tonal_dist_to_intervals(Scale('melodic minor').intervals), Minor)
    compare(match_tonal_dist_to_intervals(Scale('dorian').intervals), Minor)
    compare(match_tonal_dist_to_intervals(Scale('phrygian').intervals), Minor)
    compare(match_tonal_dist_to_intervals(Scale('neapolitan major').intervals), Minor) # supposedly!
    compare(match_tonal_dist_to_intervals(Scale('neapolitan minor').intervals), Minor)
    compare(match_tonal_dist_to_intervals(Scale('hungarian minor').intervals), Minor)



    ### second: check that chord matching detects correct chords from notes
    inv_cmaj7 = Chord('GCEB')
    compare(matching_chords('GCEB', display=False), [Chord('Cmaj7')])
    compare(matching_chords('FD#A#', display=False), [Chord('A#sus4'), Chord('D#sus2')])



    # then scale matching

    compare(list(matching_scales('I iii V7', display=False, candidate_scales=[MajorScale, MinorScale])), [Scale('major')])
    # compare(matching_scales('i bIII V7', display=False), [Scale('extended minor'), Scale('full minor')])

    # test input by pairs vs input by numerals:
    degree_chord_pairs = [(1, AbstractChord('min')), (5, AbstractChord('7')), (7, AbstractChord('maj'))]
    compare(matching_scales(degree_chord_pairs, display=False), matching_scales('i V7 VII', display=False))


    # then chord progressions

    # these are the chord progressions of some songs I'm practicing
    # and checking that they auto-detect the correct key
    house_of_the_rising_sun = ChordProgression('Am C D F Am E Am E')
    house_of_the_rising_sun2 = (house_of_the_rising_sun + ['Am', 'C', 'D', 'F', 'Am', 'C', 'E', 'E'])
    compare(house_of_the_rising_sun.key,  Key('Am'))

    # eric clapton / steve winwood:
    cant_find_my_way_home = ChordProgression('G, D/F#, Dm/F, A, C, D, A')
    compare(cant_find_my_way_home.key, Key('A'))

    # yosh / FF7R
    hollow = ChordProgression('A6 - Cmaj7#11 - Emadd9')
    compare(hollow.key, Key('Em'))

    # josh turner:
    would_you_go_with_me = ChordProgression('E C#m B E B A')
    compare(would_you_go_with_me.key, Key('E'))
    your_man = ChordProgression('C G D G') - 1
    compare(your_man.key, Key('Gb'))

    carolina = ChordProgression('Bm A Em A Bm D A Em')
    compare(carolina.key, Key('Bm'))

    carolina_full = ChordProgression('Bm Bm A Em Em7 A Bm Bm Bm Bm A Em Em7 A Bm Bm Bm7 Bm Bm7 Bm7 D A Em Esus4 D', key='Bm')

    sweet_child_of_mine = ChordProgression('D Cadd9 G D A C D')
    compare(sweet_child_of_mine.key, Key('D'))

    queen_of_argyll = ChordProgression('Am Em Am Em C G Am Em C G Am')
    queen_of_argyll2 = ChordProgression('Am Em G Am Em C G Em Am Em F G Am')
    queen_of_argyll3 = ChordProgression('Am Em G Am Em C G Em Am Em C G Em D')

    # other songs with different match cases:

    # # ( nuvole bianche doesn't currently work)
    # nuvole_bianche = ChordProgression('Fm Db Ab Eb')
    # compare(nuvole_bianche.key, Key('Ab'))
