from ..chords import Chord, AbstractChord, ChordFactors, Interval, most_likely_chord
from .testing_tools import compare

def unit_test():

    # test inversion by factor/bass, AbstractChord->Chord initialisation, and unusual note names:
    compare(Chord('E#m7/C'), AbstractChord('m7/2').on_root('F'))
    compare(Chord('E#m7/C'), AbstractChord('m7/2').on_bass('C'))
    # out-of-bounds inversion:
    compare(Chord('Cmaj7/5'), Chord('Cmaj7/E'))
    compare(Chord('Cmaj7/-1'), Chord('Cmaj7/B'))
    # some other potential failure cases:
    compare(Chord('Am7/F'), Chord('Fmaj9'), 'enharmonic')
    compare(Chord('ACEF'), Chord('Fmaj7/A'))
    # including a big one: inversion of compound chords:
    compare(Chord('CFBbEb'), Chord('C7♯9sus4(no5)'))

    # test correct production of root notes/intervals and inverted notes/intervals:
    compare(Chord('Am/C').root_notes, Chord('Am').root_notes)
    compare(Chord('Am/C').root_intervals, Chord('Am').root_intervals)
    compare(Chord('Am/C').notes, Chord('C6(no5)').notes)
    compare(Chord('Am/C').intervals, Chord('C6(no5)').intervals)

    # test recursive/arbitrary alterations:
    compare(Chord('Emaj7#9'), Chord('Eadd#9add7'))

    # test magic methods: transposition:
    compare(Chord('Caug7') + Interval(4), Chord('Eaug7'))
    # arithmetic with notes:
    compare(Chord('C') + 'B', Chord('Cmaj7'))
    compare(Chord('C7') - 'Bb', Chord('C'))
    # recursive addition with list:
    compare(Chord('C') + ['B', 2], Chord('Dmaj7'))

    # parallels and relatives:
    compare(Chord('C').parallel, Chord('Cm'))
    compare(Chord('C').relative, Chord('Am'))
    compare(~Chord('Caug'), Chord('Adim'))

    # test chord membership:
    compare(4 in AbstractChord('sus4'), True) # by factor
    compare(Interval(4) in AbstractChord('sus4'), False) # by interval
    compare('C' in Chord('Am'), True)

    # test chord matching by notes:
    # (should be in test_matching module)
    #print(matching_chords('CEA'))

    # test chord abstraction:
    compare(Chord('Cmaj7sus2').abstract(), AbstractChord('maj7sus2'))

    compare(Chord('C/G').abstract(), AbstractChord('maj/2'))

    # test chord factor init by strings and lists:
    compare(ChordFactors('1-♭3-b5'), ChordFactors(['1', '♭3', 'b5']))

    # test chord inversion identification from intervals:
    compare(AbstractChord(intervals=[0, 4, 9]), AbstractChord('m/1'))

    # test recursive init for non-existent bass note inversions:
    compare(Chord('D/C#'), Chord('Dmaj7/C#'))
    compare(Chord('Amaj7/B'), Chord('Amaj9/B'))

    # test implicit inversion identification:
    compare(Chord('CEA'), Chord('Am/C'))
    # (this one also tests automatic chord factor detection from uninitialised intervals:
    # Interval(8) is a minor sixth by default but here we parse it as the fifth in an aug chord)
    compare(Chord([4,8], root='C'), Chord('C+'))

    # test repeated interval parsing:
    compare(Chord('CEGCEGC'), Chord('C'))
    compare(Chord('CEGDGD'), Chord('Cadd9'))

    # chord init by re-casting:
    compare(Chord(Chord('Cdim9/Eb')), Chord('Cdim9/Eb'))

    compare(most_likely_chord('CEAB', invert=True), Chord('Amadd9/C'))
    compare(most_likely_chord('CEAB', invert=False), Chord('Amadd9'))
