from muse.intervals import *
from muse.scales import Key, key_names

mode_idx_names =     {1: 'ionian',
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

mode_name_intervals = {name:mode_intervals[idx] for idx, name in mode_names.items()}

mode_intervals_from_tonic = {}
for idx, intervals in mode_intervals.items():
    intervals_from_tonic = [intervals[0]]
    for i in intervals[1:]:
        intervals_from_tonic.append(intervals_from_tonic[-1] + i)

    mode_intervals_from_tonic[idx] = intervals_from_tonic[:-1] # remove octave at end; it is always implied

for idx, key_spec in mode_intervals_from_tonic.items():
    if tuple(key_spec) in key_names.keys():
        print(f'{mode_names[idx]} is equivalent to:{key_names[tuple(key_spec)][-1]}')

mode_names = {mode_idx_names[i]: mode_intervals_from_tonic[i] for i in range(1,8)}

# print(mode_intervals_from_tonic[1])
