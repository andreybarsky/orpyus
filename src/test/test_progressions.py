from ..progressions import *
from ..chords import Chord, AbstractChord, ChordList
from ..scales import MajorScale
from .testing_tools import compare

def unit_test():
    # test numeral parsing:
    seven, dim = parse_roman_numeral('viidim')
    compare([seven, dim], [7, AbstractChord('dim')])

    # test chordlist to numerals:
    compare(ChordList('Em11', 'Csus4', 'G7', 'Dmin9').as_numerals_in('G', modifiers=False, sep=' ', diacritics=False), 'vi IV I v')
    compare(ChordList('Em11', 'Csus4', 'G7', 'Dmin9').as_numerals_in('G', modifiers=True, sep=' ', diacritics=False), 'vi¹¹ IVˢ⁴ I⁷ v⁹')

    ### progression init by string or scalechords:
    compare(MajorScale.progression([2,5,1]), Progression(MajorScale.chords([2,5,1])))
    ### reparsing scalechords:
    compare(Progression(chords=[MajorScale.chord(d) for d in [2,5,1]]), Progression([MajorScale.chord(d) for d in [2,5,1]]))

    # test arithmetic operations on ScaleDegree objects:
    # compare(ScaleDegree('I') + 3, ScaleDegree('IV'))
    # compare(ScaleDegre('V') - 2, ScaleDegree('iii'))

    # and on ChordProgressions:
    compare(ChordProgression('C F G') + 7, ChordProgression('G C D'))

    # modifiermark parsing:
    compare(Progression('I-IV-vii°-I', scale='major'), Progression(['I', 'IV', 'viidim', 'I']))

    # progression slicing:
    compare(Progression('I IV V7 I').slice(1,3), Progression('IV V7'))

    # # TBI: fix however ignore_conflicting_case is supposed to work
    # compare(Progression('ii-iv-i-vi', ignore_conflicting_case=True), Progression(['ii', 'iv', 'i', 'VI'], scale='minor'))

    compare(ChordProgression('Am', 'Bdim', 'C', 'Dm'), ChordProgression([Chord('Am'), 'Bdim', Chord('C'), Chord('Dm')]))
    compare(ChordProgression('F#-C-Am-G-C'), ChordProgression(['F#', 'C', 'Am', 'G', 'C']))


    ### experimenting with ChordMotion and chromatic_lines

    ChordProgression('A6 - Cmaj7#11 - Emadd9', key='Em').find_chromatic_lines()

    ChordProgression('G, D/F#, Dm/F, A, C, D, A', key='A').find_chromatic_lines()
