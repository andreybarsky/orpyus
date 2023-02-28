from intervals import *

mode_names =     {1: 'ionian',
                  2: 'dorian',
                  3: 'phrygian',
                  4: 'lydian',
                  5: 'mixolydian',
                  6: 'aeolian',
                  7: 'locrian'}

mode_intervals = {1: [M2, M2, m2, M2, M2, M2, m2],
                  2: [M2, m2, M2, M2, M2, m2, M2],
                  3: [m2, M2, M2, M2, m2, M2, M2],
                  4: [M2, M2, M2, m2, M2, M2, m2],
                  5: [M2, M2, m2, M2, M2, m2, M2],
                  6: [M2, m2, M2, M2, m2, M2, M2],
                  7: [m2, M2, M2, m2, M2, M2, M2]}

mode_name_intervals = {name:mode_intervals[idx] for idx, name in mode_names.items()}
