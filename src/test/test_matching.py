### tests of matching algorithms to ensure that
###

from ..qualities import Major, Minor
from ..matching import matching_chords, matching_keys, match_qualdist_to_intervals
from ..progressions import *
from .testing_tools import compare

def unit_test():

    ### first: check that quality distributions map on to what they should
    compare(match_qualdist_to_intervals(Scale('harmonic major').intervals), Major)
    compare(match_qualdist_to_intervals(Scale('melodic major').intervals), Major)
    compare(match_qualdist_to_intervals(Scale('lydian').intervals), Major)
    compare(match_qualdist_to_intervals(Scale('mixolydian').intervals), Major)

    compare(match_qualdist_to_intervals(Scale('double harmonic').intervals), Major)


    compare(match_qualdist_to_intervals(Scale('harmonic minor').intervals), Minor)
    compare(match_qualdist_to_intervals(Scale('melodic minor').intervals), Minor)
    compare(match_qualdist_to_intervals(Scale('dorian').intervals), Minor)
    compare(match_qualdist_to_intervals(Scale('phrygian').intervals), Minor)
    compare(match_qualdist_to_intervals(Scale('neapolitan major').intervals), Minor) # supposedly!
    compare(match_qualdist_to_intervals(Scale('neapolitan minor').intervals), Minor)
    compare(match_qualdist_to_intervals(Scale('hungarian minor').intervals), Minor)



    ### second: check that chord matching detects correct chords from notes
    inv_cmaj7 = Chord('GCEB')
    compare(matching_chords('GCEB', display=False), [Chord('Cmaj7')])
    compare(matching_chords('FD#A#', display=False), [Chord('A#sus4'), Chord('D#sus2')])


    # first, the chord progressions of some songs I'm practicing
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

    queen_of_argyll = ChordProgression('Em Bm Em Bm G Bm Em Bm Em D Bm Em D Em Bm G Bm Em D Em D Bm Em')
    compare(queen_of_argyll.key, Key('Em'))

    # other songs with different match cases:

    # # ( nuvole bianche doesn't currently work)
    # nuvole_bianche = ChordProgression('Fm Db Ab Eb')
    # compare(nuvole_bianche.key, Key('Ab'))
