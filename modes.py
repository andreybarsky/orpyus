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
    from scales import Key, key_intervals
    major_intervals = key_intervals['major']
    minor_intervals = key_intervals['minor']
    ref_major = Key('C')
    ref_minor = Key('Cm')

    for mode_degree in range(1, 8):
        major_rotated = rotate_scale(ref_major.scale, mode_degree-1)
        major_mode_tonic = major_rotated[0]
        this_mode_intervals = [n - major_mode_tonic for n in major_rotated[1:]]
        print(f'Mode {mode_degree} of {major_mode_tonic}: {this_mode_intervals}')
