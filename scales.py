from intervals import *
# from scales import interval_scale_names, key_name_intervals
from util import rotate_list, unpack_and_reverse_dict, check_all, log
from chords import AbstractChord, chord_names_by_rarity, chord_names_to_intervals, chord_names_to_factors
from qualities import ChordQualifier
from parsing import num_suffixes
import notes as notes
import pdb


# standard keys are: natural/melodic/harmonic majors and minors

# dict mapping 'standard' key intervals to all accepted aliases for scale qualities
# 'proper' name is listed last, short suffix is listed first:
interval_scale_names = {
    IntervalList(Maj2, Maj3, Per4, Per5, Maj6, Maj7): ['', 'maj', 'M', 'major', 'natural major' ],
    IntervalList(Maj2, Min3, Per4, Per5, Min6, Min7): ['m', 'min', 'minor', 'natural minor' ],

    IntervalList(Maj2, Maj3, Per4, Per5, Min6, Maj7): ['maj harmonic', 'M harmonic', 'harmonic major',],
    IntervalList(Maj2, Min3, Per4, Per5, Min6, Maj7): ['m harmonic', 'harmonic minor'],
    IntervalList(Maj2, Maj3, Per4, Per5, Min6, Min7): ['maj melodic', 'M melodic', 'melodic major'],
    IntervalList(Maj2, Min3, Per4, Per5, Maj6, Maj7): ['m melodic', 'm melodic', 'jazz minor', 'melodic minor ascending', 'melodic minor'], # note: ascending only
    # "melodic minor" can refer to using the the natural minor scale when descending, but that is TBI
    }
scale_name_intervals = unpack_and_reverse_dict(interval_scale_names)
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
 'harmonic major': {1: ['harmonic major'], 2: ['blues', 'dorian ♭5', 'locrian ♯2♯6'], 3: ['phrygian ♭4', 'altered dominant ♯5'],
                    4: ['lydian ♭3', 'melodic minor ♯4'], 5: ['mixolydian ♭2'],
                    6: ['lydian augmented ♯2'], 7: ['locrian ♭♭7']}
                 }

################################################################################
### Scale, Subscale, and ScaleDegree classes

def mod_degree(deg, max_degree=7):
    """accepts an integer 'deg' and mods it onto 1-indexed range of ScaleDegrees,
    1-7 inclusive (or any other arbitrary maximum degree, e.g. for Subscales)"""
    if not isinstance(deg, int):
        raise ValueError(f'mod_degree only valid for int inputs, but got: {type(deg)}')
    else:
        min_degree = 1
        if not (min_degree <= deg <= max_degree):
            deg = ((deg - 1) % max_degree) + 1
        return deg

### TBI: should scales be able to be modified by ChordQualifiers or something similar, like ChordFactors can?
class Scale:
    """a hypothetical diatonic 7-note scale not built on any specific tonic,
    but defined by a series of intervals from whatever its tonic is"""
    def __init__(self, scale_name=None, intervals=None, mode=1, chromatic_intervals=None, stacked=True):
        self.intervals, self.base_scale, self.rotation = self._parse_input(scale_name, intervals, mode, stacked)

        # build degrees dict that maps ScaleDegrees to this scale's intervals:
        self.degree_intervals = {1: Unison}
        for d, i in enumerate(self.intervals):
            deg = d+2 # starting from 2
            self.degree_intervals[deg] = Interval(value=i.value, degree=deg)

        assert len(self.degree_intervals) == 7, f"{scale_name} is not diatonic: has {len(self.degree_intervals)} degrees instead of 7"
        assert len(self.intervals) == 6, f"{scale_name} has {len(self.intervals)} intervals instead of the required 6"

        # determine quality by asking: is the third major or minor
        self.quality = self[3].quality

        self.diatonic_intervals = IntervalList(self.intervals)
        # add chromatic intervals (blues notes etc.)
        if chromatic_intervals is not None:
            self.intervals = self._add_chromatic_intervals(chromatic_intervals)
            # these exist in the list of intervals, but no degree maps onto them
            self.chromatic_intervals = IntervalList(chromatic_intervals)
        else:
            self.chromatic_intervals = None

    @staticmethod
    def _parse_input(name, intervals, mode, stacked):
        # in case we've been obviously fed intervals as first arg, implicitly fix input:
        if isinstance(name, IntervalList):
            intervals = name
            name = None
        # and continue as normal

        # if neither name or interval has been given: initialise natural major scale
        if name is not None and intervals is not None:
            name = 'major'

        if name is not None:
            assert intervals is None, f'Received mutually exclusive name ({name}) and intervals ({intervals}) args to Scale init'
            # if first input (name) is an existing Scale object, just keep it:
            if isinstance(name, Scale):
                if mode != 1:
                    new_intervals = rotate_mode_intervals(name.intervals, mode)
                else:
                    new_intervals = IntervalList(name.intervals)

                return new_intervals, inp.base_scale, inp.rotation
            elif isinstance(name, str):
                if name in mode_lookup:
                    base_scale, rotation = mode_lookup[name]
                else:
                    raise ValueError(f'scale name {name} does not seem to correspond to a valid rotation of a base scale')

                if name in mode_name_intervals:
                    intervals = mode_name_intervals[name]
                else:
                    raise ValueError(f'scale name {name} does not seem to correspond to a valid set of intervals')

                # name = interval_mode_names[intervals][-1]

                if mode != 1:
                    intervals = rotate_mode_intervals(intervals, mode)
                    rotation += (mode-1)

                return intervals, base_scale, rotation

            else:
                raise TypeError(f'Invalid init to Scale, expected first arg (name) to be a string, or at least an existing Scale or IntervalList, but is: {type(name)}')

        # name is None; so we have been supplied an intervals arg instead:
        else:
            assert intervals is not None, f'Received neither name or intervals arg to Scale init; need one or the other!'

            if isinstance(intervals, (list, tuple)):
                # intervals = IntervalList(intervals)
                intervals = Scale.sanitise_intervals(intervals)
                if intervals in interval_mode_names:
                    name = interval_mode_names[intervals][-1]
                    base_scale, rotation = mode_lookup[name]

                    if mode != 1:
                        intervals = rotate_mode_intervals(intervals, mode)
                        rotation += (mode-1)

                    return intervals, base_scale, rotation
                else:
                    raise KeyError(f'No scale found that matches intervals: {intervals}')
            else:
                raise TypeError(f'Invalid input to Scale init: expected second arg (intervals) to be an iterable of Intervals, but got: {type(inp)}')

    @staticmethod
    def sanitise_intervals(intervals, stacked=True):
        """forces a list of (assumed) stacked Intervals into canonical form,
            with unisons neither at start nor end, and one interval for each degree.
        if stacked=False, accepts unstacked intervals (of form: M2, m1, M2, M2, etc.) and stacks them first."""
        if not stacked:
            intervals = IntervalList(intervals).strip().stack()
        elif stacked:
            intervals = IntervalList(intervals).flatten().strip()

        # sanitise interval list to have the exact desired degrees:
        desired_degrees = range(2,8)
        sanitised_intervals = IntervalList()
        for d, i in zip(desired_degrees, intervals):
            sanitised_intervals.append(Interval(i.value, degree=d))
        return sanitised_intervals

    def _add_chromatic_intervals(self, chromatic_intervals):
        assert isinstance(chromatic_intervals, (list, tuple)), f'chromatic_intervals must be an iterable of Interval objects'
        assert check_all(chromatic_intervals, 'isinstance', Interval), f'chromatic_intervals contains non-Interval object/s'
        new_intervals = [i for i in self.intervals]
        existing_interval_values = set([i.value for i in self.intervals])
        for ci in chromatic_intervals:
            assert ci.value not in existing_interval_values, f'Chromatic interval {ci} conflicts with existing interval in subscale: {self.intervals}'
            new_intervals.append(ci)
        return IntervalList(sorted(new_intervals))

    def __len__(self):
        # diatonic scale by definition has 7 intervals:
        assert len(self.degree_intervals) == 7
        return 7

    def __contains__(self, item):
        """if item is an Interval, does it fit in our list of degree-intervals plus chromatic-intervals?"""
        if isinstance(item, (Interval, int)):
            return Interval(item) in self.intervals
        #### I have realised this makes sense for Keys but not Scales - an AbstractChord being in a scale is dependent on its root
        # elif isinstance(item, (AbstractChord, ChordFactors, str)):
        #     # accept objects that cast to AbstractChords:
        #     if isinstance(item, str):
        #         item = AbstractChord(item)
        #     elif isinstance(item, ChordFactors):
        #         item = AbstractChord(factors=item)
        #     assert isinstance(item, AbstractChord)
        #     for i in item.intervals:
        #         if i not in self.intervals:
        #             return False
        #     return True
        else:
            raise TypeError(f'Scale.__contains__ not defined for items of type: {type(item)}')

    def __getitem__(self, idx):
        """returns the (flattened) Interval or Intervals from root to this scale degree"""
        if isinstance(idx, int):
            return self.degree_intervals[mod_degree(idx)]
        else:
            return IntervalList([self.degree_intervals[mod_degree(d)] for d in idx])

    def __call__(self, degree, order=3, qualifiers=None):
        """wrapper around self.chord - returns an AbstractChord built on desired degree"""
        return self.chord(degree=degree, order=order, qualifiers=qualifiers)

    def __eq__(self, other):
        if isinstance(other, Scale):
            return self.intervals == other.intervals
        else:
            raise TypeError(f'__eq__ not defined between Scale and {type(other)}')

    def __hash__(self):
        return hash((self.diatonic_intervals, self.intervals, self.chromatic_intervals))

    def __str__(self):
        return f'𝄢 {self.name} scale  {self.intervals.pad()}'

    def __repr__(self):
        return str(self)

    @property
    def name(self):
        if self.chromatic_intervals is None:
            if self.intervals in interval_mode_names:
                return interval_mode_names[self.diatonic_intervals][-1]
            else:
                return 'unknown'
        else:
            # TBI - identify special scales with chromatic intervals?
            raise Exception('Unimplemented')

    @property
    def short_name(self):
        # for use in Keys, so that Key('Cm') is listed as Cm, and not C natural minor
        remapping = {'natural major': '', 'natural minor': 'm'}
        name = self.name
        if name in remapping:
            return remapping[name]
        else:
            return name

    @property
    def aliases(self):
        """return a list of other names for this scale"""
        return mode_name_aliases[self.name]

    @property
    def pentatonic(self):
        """returns the pentatonic subscale of the natural major or minor scales.
        will function for other scales, though is not well-defined."""
        if self.quality.major: # and self.natural?
            pent_scale = self.subscale(degrees=[1,2,3,5,6])
        elif self.quality.minor: # and self.natural?
            pent_scale = self.subscale(degrees=[1,3,4,5,7])
        return pent_scale

    @property
    def blues(self):
        """returns the hexatonic blues subscale of the natural major or minor scales.
        will probably not function at all for other scales."""
        if self.quality.major: # and self.natural?
            hex_scale = self.subscale(degrees=[1,2,3,5,6], chromatic_intervals=[Min3])
        elif self.quality.minor: # and self.natural?
            hex_scale = self.subscale(degrees=[1,3,4,5,7], chromatic_intervals=[Dim5])
        return hex_scale

    def get_higher_interval(self, idx):
        """from root to this scale degree, which is NOT in the range 1-7,
        return the relevant extended interval without modding the degree.
        e.g. Scale('major').get_higher_interval[8] returns MajorNinth"""
        octave_span = (idx-1) // 7
        # deg_mod = mod_degree(idx)
        flat_interval = self[idx]
        ext_interval = Interval(flat_interval.value + (12*octave_span), degree=idx)
        return ext_interval

    def chord(self, degree, order=3, qualifiers=None):
        """returns an AbstractChord built on a desired degree of this scale,
        and of a desired order (where triads are order=3, tetrads are order=4, etc.).
        optionally accepts chord qualifiers in addition, to modify the chord afterward"""
        root_degree = degree
        # calculate chord degrees by successively applying thirds:
        desired_degrees = range(1, (2*order), 2)
        chord_degrees = [root_degree] + [root_degree+(o*2) for o in range(1, order)] # e.g. third and fifth degrees for order=3
        root_interval = self[root_degree]
        # note we use self.degree_intervals[d] instead of self[d] to avoid the mod behaviour:
        chord_intervals = [self.get_higher_interval(d) - root_interval for d in chord_degrees]

        # sanitise relative intervals to thirds, fifths etc. (instead of aug4ths and whatever)
        sanitised_intervals = []
        for i,d in zip(chord_intervals, desired_degrees):
            assert i.extended_degree == d

        return AbstractChord(intervals=chord_intervals, qualifiers=qualifiers)

    def triad(self, degree, qualifiers=None):
        """wrapper for self.chord() to create a tetrad (i.e. 7-chord)
        on the chosen degree of this scale"""
        return self.chord(degree, order=3, qualifiers=qualifiers)

    def tetrad(self, degree, qualifiers=None):
        """wrapper for self.chord() to create a tetrad (i.e. 7-chord)
        on the chosen degree of this scale"""
        return self.chord(degree, order=4, qualifiers=qualifiers)

    def subscale(self, degrees, chromatic_intervals=None):
        """returns a Subscale initialised from this Scale with the desired degrees"""
        return Subscale(parent_scale=self, degrees=degrees, chromatic_intervals=chromatic_intervals) # [self[s] for s in degrees]

    def neighbouring_scales(self):
        """return a list of Scale objects that differ from this one by only a semitone"""
        neighbours = {}
        for degree, intv in self.degree_intervals.items(): # try modifying each interval in this scale
            if degree != 1: # (but not the tonic)
                if not intv.quality.minor_ish: # don't flatten minor/dim degrees (they're already flat)
                    flat_deg_intervals = IntervalList(self.diatonic_intervals)
                    interval_to_modify = flat_deg_intervals[degree-2]
                    new_value = interval_to_modify.value -1
                    if (new_value not in flat_deg_intervals) and (new_value % 12 != 0):
                        new_interval = Interval(new_value, degree=degree)
                        flat_deg_intervals[degree-2] = new_interval

                        flat_deg_qualifier = ChordQualifier(modify={degree:-1})
                        try:
                            flat_deg_scale = Scale(intervals=flat_deg_intervals)
                            neighbours[flat_deg_qualifier] = flat_deg_scale
                        except KeyError as e:
                            log(f'Could not find neighbour of {self.name} with alteration {flat_deg_qualifier.name}: {e}')

                if not intv.quality.augmented: # and don't raise augmented degrees (they're already sharp)
                    sharp_deg_intervals = IntervalList(self.diatonic_intervals)
                    interval_to_modify = sharp_deg_intervals[degree-2]
                    new_value = interval_to_modify.value +1
                    if (new_value not in sharp_deg_intervals) and (new_value % 12 != 0): # don't raise intervals to a degree that's already in the scale
                        new_interval = Interval(new_value, degree=degree)
                        sharp_deg_intervals[degree-2] = new_interval
                        # sharp_deg_intervals[degree] = Interval(sharp_deg_intervals[degree-2]+1, degree)
                        sharp_deg_qualifier = ChordQualifier(modify={degree:+1})
                        try:
                            sharp_deg_scale = Scale(intervals=sharp_deg_intervals)
                            neighbours[sharp_deg_qualifier] = sharp_deg_scale
                        except KeyError as e:
                            log(f'Could not find neighbour of {self.name} with alteration {sharp_deg_qualifier.name}: {e}')
        return neighbours

    def valid_chords(self, degree, max_order=4, min_likelihood=0.4, min_consonance=0, max_results=None, sort_by='likelihood', inversions=False, display=True):
        """For a specified degree, returns all the chords that can be built on that degree
        that fit perfectly into this scale."""

        root_interval = self[degree]

        intervals_from_this_degree = IntervalList([self.get_higher_interval(d) - root_interval for d in range(degree+1, degree+15)])

        # built a dict of candidates as we go, keying AbstractChord objects to (likelihood, consonance) tuples
        candidates = {}
        for rarity, chord_names in chord_names_by_rarity.items():
            for name in [c for c in chord_names if '(no5)' not in c]: # ignore no5 chords

                # this will be a one-item dict if inversions are not allowd, or contain all possible inversions if they are
                candidate_intervals_by_inversion = {0: chord_names_to_intervals[name]}

                if inversions:
                    # invert this chord every which way and compare its intervals too
                    # first we need to know how big the main chord is:
                    chord_order = len(candidate_intervals_by_inversion[0])
                    # then loop through its possible bass degrees:
                    for i in range(1, chord_order):
                        inversion_intervals = AbstractChord(factors=chord_names_to_factors[name], inversion=i).intervals
                        candidate_intervals_by_inversion[i] = inversion_intervals

                for inversion, candidate_intervals in candidate_intervals_by_inversion.items():
                    is_match = True
                    for interval in candidate_intervals[1:]: # skip the root
                        if interval not in intervals_from_this_degree:
                            is_match = False
                            break
                    if is_match:
                        candidate = AbstractChord(factors=chord_names_to_factors[name], inversion=inversion)
                        if candidate.order <= max_order and candidate.likelihood >= min_likelihood and candidate.consonance >= min_consonance:
                            candidates[candidate] = {'order': candidate.order,
                                                     'likelihood': round(candidate.likelihood,2),
                                                     'consonance': round(candidate.consonance,3)}

        # sort result: (always by chord size first)
        if sort_by=='likelihood':
            sort_key = lambda c: (-candidates[c]['order'], candidates[c]['likelihood'], candidates[c]['consonance'])
        elif sort_by=='consonance':
            sort_key = lambda c: (-candidates[c]['order'], candidates[c]['consonance'], candidates[c]['likelihood'])
        else:
            raise ValueError(f"valid_chords sort_by arg must be one of: 'likelihood', 'consonance', not: {sort_by}")

        sorted_cands = sorted(candidates, key=sort_key, reverse=True)[:max_results]

        if display:
            longest_name_len = max([len(str(c.suffix)) for c in sorted_cands])+3
            longest_intvs_len = max([len(str(c.intervals)) for c in sorted_cands])+3
            orders_represented = sorted(list(set([c.order for c in sorted_cands])))

            print(f'Valid chords built on degree {degree} of {self}')
            order_names = {2: 'dyads', 3:'triads', 4:'tetrads', 5:'pentads', 6:'hexads', 7: 'heptads'}
            for o in orders_represented:
                if o in order_names:
                    print(f'  {order_names[o]}:')
                else:
                    print(f'  {o}-note chords')
                this_order_chords = [c for c in sorted_cands if c.order == o]
                for chord in this_order_chords:
                    suffix = chord.suffix if chord.suffix is not '' else 'maj'
                    sort_str = f"L:{chord.likelihood:.2f} C:{chord.consonance:.3f}" if sort_by=='likelihood' else f"C:{chord.consonance:.3f} L:{chord.likelihood:.2f}"
                    print(f'    ♫ {str(suffix):{longest_name_len}} {str(chord.intervals + root_interval):{longest_intvs_len}} {sort_str}')

        else:
            return sorted_cands




class Subscale(Scale):
    """a scale that contains a subset of the diatonic 7 intervals,
    such as a pentatonic or hexatonic scale.
    not all Scale methods are well-defined on Subscales, but some will work fine.

    can be initialised by a subscale name as first arg, e.g. 'major pentatonic' or 'blues minor',
    or otherwise by providing a parent_scale object and some desired degrees to pull from it.

    accepts an extra optional init argument, chromatic_degrees: None, or iterable.
    if not None, should contain a list of Intervals that don't belong to the base scale, like blues notes.
    chords using those notes are valid, though they are never chord roots"""

    def __init__(self, subscale_name=None, parent_scale=None, degrees=None, chromatic_intervals=None):
        if subscale_name is not None:
            # init by name; reject all other input args
            assert parent_scale is None and degrees is None and chromatic_intervals is None
            subscale_obj = subscales_by_name[subscale_name]
            parent_scale, degrees, chromatic_intervals = subscale_obj.parent_scale, subscale_obj.borrowed_degrees, subscale_obj.chromatic_intervals

        assert 1 in degrees, "Subscale sub-degrees must include the tonic"
        self.parent_scale = parent_scale
        self.borrowed_degrees = sorted(degrees)
        # ordered dict of this subscale's degrees with respect to parent, with gaps:
        self.degree_intervals = {d: parent_scale[d] for d in self.borrowed_degrees}
        self.intervals = IntervalList(list(self.degree_intervals.values()))
        # ordered dict of this subscale's degrees with no gaps:
        self.subdegree_intervals = {d+1: self.intervals[d] for d in range(len(self.intervals))}

        self.diatonic_intervals = self.intervals
        if chromatic_intervals is not None:
            self.intervals = self._add_chromatic_intervals(chromatic_intervals)
            self.chromatic_intervals = IntervalList(chromatic_intervals) # these exist in the list of intervals, but no degree maps onto them
        else:
            self.chromatic_intervals = None

        self.order = len(degrees)
        self.chromatic_order = len(self.intervals)

    def __str__(self):
        return f'𝄢 {self.name} (subscale)  {self.intervals.pad()}'

    @property
    def name(self):
        if self in subscales_to_aliases:
            aliases = subscales_to_aliases[self]
            proper_name = aliases[0]
            return proper_name
        else:
            return 'unknown'


    def possible_parents(self):
        """returns a list of Scales that are also valid parents for this Subscale"""
        ... #TBI
        #



################################################################################
### definition of modes, and hashmaps from scale/mode names to their intervals and vice versa

#
# scale_name_intervals = {}
# # dict mapping valid whole names of each possible key (for every tonic) to a tuple: (tonic, intervals)
#
# for intervals, names in interval_scale_names.items():
#     for scale_name_alias in names:
#         scale_name_intervals[scale_name_alias] = intervals



# keys arranged vaguely in order of rarity, for auto key detection/searching:
# common_suffixes = ['', 'm']
# uncommon_suffixes = ['m harmonic', 'm melodic']
# rare_suffixes = ['maj harmonic', 'maj melodic']
# very_rare_key_suffixes = [v[0] for v in list(interval_scale_names.values()) if v[0] not in (common_key_suffixes + uncommon_key_suffixes + rare_key_suffixes)]

def get_modes(scale_name):
    """for a given scale name, fetch the intervals of that scale
    and return the 7 rotations of that scale as its modes,
    in a dict mapping mode_degrees to lists of intervals from tonic"""
    this_mode_names = mode_idx_names[scale_name]
    this_mode_intervals_from_tonic = scale_name_intervals[scale_name]
    this_mode_degrees_to_intervals = {degree: rotate_mode_intervals(this_mode_intervals_from_tonic, degree) for degree in range(1,8)}
    return this_mode_degrees_to_intervals

def rotate_mode_intervals(scale_intervals_from_tonic, degree):
    """given a list of 6 intervals from tonic that describe a key/scale,
    e.g.: (maj2, maj3, per4, per5, maj6, maj7),
    and an integer degree between 1 and 7 (inclusive),
    return the mode of that scale corresponding to that degree"""
    assert len(scale_intervals_from_tonic) == 6, """list of intervals passed to rotate_mode_intervals must exclude tonics (degrees 1 and 8), and so should be exactly 6 intervals long"""
    if degree == 1:
        # rotation 1 is just the original intervals:
        return IntervalList(scale_intervals_from_tonic)
    elif degree in range(2,8):
        # relative_intervals = stacked_intervals(list(scale_intervals_from_tonic) + [P8])
        relative_intervals = scale_intervals_from_tonic.pad(left=False, right=True).unstack()
        # rotated_relative_intervals = rotate_list(relative_intervals, degree-1)
        rotated_relative_intervals = relative_intervals.rotate(degree-1)
        mode_intervals_from_tonic = rotated_relative_intervals.stack().strip()

        # ensure that intervals are one-per-degree:
        mode_intervals_from_tonic = IntervalList([Interval(i.value, d+2) for d, i in enumerate(mode_intervals_from_tonic)])

        return mode_intervals_from_tonic
    else:
        raise Exception(f'Invalid mode rotation of {degree}, must be in range 1-7 inclusive')


#### TBI: refactor this loop to use IntervalList's methods, .rotate() etc

# in this loop we build the mode_lookup dict that connects mode aliases to their corresponding identifiers as (base, degree) tuples
# and also construct the interval_mode_names dict that connects IntervalLists to corresponding mode names
mode_lookup = {}   # lookup of any possible name for a key/scale/mode, i.e. 'natural minor' or 'aeolian' or 'phrygian dominant', to tuples of (base_scale, degree)
interval_mode_names = {}  # lookup of IntervalLists to the names that scale is known by
non_scale_interval_mode_names = {} # a subset of interval_mode_names that does not include modes enharmonic to base scales
mode_name_aliases = {} # list mapping 'proper' mode names to lists of whole aliases, or empty lists if none exist

mode_bases = list(mode_idx_names.keys())  # same as base_scale_names
for base in mode_bases:
    intervals_from_tonic = scale_name_intervals[base]

    for degree, name_list in mode_idx_names[base].items():
        th = num_suffixes[degree]

        # proper_name = f'{base} scale, {degree}{th} mode'
        simple_name = f'{base} mode {degree}'
        preferred_name = name_list[0] if len(name_list) > 0 else simple_name
        full_name_list = [preferred_name, simple_name] + name_list[1:]
        # do some string augmentation to catch all the possible ways we might refer to a scale:
        full_name_list.extend([name.replace('♭', 'b') for name in name_list if '♭' in name])
        full_name_list.extend([name.replace('♯', '#') for name in name_list if '♯' in name])
        if degree == 1:
            full_name_list.append(base)


        # attach every possible name a mode could have, to a tuple of its base and degree:
        for full_name in full_name_list:
            mode_hashkey = (base, degree)
            mode_lookup[full_name] = mode_hashkey

        mode_intervals_from_tonic = rotate_mode_intervals(intervals_from_tonic, degree)
        log(f'mode *{degree}* of {base} key: {mode_intervals_from_tonic}')

        this_mode_names = mode_idx_names[base][degree]

        # aliases dict maps first name in list to other names in list (for use in Scale.aliases property)
        this_mode_aliases = list(this_mode_names)

        log(f'  also known as: {", ".join(this_mode_names)}')

        # workaround: we want the 'suffix' and 'scale_name' for modes to be the common mode name itself
        # so we append a copy of the first mode name to each list, so that it acts as first and last:
        this_mode_names.extend(this_mode_names[:1])

        if mode_intervals_from_tonic in interval_scale_names.keys():
            enharmonic_scale_name = interval_scale_names[mode_intervals_from_tonic][-1]
            this_mode_aliases.append(enharmonic_scale_name)
            log(f'--also enharmonic to:{enharmonic_scale_name} scale')
            # add non-mode scale names to mode_lookup too: e.g. mode_lookup['natural minor'] returns ('major', 6)
            for name in interval_scale_names[mode_intervals_from_tonic]:
                mode_lookup[name] = mode_hashkey
                # add standard scale names to the interval_scale_names lookup too:
                this_mode_names.append(name) # (this also means the last standard scale name becomes the standard lookup name)
        else: # record the modes that are not enharmonic to base scales in a separate dict
            non_scale_interval_mode_names[mode_intervals_from_tonic] = this_mode_names

        if mode_intervals_from_tonic in interval_mode_names:
            print(f'Key clash! we want to add {this_mode_names} as a key, but its intervals ({mode_intervals_from_tonic}) are already in interval_mode_names as: {interval_mode_names[mode_intervals_from_tonic]}')
            import pdb; pdb.set_trace()
        else:
            interval_mode_names[mode_intervals_from_tonic] = full_name_list + this_mode_names

        # attach one-to-many mappings for mode_name_aliases dict:
        for i in range(len(this_mode_aliases)):
            i_name = this_mode_aliases[i]
            other_names = [j_name for j,j_name in enumerate(this_mode_aliases) if (j != i) and (j_name != i_name)]
            mode_name_aliases[i_name] = other_names

    log('=========\n')

######################
# important output: reverse dict that maps all scale/mode names to their intervals:
mode_name_intervals = unpack_and_reverse_dict(interval_mode_names)
######################
# subscale definitions:
subscales_to_aliases = {Scale('major').subscale([1,2,3,5,6]): ['major pentatonic', 'pentatonic major', 'major pent', 'pent major', 'major5'],
                        Scale('minor').subscale([1,3,4,5,7]): ['minor pentatonic', 'pentatonic minor', 'minor pent', 'pent minor', 'minor5'],
                        Scale('major').subscale([1,2,3,5,6], chromatic_intervals=[Min3]): ['blues major', 'major blues', 'major blues hexatonic', 'blues major hexatonic'],
                        Scale('minor').subscale([1,3,4,5,7], chromatic_intervals=[Dim5]): ['blues minor', 'minor blues', 'minor blues hexatonic', 'blues minor hexatonic'],
                       }
subscales_by_name = unpack_and_reverse_dict(subscales_to_aliases)
######################

def unit_test():
    from chords import AbstractChord
    # test mode retrieval by name:
    test(mode_name_intervals['natural major'], get_modes('major')[1])

    print('Test scale init by intervals:')
    test(Scale('major'), Scale(intervals=scale_name_intervals['natural major']))

    print('Test chords built on Scale degrees:')
    test(Scale('minor').chord(2), AbstractChord('dim'))
    test(Scale('major').chord(5, order=5), AbstractChord('dom9'))

    print('Scales underlying the common 13th chords:')
    test(Scale('lydian').chord(1, order=7), AbstractChord('maj13'))
    test(Scale('mixolydian').chord(1, order=7), AbstractChord('13'))
    test(Scale('dorian').chord(1, order=7), AbstractChord('m13'))
    test(Scale('lydian b3').chord(1, order=7), AbstractChord('mmaj13'))

    print('Subscales:')
    test(Scale('major').pentatonic.intervals, [0, 2, 4, 7, 9])
    test(Scale('minor').blues.intervals, [0, 3, 5, 6, 7, 10])

    test(Subscale('blues minor')[4], P4)
    test(Subscale('blues minor').intervals[3], Dim5)

    # test neighbours:
    major_neighbours = Scale('natural major').neighbouring_scales()
    print(f'Neighbours of natural major scale:')
    for a, sc in major_neighbours.items():
        print(f'with {a.name}: {sc}')

    # extreme test case: do we crash if computing neighbours for every possible scale?
    for intvs, names in interval_mode_names.items():
        name = names[0]
        sc = Scale(name)
        neighbours = sc.neighbouring_scales()
        log(f'{name} scale has {len(neighbours)} neighbours')

    print('Valid chords from scale degrees:')
    Scale('major').valid_chords(4, inversions=True)

    Scale('harmonic minor').valid_chords(4, 6)

if __name__ == '__main__':
    unit_test()

    # which modes correspond to which 13 chords?

    _13chords = '13', 'maj13', 'min13', 'mmaj13', 'dim13'
    for chord_name in _13chords:
        c = AbstractChord(chord_name)
        chord_intervals = c.intervals
        s = Scale(intervals=chord_intervals)
        alias_str = f" (aka: {', '.join(s.aliases)})" if len(s.aliases) > 0 else ''

        # print(f'\n{c}')
        # print(f'  flattened intervals: {c.intervals.flatten()}')
        # print(f'    unstacked intervals: {s.intervals.unstack()}')
        # print(f'------associated scale: {s}{alias_str}')
