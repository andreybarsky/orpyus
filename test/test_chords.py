from .util import compare, log
from orpyus.chords import Chord, AbstractChord, ChordFactors, Interval, matching_chords, most_likely_chord

def test_chords(verbose=False):
    log.verbose=verbose

    # test inversion by factor/bass, AbstractChord->Chord initialisation, and unusual note names:
    compare(Chord('E#m7/C'), AbstractChord('m7/2').on_root('F'))
    compare(Chord('E#m7/C'), AbstractChord('m7/2').on_bass('C'))
    # test correct production of root notes/intervals and inverted notes/intervals:
    compare(Chord('Am/C').root_notes, Chord('Am').root_notes)
    compare(Chord('Am/C').root_intervals, Chord('Am').root_intervals)
    compare(Chord('Am/C').notes, Chord('C6(no5)').notes)
    compare(Chord('Am/C').intervals, Chord('C6(no5)').intervals)

    # test magic methods: transposition:
    compare(Chord('Caug7') + Interval(4), Chord('Eaug7'))

    # parallels and relatives:
    compare(Chord('C').parallel, Chord('Cm'))
    compare(Chord('C').relative, Chord('Am'))
    compare(~Chord('Caug'), Chord('Adim'))

    # test chord membership:
    compare(4 in AbstractChord('sus4'), True)
    compare(Interval(4) in AbstractChord('sus4'), False)
    compare('C' in Chord('Am'), True)

    # test chord matching by notes:
    print(matching_chords('CEA'))

    # test chord abstraction:
    compare(Chord('Cmaj7sus2').abstract(), AbstractChord('maj7sus2'))

    # test chord factor init by strings and lists:
    compare(ChordFactors('1-♭3-b5'), ChordFactors(['1', '♭3', 'b5']))

    # test chord inversion identification from intervals:
    compare(AbstractChord(intervals=[0, 4, 9]), AbstractChord('m/1'))

    # test recursive init for non-existent bass note inversions:
    compare(Chord('D/C#'), Chord('Dmaj7/C#'))
    compare(Chord('Amaj7/B'), Chord('B13sus4'))

    # test arg re-parsing
    compare(Chord('CEA'), Chord(notes='CEA'))
    # (this one also tests automatic chord factor detection from uninitialised intervals:
    # Interval(8) is a minor sixth by default but here we parse it as the fifth in an aug chord)
    compare(Chord([4,8], root='C'), Chord('C+'))

    # test repeated interval parsing:
    compare(Chord('CEGCEGC'), Chord('C'))
    compare(Chord('CEGDGD'), Chord('Cadd9'))

    # chord init by re-casting:
    compare(Chord(Chord('Cdim9/Eb')), Chord('Cdim9/Eb'))

    log.verbose = False

    compare(most_likely_chord('CEAB'), Chord('Amadd9/C'))
