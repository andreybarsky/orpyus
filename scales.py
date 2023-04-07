from intervals import *
# from scales import interval_scale_names, key_name_intervals
from util import rotate_list, log
from parsing import num_suffixes
import notes as notes
import pdb


class ScaleDegree:
    """The degrees of a scale, with modulo arithmetic defined over them"""

    def __init__(self, degree):
        # accept re-casting:
        if isinstance(degree, ScaleDegree):
            self.value = degree.value
        else:
            assert isinstance(degree, int), f'ScaleDegree received invalid init arg, expected int but got: {degree}'
            if (degree < 1) or (degree > 7):
                degree = ((degree-1) % 7) + 1
            self.value = degree

    def __add__(self, other):
        assert isinstance(other, (int, Interval))
        other_val = int(other)
        return ScaleDegree(self.value + other_val)
        # # mod back to range 1-7
        # new_degree = ((new_degree-1) % 7) + 1

    def __sub__(self, other):
        assert isinstance(other, (int, Interval))
        return self + (-other)

    def __str__(self):
        return f'{self.value}\u0302' # unicode circumflex character

    def __repr__(self):
        return str(self)

    def __int__(self):
        return self.value

    def __eq__(self, other):
        if isinstance(other, ScaleDegree):
            return self.value == other.value
        else:
            raise TypeError(f'__eq__ not defined between ScaleDegree and {type(other)}')

    def __hash__(self):
        return hash(str(self))

    def fifth_distance(self, other):
        return interval_distance(self, other, 4)

    def fourth_distance(self, other):
        return interval_distance(self, other, 3)

    def third_distance(self, other):
        return interval_distance(self, other, 2)

    def second_distance(self, other):
        return interval_distance(self, other, 1)



def interval_distance(deg1, deg2, step_degree):
    """distance between two scale-degrees, in degree-interval steps"""
    assert step_degree in range(1,8), f'Invalid step degree for counting interval distance between ScaleDegrees: {step_degree}'
    deg1 = ScaleDegree(deg1)
    distance = 0
    # count in two directions simultaneously, return the lowest:
    pos_proxy = ScaleDegree(deg2)
    neg_proxy = ScaleDegree(deg2)
    while (pos_proxy != deg1) and (neg_proxy != deg1):
        pos_proxy += step_degree
        neg_proxy -= step_degree
        distance += 1
    if pos_proxy == deg1:
        return -distance
    elif neg_proxy == deg1:
        return distance

### TBI: should scales be able to be modified by ChordQualifiers or something similar, like ChordFactors can?
class Scale:
    """a hypothetical scale not built on any specific note,
    but defined by a series of intervals from its tonic"""
    def __init__(self, scale_name: str):
        self.name, self.intervals, self.base_scale, self.rotation = self._parse_input(scale_name)

        # determine quality by asking: is the third major or minor
        self.quality = self.intervals[2].quality

        # build own ScaleDegrees:
        self.degrees = {ScaleDegree(1): Unison}
        for d, i in enumerate(self.intervals):
            degree = ScaleDegree(d+2)
            self.degrees[degree] = i

    def __contains__(self, item):
        return item in self.intervals

    def _parse_input(self, inp):
        # if input is an existing scale, just keep it:
        if isinstance(inp, Scale):
            return inp.name, inp.intervals, inp.base_scale, inp.rotation
        elif isinstance(inp, str):
            if inp in mode_lookup:
                base_scale, rotation = mode_lookup[inp]
            else:
                raise ValueError(f'{inp} does not seem to correspond to a valid rotation of a base scale')

            if inp in mode_name_intervals:
                intervals = mode_name_intervals[inp]
            else:
                raise ValueError(f'{inp} does not seem to correspond to a valid set of intervals')

            name = interval_mode_names[intervals][-1]

            return name, intervals, base_scale, rotation

        elif isinstance(inp, (list, tuple)):
            # received a list, parse it as a series of intervals:
            intervals = tuple([Interval(i) for i in inp])
            name = interval_mode_names[intervals][-1]
            base_scale, rotation = mode_lookup[name]
            return name, intervals, base_scale, rotation
        else:
            raise TypeError(f'Invalid input to Scale init: expected scale_name string, or iterable of intervals, or Scale object, but got: {type(inp)}')

    @staticmethod
    def from_intervals(interval_key):
        scale_name = interval_mode_names[interval_key]
        return Scale(scale_name)

    def __str__(self):
        return f'Scale:{self.name}'

    def __repr__(self):
        return str(self)

    def __len__(self):
        return len(self.scale)

    def __eq__(self, other):
        if isinstance(other, Scale):
            return self.intervals == other.intervals
        else:
            raise TypeError(f'__eq__ not defined between Scale and {type(other)}')

    def __getitem__(self, d):
        d = ScaleDegree(d)
        return self.degrees[d]


    @property
    def pentatonic(self):
        if self.quality.major: # and self.natural?
            pent_scale = [self[s] for s in [1,2,3,5,6]]
        elif self.quality.minor: # and self.natural?
            pent_scale = [self[s] for s in [1,3,4,5,7]]
        return pent_scale


# standard keys are: natural/melodic/harmonic majors and minors

# dict mapping 'standard' key intervals to all accepted aliases for scale qualities
interval_scale_names = {
    (Maj2, Maj3, Per4, Per5, Maj6, Maj7): ['', 'maj', 'M', 'major', 'natural major' ],
    (Maj2, Min3, Per4, Per5, Min6, Min7): ['m', 'min', 'minor', 'natural minor' ],

    (Maj2, Maj3, Per4, Per5, Min6, Maj7): ['maj harmonic', 'M harmonic', 'harmonic major',],
    (Maj2, Min3, Per4, Per5, Min6, Maj7): ['m harmonic', 'harmonic minor'],
    (Maj2, Maj3, Per4, Per5, Min6, Min7): ['maj melodic', 'M melodic', 'melodic major'],
    (Maj2, Min3, Per4, Per5, Maj6, Maj7): ['m melodic', 'm melodic', 'jazz minor', 'melodic minor ascending', 'melodic minor'], # note: ascending only
    # "melodic minor" can refer to using the the natural minor scale when descending, but that is TBI
    }

# 'proper' name is listed last, short suffix is listed first:
standard_scale_names = list([names[-1] for names in interval_scale_names.values()])
standard_scale_suffixes = list([names[0] for names in interval_scale_names.values()])

#### here we define the 'base scales': natural major, melodic minor, harmonic minor/major
# which are those scales that are not modes of other scales
# and the names their modes are known by
base_scale_names = ['major', 'melodic minor', 'harmonic minor', 'harmonic major']
# note that melodic major modes are just rotations of melodic minor modes
# this is technically true in the reverse as well, but 'melodic minor' is more common / well-known than mel. major

# this dict maps base scale names to dicts that map scale degrees to the modes of that base scale
mode_idx_names = {
          'major': {1: ['ionian'], 2: ['dorian'], 3: ['phrygian'], 4: ['lydian'],
                    5: ['mixolydian'], 6: ['aeolian'], 7: ['locrian']},
  'melodic minor': {1: ['athenian'], 2: ['phrygian ♯6', 'cappadocian', 'dorian ♭2'],
                    3: ['lydian augmented', 'asgardian'], 4: ['lydian dominant', 'pontikonisian'],
                    5: ['aeolian dominant', 'olympian', 'mixolydian ♭6'],
                    6: ['half-diminished', 'sisyphean'], 7: ['altered dominant', 'palamidian']},
 'harmonic minor': {1: ['harmonic minor'], 2: ['locrian ♯6'], 3: ['ionian ♯5'], 4: ['ukrainian dorian'],
                    5: ['phrygian dominant'], 6: ['lydian ♯2'], 7: ['altered diminished']},
 'harmonic major': {1: ['harmonic major'], 2: ['dorian ♭5', 'locrian ♯2♯6'], 3: ['phrygian ♭4', 'altered dominant ♯5'],
                    4: ['lydian ♭3', 'melodic minor ♯4'], 5: ['mixolydian ♭2'],
                    6: ['lydian augmented ♯2'], 7: ['locrian ♭♭7']}
                 }


## dict mapping all accepted (standard) key quality names to lists of their intervals:
scale_name_intervals = {}
# dict mapping valid whole names of each possible key (for every tonic) to a tuple: (tonic, intervals)

for intervals, names in interval_scale_names.items():
    for scale_name_alias in names:
        scale_name_intervals[scale_name_alias] = intervals


# keys arranged vaguely in order of rarity, for auto key detection/searching:
common_suffixes = ['', 'm']
uncommon_suffixes = ['m harmonic', 'm melodic']
rare_suffixes = ['maj harmonic', 'maj melodic']
# very_rare_key_suffixes = [v[0] for v in list(interval_scale_names.values()) if v[0] not in (common_key_suffixes + uncommon_key_suffixes + rare_key_suffixes)]

def get_modes(scale_name):
    """for a given scale name, fetch the intervals of that scale
    and return the 7 rotations of that scale as its modes,
    in a dict mapping mode_degrees to lists of intervals from tonic"""
    this_mode_names = mode_idx_names[scale_name]
    this_mode_intervals_from_tonic = scale_name_intervals[scale_name]
    this_mode_degrees_to_intervals = {}
    for degree in range(1,8):
        this_mode_degrees_to_intervals[degree] = rotate_mode_intervals(this_mode_intervals_from_tonic, degree)
    return this_mode_degrees_to_intervals

def rotate_mode_intervals(scale_intervals_from_tonic, degree):
    """given a list of 6 intervals from tonic that describe a key/scale,
    e.g.: (maj2, maj3, per4, per5, maj6, maj7),
    and an integer degree between 1 and 7 (inclusive),
    return the mode of that scale corresponding to that degree"""
    assert len(scale_intervals_from_tonic) == 6, """list of intervals passed to rotate_mode_intervals must exclude tonics (degrees 1 and 8), and so should be exactly 6 intervals long"""

    relative_intervals = stacked_intervals(list(scale_intervals_from_tonic) + [P8])
    rotated_relative_intervals = rotate_list(relative_intervals, degree-1)
    mode_intervals_from_tonic = [rotated_relative_intervals[i] + sum(rotated_relative_intervals[:i]) for i in range(6)]
    # turn intervals into IntervalDegrees to probably parse e.g. aug4s over dim5s
    mode_intervals_from_tonic = [IntervalDegree(i.value, degree=j+2) for j, i in enumerate(mode_intervals_from_tonic)]
    return mode_intervals_from_tonic


# in this loop we build the mode_lookup dict that connects mode aliases to their corresponding identifiers as (base, degree) tuples
# and also construct the interval_mode_names dict that connects interval tuples to corresponding mode names
mode_lookup = {}   # lookup of any possible name for a key/scale/mode, i.e. 'natural minor' or 'aeolian' or 'phrygian dominant', to tuples of (base_scale, degree)
interval_mode_names = {}  # lookup of interval tuples to the names that scale is known by
non_scale_interval_mode_names = {} # a subset of interval_mode_names that does not include modes enharmonic to base scales

mode_bases = list(mode_idx_names.keys())  # same as base_scale_names
for base in mode_bases:
    intervals_from_tonic = scale_name_intervals[base]

    for degree, name_list in mode_idx_names[base].items():
        th = num_suffixes[degree]
        proper_name = f'{base} scale, {degree}{th} mode'
        simple_name = f'{base} mode {degree}'
        preferred_name = name_list[0] if len(name_list) > 0 else proper_name
        full_name_list = [preferred_name, proper_name, simple_name] + name_list[1:]
        # do some string augmentation to catch all the possible ways we might refer to a scale:
        full_name_list.extend([name.replace('♭', 'b') for name in name_list if '♭' in name])
        full_name_list.extend([name.replace('♯', '#') for name in name_list if '♯' in name])
        full_name_list.extend([f' {name}' for name in full_name_list])
        full_name_list.extend([f'{name} scale' for name in full_name_list])
        if degree == 1:
            full_name_list.extend([f'{base} scale'])

        # attach every possible name a mode could have, to a tuple of its base and degree:
        for full_name in full_name_list:
            mode_hashkey = (base, degree)
            mode_lookup[full_name] = mode_hashkey

        mode_intervals_from_tonic = rotate_mode_intervals(intervals_from_tonic, degree)
        mode_interval_from_tonic_short_names = [f'{i.quality[:3]}{i.degree}' for i in mode_intervals_from_tonic]
        mode_interval_from_tonic_short_names = ', '.join(mode_interval_from_tonic_short_names)
        log(f'mode *{degree}* of {base} key: {mode_interval_from_tonic_short_names}')

        this_mode_names = mode_idx_names[base][degree]
        this_mode_names.extend([f'{m} scale' for m in this_mode_names])


        interval_key = tuple(mode_intervals_from_tonic)

        log(f'  also known as: {", ".join(this_mode_names)}')

        # workaround: we want the 'suffix' and 'scale_name' for modes to be the common mode name itself
        # so we append a copy of the first mode name to each list, so that it acts as first and last:
        this_mode_names.extend(this_mode_names[:1])

        if interval_key in interval_scale_names.keys():
            log(f'--also enharmonic to:{interval_scale_names[interval_key][-1]} scale')
            # add non-mode scale names to mode_lookup too: e.g. mode_lookup['natural minor'] returns ('major', 6)
            for name in interval_scale_names[interval_key]:
                mode_lookup[name] = mode_hashkey
                # add standard scale names to the interval_scale_names lookup too:
                this_mode_names.append(name) # (this also means the last standard scale name becomes the standard lookup name)
        else: # record the modes that are not enharmonic to base scales in a separate dict
            non_scale_interval_mode_names[interval_key] = this_mode_names

        interval_mode_names[interval_key] = this_mode_names




    log('=========\n')

######################
# important output: reverse dict that maps all mode names to their intervals:
mode_name_intervals = {}
for intervals, names in interval_mode_names.items():
    for name in names:
        mode_name_intervals[name] = intervals
######################

def unit_test():
    test(mode_name_intervals['natural major'], tuple(get_modes('major')[1]))
    test(Scale('major'), Scale(scale_name_intervals['natural major']))

if __name__ == '__main__':
    unit_test()
