from ..intervals import *
from ..scales import *
from ..chords import AbstractChord
from .testing_tools import compare

def unit_test():

    ### NewScales:

    # test scale factor/degree distinction:
    compare(Scale(ScaleFactors('1,2,3,5,6')).degree_intervals[4], P5) # the fourth degree of the maj pent scale is a P5
    compare(Scale(ScaleFactors('1,2,3,5,6')).factor_intervals[5], P5) # which is also the 5th _factor_ of the maj pent scale

    # test scale init by name:
    compare(Scale('minor natural'), Scale('nat min'))
    compare(Scale('maj pent'), Scale('pentatonic major'))

    compare(Scale('major').mode(6), Scale('minor'))
    compare(Scale('major', mode=6), Scale('minor'))

    compare(Scale('harmonic major b6'), Scale('major natural'))

    # test mode retrieval by name:
    compare(mode_name_intervals['natural major'], get_modes('natural major')[1])

    print('Test scale init by intervals:')
    compare(Scale('major'), Scale(intervals=scale_name_intervals['natural major']))

    print('Test chords built on Scale degrees:')
    compare(Scale('minor').chord(2), AbstractChord('dim'))
    compare(Scale('major').chord(5, order=5), AbstractChord('dom9'))

    print('Scales underlying the common 13th chords:')
    compare(Scale('lydian').chord(1, order=7), AbstractChord('maj13'))
    compare(Scale('mixolydian').chord(1, order=7), AbstractChord('13'))
    compare(Scale('dorian').chord(1, order=7), AbstractChord('m13'))
    compare(Scale('lydian b3').chord(1, order=7), AbstractChord('mmaj13'))

    print('Subscales:')
    compare(Scale('major').pentatonic.intervals, [2, 4, 7, 9])
    compare(Scale('minor').blues.intervals, [3, 5, 6, 7, 10])

    compare(Subscale('pentatonic minor')[3], m3)
    compare(Subscale('blues minor').intervals[2], Scale('minor').blues.chromatic_intervals[0])

    # test neighbours:
    major_neighbours = Scale('natural major').neighbouring_scales
    print(f'Neighbours of natural major scale:')
    for a, sc in major_neighbours.items():
        print(f'with {a.name}: {sc}')

    # extreme test case: do we crash if computing neighbours for every possible scale?
    for intvs, names in interval_mode_names.items():
        name = names[0]
        sc = Scale(name)
        neighbours = sc.neighbouring_scales
        # print(f'{name} scale has {len(neighbours)} neighbours')

    print('Valid chords from scale degrees:')
    Scale('major').valid_chords(4, inversions=True)

    Scale('harmonic minor').valid_chords(4, 6)

    #### TBI: (bug?)
    Scale(intervals=[2,1,2,2,1,2], stacked=False) # returns error?

    # which modes correspond to which 13 chords?

    _13chords = '13', 'maj13', 'min13', 'mmaj13', 'dim13'
    for chord_name in _13chords:
        c = AbstractChord(chord_name)
        chord_intervals = c.intervals
        s = Scale(intervals=chord_intervals)
        alias_str = f" (aka: {', '.join(s.aliases)})" if len(s.aliases) > 0 else ''

        print(f'\n{c}')
        print(f'  flattened intervals: {c.intervals.flatten()}')
        print(f'    unstacked intervals: {s.intervals.unstack()}')
        print(f'------associated scale: {s}{alias_str}')



    # display all scale consonances:
    include_subscales = False
    all_consonances = {}
    for ivs, scs in interval_mode_names.items():
        sc = Scale(scs[0])
        all_consonances[sc] = sc.consonance
    if include_subscales:
        for subsc, als in subscales_to_aliases.items():
            all_consonances[subsc] = subsc.consonance

    sorted_scales = sorted(all_consonances, key=lambda x: all_consonances[x], reverse=True)
    cons_names = [sc.name for sc in sorted_scales]
    cons_values = [all_consonances[sc] for sc in sorted_scales]

    # cons_names, cons_values = [sc.name for sc in all_consonances.keys()], [c for c in all_consonances.values()]

    descriptors = []
    aliases = []
    for cons_name in cons_names:
        if cons_name in base_scale_names:
            # full_names.append(f'{cons_name}')
            descriptors.append('')
            this_aliases = list(set(mode_name_aliases[cons_name]))
        elif cons_name in subscales_by_name:
            subsc = subscales_by_name[cons_name]
            descriptors.append(f'subscale of {subsc.parent_scale.name} scale')
            this_aliases = []
        else:
            base, mode = mode_lookup[cons_name]
            descriptors.append(f'mode {mode} of {base} scale')
            this_aliases = list(set(mode_name_aliases[cons_name]))
        aliases.append(this_aliases)

    longest_name = max([len(c) for c in cons_names])
    longest_desc = max([len(d) for d in descriptors])

    # rows = zip(cons_names, cons_values)
    # rows = rows.sorted(lambda x: (x[1]), reverse=True)

    print('====================================\n')
    print('Modes/scales by pairwise consonance:\n')

    print(f'consonance {"    scale name":{longest_name}}   {"    mode rotation":{longest_desc}}           aliases')
    print('---------------------------------------------------------------------------------------------------')
    for i, (name, desc, value, this_aliases) in enumerate(zip(cons_names, descriptors, cons_values, aliases)):
        if i % 4 == 0:
            print('')
        print(f'  {value:.3f}       {name:{longest_name}}   {desc:{longest_desc}}      {", ".join(this_aliases)}')

    import numpy as np
    print(f'Highest consonance: {np.max(cons_values):.05f} ({cons_names[np.argmax(cons_values)]})')
    print(f'Lowest consonance: {np.min(cons_values):.05f} ({cons_names[np.argmin(cons_values)]})')
    # import matplotlib.pyplot as plt
