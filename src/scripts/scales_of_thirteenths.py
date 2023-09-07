import chords, scales
# which scales correspond to which 13th chords?

_13chords = '13', 'maj13', 'min13', 'mmaj13', 'dim13'
for chord_name in _13chords:
    c = chords.AbstractChord(chord_name)
    chord_intervals = c.intervals
    s = scales.Scale(intervals=chord_intervals.flatten())
    alias_str = f" (aka: {', '.join(s.aliases)})" if len(s.aliases) > 0 else ''

    print(f'\n{c}')
    print(f'  flattened intervals: {c.intervals.flatten()}')
    print(f'    unstacked intervals: {s.intervals.unstack()}')
    print(f'------associated scale: {s}{alias_str}')
