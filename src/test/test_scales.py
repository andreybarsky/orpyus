from ..intervals import *
from ..scales import *
from ..chords import AbstractChord
from .testing_tools import compare
from ..display import DataFrame

def unit_test():

    ### new Scale class, after refactor:

    # test scale factor/degree distinction:
    compare(Scale(ScaleFactors('1,2,3,5,6')).degree_intervals[4], P5) # the fourth degree of the maj pent scale is a P5
    compare(Scale(ScaleFactors('1,2,3,5,6')).factor_intervals[5], P5) # which is also the 5th _factor_ of the maj pent scale

    # test scale init by name:
    compare(Scale('minor natural'), Scale('nat min'))
    compare(Scale('maj pent'), Scale('pentatonic major'))

    compare(Scale('major').mode(6), Scale('minor'))
    compare(Scale('major', mode=6), Scale('minor'))

    compare(Scale('harmonic major b7'), Scale('melodic major'))

    # test modes of pentatonic scales:
    compare(Scale('hirajoshi').mode(2).intervals, Scale('hirajoshi').intervals.mode(2))

    # test utility methods on heptatonic/pentatonic scales:
    compare(Scale('mixo').nearest_natural_scale, Scale('major pent').nearest_natural_scale)
    compare(Scale('melodic major').is_mode_of(Scale('melodic minor')), True)
    compare(Scale('harmonic major').is_mode_of(Scale('harmonic minor')), False)

    print('Test scale init by intervals:')
    compare(Scale('major'), Scale(intervals=canonical_scale_name_intervals['natural major'][0]))
    # by unstacked intervals:
    compare(Scale([2,1,2,2,1,2]), Scale([2,3,5,7,8,10]))


    print('Test chords built on Scale degrees:')
    compare(Scale('minor').chord(2, linked=False), AbstractChord('dim'))
    compare(Scale('major').chord(5, order=5, linked=False), AbstractChord('dom9'))

    print('Scales underlying the common 13th chords:')
    compare(Scale('lydian').chord(1, order=7), AbstractChord('maj13#11'))
    compare(Scale('mixolydian').chord(1, order=7), AbstractChord('13'))
    compare(Scale('dorian').chord(1, order=7), AbstractChord('m13'))
    compare(Scale('lydian b3').chord(1, order=7), AbstractChord('mmaj13'))

    # init multiple chords at once:
    compare(Scale('major').get_chords([1,4,5]), [Scale('major').chord(d) for d in [1,4,5]])

    print('Subscales:')
    compare(Scale('major').pentatonic.intervals, [0, 2, 4, 7, 9])
    compare(Scale('minor blues').intervals, [0, 3, 5, 6, 7, 10])

    compare(Scale('pentatonic minor').factor_intervals[3], m3)
    compare(Scale('blues minor').factors.chromatic.as_intervals[0], Scale('minor blues').chromatic_intervals[0])


    ### matching_scales:
    compare(list(matching_scales('I iii V7', display=False, candidate_scales=[MajorScale, MinorScale])), [Scale('major')])
    # compare(matching_scales('i bIII V7', display=False), [Scale('extended minor'), Scale('full minor')])

    # test input by pairs vs input by numerals:
    degree_chord_pairs = [(1, AbstractChord('min')), (5, AbstractChord('7')), (7, AbstractChord('maj'))]
    compare(matching_scales(degree_chord_pairs, display=False), matching_scales('i V7 VII', display=False))


    # test scalechord parsing:
    compare(ScaleChord('III'), Scale('minor').chord(3))

    # test secondary chords:
    # compare(ScaleChord('V7/V'), ScaleChord('dom7', degree=2, scale='major'))

    # test neighbours:
    major_neighbours = Scale('natural major').neighbouring_scales
    print(f'Neighbours of natural major scale:')
    for sc in major_neighbours:
        print(sc)

    # extreme test case: do we crash if computing neighbours for every possible scale?
    for intvs, name in canonical_scale_interval_names.items():
        sc = Scale(name)
        neighbours = sc.neighbouring_scales
        # print(f'{name} scale has {len(neighbours)} neighbours')

    print('Valid chords from scale degrees:')
    Scale('major').valid_chords_on(4, inversions=True)

    Scale('harmonic minor').valid_chords_on(4, order=6)
