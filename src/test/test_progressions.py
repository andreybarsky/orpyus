from ..progressions import Progression, ChordProgression, parse_roman_numeral
from ..chords import Chord, AbstractChord
from
from .testing_tools import compare

def unit_test():
    # test numeral parsing:
    seven, dim = parse_roman_numeral('viidim')
    compare([seven, dim], [7, AbstractChord('dim')])

    # test chordlist to numerals:
    compare(ChordList('Em11', 'Csus4', 'G7', 'Dmin9').as_numerals_in('G', modifiers=False, sep=' '), 'vi IV I v')
    compare(ChordList('Em11', 'Csus4', 'G7', 'Dmin9').as_numerals_in('G', modifiers=True, sep=' '), 'vi¹¹ IVs4 I⁷ v⁹')

    # test arithmetic operations on ScaleDegree objects:
    # compare(ScaleDegree('I') + 3, ScaleDegree('IV'))
    # compare(ScaleDegre('V') - 2, ScaleDegree('iii'))
    compare(Progression('I-IV-vii°-I', scale='major'), Progression(['I', 'IV', 'viidim', 'I']))

    # # TBI: fix however ignore_conflicting_case is supposed to work
    # compare(Progression('ii-iv-i-vi', ignore_conflicting_case=True), Progression(['ii', 'iv', 'i', 'VI'], scale='minor'))

    compare(ChordProgression('Am', 'Bdim', 'C', 'Dm'), ChordProgression([Chord('Am'), 'Bdim', Chord('C'), Chord('Dm')]))
    compare(ChordProgression('F#-C-Am-G-C'), ChordProgression(['F#', 'C', 'Am', 'G', 'C']))
