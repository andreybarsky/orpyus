from muse.intervals import *

mode_idx_names = {1: 'ionian',
                  2: 'dorian',
                  3: 'phrygian',
                  4: 'lydian',
                  5: 'mixolydian',
                  6: 'aeolian',
                  7: 'locrian'}

mode_steps = {1: [2, 2, 1, 2, 2, 2, 1],
              2: [2, 1, 2, 2, 2, 1, 2],
              3: [1, 2, 2, 2, 1, 2, 2],
              4: [2, 2, 2, 1, 2, 2, 1],
              5: [2, 2, 1, 2, 2, 1, 2],
              6: [2, 1, 2, 2, 1, 2, 2],
              7: [1, 2, 2, 1, 2, 2, 2]}

mode_intervals = {idx: [Interval(i) for i in steps] for idx,steps in mode_steps.items()}

mode_name_intervals = {name:mode_intervals[idx] for idx, name in mode_idx_names.items()}

mode_intervals_from_tonic = {}
for idx, intervals in mode_intervals.items():
    intervals_from_tonic = [intervals[0]]
    for i in intervals[1:]:
        intervals_from_tonic.append(intervals_from_tonic[-1] + i)

    mode_intervals_from_tonic[idx] = intervals_from_tonic[:-1] # remove octave at end; it is always implied

mode_names = {mode_idx_names[i]: mode_intervals_from_tonic[i] for i in range(1,8)}

### TBI: (experimental?)
### generate modes fully procedurally from rotations of maj, min, and harmonic/melodic maj/min ascending scales

def rotate_scale(scale, num_steps):
    """Accepts a scale as iterable of note-like objects, and returns the scale
    that begins num_steps up from the tonic of that scale,
    equivalent to the (num_steps+1)th mode of the scale that starts there"""

    rotated_tonic_place = num_steps
    rotated_scale_idxs = [(rotated_tonic_place + i) % 7 for i in range(7)]
    rotated_scale = [scale[i] for i in rotated_scale_idxs]
    return rotated_scale

if __name__ == '__main__':
    from muse.scales import Key, key_intervals
    from muse.intervals import stacked_intervals

    # ref_major = Key('C')
    # ref_minor = Key('Cm')
    # ref_melmaj = Key('C melodic major')
    # ref_melmin = Key('C melodic major')
    # ref_harmaj = Key('C harmonic major')
    # ref_harmin = Key('C harmonic minor')
    # ref_keys = [ref_major, ref_minor, ref_harmaj, ref_harmin, ref_melmaj, ref_melmin]


    # major_intervals = key_intervals['major']
    # minor_intervals = key_intervals['minor']
    # hmaj_intervals = key_intervals['harmonic major']
    # hmin_intervals = key_intervals['harmonic minor']
    # mmaj_intervals = key_intervals['melodic major']
    # mmin_intervals = key_intervals['melodic minor']

    key_qualities = ['major', 'minor', 'harmonic major', 'harmonic minor', 'melodic major', 'melodic minor']

    for quality in key_qualities:
        intervals_from_tonic = key_intervals[quality]
    # for intervals_from_tonic in [major_intervals, minor_intervals, hmaj_intervals, hmin_intervals, mmaj_intervals, mmin_intervals]:

        for mode_degree in range(1, 8):
            # if mode_degree != 1: # 1st mode does not change
            relative_intervals = stacked_intervals(list(intervals_from_tonic) + [P8])
            rotated_relative_intervals = rotate_scale(relative_intervals, mode_degree-1)
            mode_intervals_from_tonic = [rotated_relative_intervals[i] + sum(rotated_relative_intervals[:i]) for i in range(7)]
            mode_interval_short_names = [f'{i.quality[:3]}{i.expected_degree}' for i in mode_intervals_from_tonic]
            mode_interval_short_names[-1] = 'per8'
            print(f'mode *{mode_degree}* of {quality} key: {mode_interval_short_names}')
        print()

        #
        #     if quality == 'major':
        #         assert rotated_relative_intervals == mode_intervals[mode_degree], f"{rotated_relative_intervals}\nDoes not equal: \n{mode_intervals[mode_degree]}"
        #         print(f'Which is equal to the intervals of the {mode_degree}th mode: {mode_intervals[mode_degree]}')
        #
        #
        # print('\n===========\n')

    # for ref_key in ref_keys:
    #     for mode_degree in range(1, 8):
    #         scale_rotated = rotate_scale(ref_key.scale, mode_degree-1)
    #         this_mode_tonic = scale_rotated[0]
    #         this_mode_intervals_from_tonic = [n - this_mode_tonic for n in scale_rotated[1:]] + [P8] # add octave onto the end
    #         this_mode_intervals = stacked_intervals(this_mode_intervals_from_tonic)

    # alternate method:
