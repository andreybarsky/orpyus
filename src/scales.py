from .intervals import *
# from scales import interval_scale_names, key_name_intervals
from .util import rotate_list, reverse_dict, unpack_and_reverse_dict, check_all, log
from .chords import ChordFactors, AbstractChord, chord_names_by_rarity, chord_names_to_intervals, chord_names_to_factors
from .qualities import ChordModifier, Quality
from .parsing import num_suffixes, numerals_roman
from . import notes, _settings


# 'standard' scales are: natural/melodic/harmonic majors and minors.
standard_scale_names = {'natural major', 'natural minor', 'harmonic major', 'harmonic minor', 'melodic major', 'melodic minor'}
base_scale_names = {'natural major', 'melodic minor', 'harmonic minor', 'harmonic major'}
natural_scale_names = {'natural major', 'natural minor'}
# this dict maps scale intervals (in canonical, stripped form) to all accepted aliases
# at first just for the standard scales, but it gets filled out later
interval_scale_names = {
    IntervalList(M2, M3, P4, P5, M6, M7): ['', 'maj', 'M', 'major', 'natural major' ],
    IntervalList(M2, m3, P4, P5, m6, m7): ['m', 'min', 'minor', 'natural minor' ],

    IntervalList(M2, M3, P4, P5, m6, M7): ['harmonic major', 'M harmonic', 'major harmonic', 'maj harmonic', 'harmonic major'],
    IntervalList(M2, m3, P4, P5, m6, M7): ['harmonic minor', 'm harmonic', 'minor harmonic', 'min harmonic', 'harmonic minor'],
    IntervalList(M2, M3, P4, P5, m6, m7): ['melodic major', 'M melodic', 'major melodic', 'melodic major', 'maj melodic', 'melodic major'],
    IntervalList(M2, m3, P4, P5, M6, M7): ['melodic minor', 'm melodic', 'minor melodic', 'min melodic', 'jazz minor', 'melodic minor ascending','melodic minor'], # note: ascending only
    # "melodic minor" can refer to using the the natural minor scale when descending, but that is TBI
    }
scale_name_intervals = unpack_and_reverse_dict(interval_scale_names)
# standard_scale_suffixes = list([names[0] for names in interval_standard_scale_names.values()])


# this dict maps base scale names to dicts that map scale degrees to the modes of that base scale
mode_idx_names = {
  'natural major': {1: ['ionian'], 2: ['dorian'], 3: ['phrygian'], 4: ['lydian'],
                    5: ['mixolydian'], 6: ['aeolian'], 7: ['locrian']},
  'melodic minor': {1: ['athenian', 'melodic minor ascending', 'jazz minor'], 2: ['cappadocian', 'phrygian ♯6', 'dorian ♭2'],
                    3: ['asgardian', 'lydian augmented'], 4: ['pontikonisian', 'lydian dominant'],
                    5: ['olympian', 'aeolian dominant', 'mixolydian ♭6'],
                    6: ['sisyphean', 'aeolocrian', 'half-diminished'], 7: ['palamidian', 'altered dominant']},
 'harmonic minor': {1: ['harmonic minor'], 2: ['locrian ♯6'], 3: ['ionian ♯5'], 4: ['ukrainian dorian'],
                    5: ['phrygian dominant'], 6: ['lydian ♯2'], 7: ['altered diminished']},
 'harmonic major': {1: ['harmonic major'], 2: ['blues heptatonic', 'dorian ♭5', 'locrian ♯2♯6'], 3: ['phrygian ♭4', 'altered dominant ♯5'],
                    4: ['lydian minor', 'lydian ♭3', 'melodic minor ♯4'], 5: ['mixolydian ♭2'],
                    6: ['lydian augmented ♯2'], 7: ['locrian ♭♭7']}
                 }

################################################################################

class ScaleDegree(int):
    subscript_numerals = '₀₁₂₃₄₅₆₇₈₉'
    """class representing the degrees of a scale with associated mod-operations"""
    def __new__(cls, degree, num_degrees=7):
        extended_degree = degree
        if (degree > num_degrees) or (degree < 1):
            degree = ((degree -1 ) % num_degrees) + 1
        x = int.__new__(cls, degree)
        x.degree = degree
        x.num_degrees = num_degrees # i.e. scale size
        x.extended_degree = extended_degree
        return x

    # mathematical operations on scale degrees preserve extended degree and scale size:
    def __add__(self, other):
        assert not isinstance(other, Interval), "ScaleDegrees cannot be added to intervals"
        return ScaleDegree(self.extended_degree + int(other), num_degrees=self.num_degrees)
    def __sub__(self, other):
        assert not isinstance(other, Interval), "ScaleDegrees cannot be added to intervals"
        return ScaleDegree(self.extended_degree - int(other), num_degrees=self.num_degrees)

    def __str__(self):
        # integer combined with caret above:
        num_char = f'{int(self)}\u0311'
        if self.num_degrees != 7:
            # show that this is a degree of a non-heptatonic scale with a subscript marker:
            if self.num_degrees < 10:
                # single unicode integer
                addendum = self.subscript_numerals[self.num_degrees]
            else:
                # combine multiple unicode integers:
                addendum = ''.join([self.subscript_numerals[int(n)] for n in str(self.num_degrees)])
            return num_char + addendum
        else:
            return num_char

    def __repr__(self):
        return str(self)

    #
    # def __add__(self, other):
    #     return ScaleDegree(self + other)
    #
    # def __sub__(self, other):
    #     return ScaleDegree(self - other)


# ScaleFactors work exactly as ChordFactors, so this is just a wrapper:
class ScaleFactors(ChordFactors):
    pass

### Scale class that spans diatonic scales, subscales, blues scales, octatonic scales and all the rest:



### TBI: should scales be able to be modified by ChordModifiers or something similar, like ChordFactors can?

### TBI: Scales should accept arbitrary degree alterations as init, like 'lydian b3' or whatever
class Scale:
    """a hypothetical diatonic 7-note scale not built on any specific tonic,
    but defined by a series of Intervals from whatever its hypothetical tonic is"""
    def __init__(self, scale_name=None, intervals=None, mode=1, chromatic_intervals=None, stacked=True, alias=None):
        self.intervals, self.base_scale_name, self.rotation = self._parse_input(scale_name, intervals, mode, stacked)

        # build degrees dict that maps ScaleDegrees to this scale's intervals:
        self.degree_intervals = {1: Unison}
        for d, i in enumerate(self.intervals):
            deg = d+2 # starting from 2
            self.degree_intervals[deg] = Interval.from_cache(value=i.value, degree=deg)
        self.interval_degrees = reverse_dict(self.degree_intervals)

        # just the numbers from 1 to 7 for diatonic scales, but may be different for other scales:
        self.degrees = list(self.degree_intervals.keys())

        # base degrees and degrees are identical for Scale objects, but may differ for Subscales:
        self.base_degree_intervals = self.degree_intervals
        self.interval_base_degrees = self.interval_degrees
        # higher degrees are simply the numbers from 1 to 21 for Scales (3 octaves), but a subset of that for Subscales
        self.higher_degrees = list(range(1,22))

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
            self.diatonic = False
        else:
            # TBI - should this be emptylist instad?
            self.chromatic_intervals = None
            self.diatonic = True

        self.is_subscale = False
        self.assigned_name = alias
        # self.is_natural = (self.name in natural_scale_names)

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


                return new_intervals, name.base_scale_name, name.rotation
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
                if not isinstance(intervals, IntervalList):
                    # force to IntervalList if it is not one:
                    intervals = IntervalList(intervals)

                # early check to see if these intervals are registered to a known scale:
                # (and try sanitising them to canonical diatonic form if not)
                if intervals not in interval_mode_names:
                    intervals = Scale.sanitise_intervals(intervals, stacked='auto')
                # allocate name, base scale etc. if the (sanitised) intervals are registered:
                if intervals in interval_mode_names:
                    name = interval_mode_names[intervals][-1]
                    base_scale, rotation = mode_lookup[name]
                    if mode != 1:
                        intervals = intervals.rotate(mode-1)

                    return intervals, base_scale, rotation

                else:
                    # not a known diatonic scale, so we treat this as a special case
                    log(f'Unusual scale found with (sanitised) intervals: {intervals}')
                    # name = 'unknown'
                    # import pdb; pdb.set_trace()
                    return intervals, None, None

            else:
                raise TypeError(f'Invalid input to Scale init: expected second arg (intervals) to be an iterable of Intervals, but got: {type(inp)}')

    @staticmethod
    def sanitise_intervals(intervals, stacked='auto'):
        """forces a list of (assumed) stacked Intervals into canonical form,
            which is diatonic if the intervals appear to correspond to a diatonic scale,
            with unisons neither at start nor end, and one interval for each degree.
        if stacked==False, accepts unstacked intervals (of form: M2, m1, M2, M2, etc.) and stacks them first.
        if stacked=='auto', tries to detect if the intervals are stacked or not and treats them appropriately."""

        if stacked == 'auto':
            # if the highest interval is a dim5 or greater, assume these are stacked:
            stacked = (max(intervals) >= 6)

        if not stacked:
            intervals = IntervalList(intervals).strip().stack()
        elif stacked:
            # check for diatonicity:
            intervals = IntervalList(intervals).flatten().strip()

        full_padded_intervals = intervals.pad(left=True, right=True)
        seems_diatonic = (len(full_padded_intervals) == 8)
        log(f'checking for diatonicity of intervals: {seems_diatonic}')

        # sanitise interval list to have the exact desired degrees:
        if seems_diatonic:
            desired_degrees = range(2,8)
        else:
            # non diatonic scale can have more than 7 degrees
            desired_degrees = range(2,len(intervals)+2)

        sanitised_intervals = []
        for d, i in zip(desired_degrees, intervals):
            sanitised_intervals.append(Interval.from_cache(i.value, degree=d))
        return IntervalList(sanitised_intervals)

    def _add_chromatic_intervals(self, chromatic_intervals):
        # cast as intervallist if non-Interval objects provided or if solo Interval outside list:
        chromatic_intervals = IntervalList(chromatic_intervals)
        # assert isinstance(chromatic_intervals, (list, tuple)), f'chromatic_intervals must be an iterable of Interval objects'
        # assert check_all(chromatic_intervals, 'isinstance', Interval), f'chromatic_intervals contains non-Interval object/s'
        new_intervals = [i for i in self.intervals]
        existing_interval_values = set([i.value for i in self.intervals])
        for ci in chromatic_intervals:
            assert ci.value not in existing_interval_values, f'Chromatic interval {ci} conflicts with existing interval in subscale: {self.intervals}'
            new_intervals.append(ci)
        return IntervalList(sorted(new_intervals))

    def mod_degree(self, deg):
        """accepts an integer 'deg' and mods it onto 1-indexed range of ScaleDegrees,
        1-7 inclusive (or any other arbitrary maximum degree, e.g. for Subscales)"""
        max_degree = 7 # or len(self.degree_intervals)?
        if not isinstance(deg, int):
            raise ValueError(f'mod_degree only valid for int inputs, but got: {type(deg)}')
        else:
            min_degree = 1
            if not (min_degree <= deg <= max_degree):
                deg = ((deg - 1) % max_degree) + 1
            return deg

    def __len__(self):
        # diatonic scale by definition has 7 intervals, but chromatic scales like the bebop scale may have more
        return (len(self.intervals))

    def __contains__(self, item):
        """if item is an Interval, does it fit in our list of diatonic-degree-intervals plus chromatic-intervals?
        if it is an IntervalList, do they all fit?"""
        if isinstance(item, (Interval, int)):
            if item % 12 == 0:
                return True # by definition
            else:
                return (Interval.from_cache(item).flatten() in self.intervals)
        elif isinstance(item, (list, IntervalList)):
            if type(item) == list:
                item = IntervalList(item)
            # for an iterable of intervals from root, check if they all belong:
            padded_intervals = self.intervals.pad()
            for iv in item.flatten():
                if iv not in padded_intervals:
                    return False
            return True
        else:
            raise TypeError(f'Scale.__contains__ not defined for items of type: {type(item)}')

    def contains_degree_chord(self, degree, abs_chord, degree_interval=None):
        """checks whether a given AbstractChord on a given Degree of this Scale belongs in this Scale"""
        if isinstance(abs_chord, str):
            abs_chord = AbstractChord(abs_chord)
        # assert type(abs_chord) == AbstractChord, "Scales can only contain AbstractChords"
        assert 1 <= degree <= 7, "Scales can only contain chords built on degrees between 1 and 7"
        # if degree_interval is None:
        #     # we can optionally require the chord root to be on a specific interval as well as a specific degree
        #     degree_interval = self.degree_intervals[degree]
        if degree_interval is not None:
            if self.degree_intervals[degree] != degree_interval:
                return False
        intervals_from_root = IntervalList([self.degree_intervals[degree] + iv for iv in abs_chord.intervals])
        # call __contains__ on resulting iv list:
        return intervals_from_root in self

    def __getitem__(self, idx):
        """returns the (flattened) Interval or Intervals from root to this scale degree"""
        if isinstance(idx, int):
            return self.degree_intervals[self.mod_degree(idx)]
        else:
            return IntervalList([self.degree_intervals[self.mod_degree(d)] for d in idx])

    def __call__(self, degree, order=3, modifiers=None):
        """wrapper around self.chord - returns a chord object built on desired degree"""
        return self.chord(degree=degree, order=order, modifiers=modifiers)

    def __eq__(self, other):
        if isinstance(other, Scale):
            return self.intervals == other.intervals
        else:
            raise TypeError(f'__eq__ not defined between Scale and {type(other)}')

    def __hash__(self):
        return hash((self.diatonic_intervals, self.intervals, self.chromatic_intervals))


    @property
    def aliases(self):
        """return a list of other names for this scale"""
        return list(set(mode_name_aliases[self.name]))

    def rotate(self, rot):
        """Returns the mode of this scale with intervals rotated by specified order."""
        return Scale(intervals=self.intervals, mode=rot)

    # return all the modes of this scale, starting from wherever it is:
    @property
    def modes(self):
        return [self.rotate(m) for m in range(1,8)]

    @property
    def pentatonic(self):
        """returns the pentatonic subscale of the natural major or minor scales.
        will function for other scales, though is not well-defined."""
        # return pre-computed pentatonic scale from cache if it exists:
        if self in cached_pentatonics:
            return cached_pentatonics[self]
        else:
            if self.quality.major and self.is_natural:
                # return self.subscale(degrees=[1,2,3,5,6])
                pent = MajorPentatonic
            elif self.quality.minor and self.is_natural:
                # return self.subscale(degrees=[1,3,4,5,7])
                pent = MinorPentatonic
            else:
                # experimental: we've been asked for the pentatonic scale of a non-natural diatonic scale
                # so we try to find one that maximises pairwise interval consonance while preserving scale character
                ordered_pent_scales = self.compute_pentatonics(preserve_character=True)
                preferred = list(ordered_pent_scales.keys())[0]
                if preferred in subscales_to_aliases:
                    # use existing pre-defined subscale name (like 'blues scale') if one exists:
                    pent = preferred
                else:
                    # otherwise just call this a subscale of its parent scale:
                    pent = self.subscale(omit=preferred.omit, name=f'{self.name} pentatonic')
        if _settings.DYNAMIC_CACHING:
            cached_pentatonics[self] = pent
        return pent

    def compute_pentatonics(self, preserve_character=False, keep_quality=True):
        """Given this scale and its degree-intervals,
        find the size-5 subset of its degree-intervals that maximises pairwise consonance"""
        assert not self.is_subscale, "Cannot compute pentatonics of a subscale"
        candidates = []
        if preserve_character:
            character = self.character
            possible_degrees_to_exclude = [d for d, iv in self.degree_intervals.items() if ((d != 1) and (iv not in character))]
        else:
            possible_degrees_to_exclude = [d for d, iv in self.degree_intervals.items() if d != 1]

        for deg1 in possible_degrees_to_exclude:
            other_degrees_to_exclude = [d for d in possible_degrees_to_exclude if d not in {1, deg1}]
            for deg2 in other_degrees_to_exclude:
                remaining_degrees = [d for d in self.degree_intervals.keys() if d not in {deg1, deg2}]
                subscale_candidate = self.subscale(degrees=remaining_degrees)
                subscale_candidate.assigned_name = f'{self.name} omit({deg1},{deg2})'
                candidates.append(subscale_candidate)
        sorted_cands = sorted(candidates, key = lambda x: (x.consonance), reverse=True)
        return {x: round(x.consonance,3) for x in sorted_cands}


    def __sub__(self, other):
        # subtraction with another scale produces the intervalwise difference
        if isinstance(other, Scale):
            assert len(self) == len(other)
            return [iv.value for iv in (self.intervals - other.intervals)]
        else:
            raise TypeError(f'__sub__ not defined between Scale and: {type(other)}')

    @property
    def nearest_natural_scale(self):
        return self.find_nearest_natural_scale()

    # quality-of-life alias (because I keep getting them mixed up):
    @property
    def closest_natural_scale(self):
        return self.nearest_natural_scale

    def find_nearest_natural_scale(self):
        """return the natural scale that has the most intervallic overlap with this scale
        (defaulting to major in the rare event of a tie)"""

        diffs_from_major = self.intervals - scale_name_intervals['major']
        dist_from_major = sum([abs(iv.value) for iv in diffs_from_major])

        diffs_from_minor = self.intervals - scale_name_intervals['minor']
        dist_from_minor = sum([abs(iv.value) for iv in diffs_from_minor])

        if dist_from_major <= dist_from_minor:
            return MajorScale
        elif dist_from_minor < dist_from_major:
            return MinorScale

    @property
    def parallel(self):
        """returns the parallel minor or major or a natural major or minor scale,
        or of harmonic/melodic minor or major scales"""
        if self in parallel_scales:
            return parallel_scales[self]
        else:
            raise Exception(f'No parallel scale defined for {self}')

    @property
    def character(self, verbose=False):
        """if this is a mode, returns the intervals of this mode that are different to its nearest natural scale.
        if it is a natural scale, return the intervals that make it distinct from its parallel scale."""
        if not self.is_natural:
            nearest_natural = self.nearest_natural_scale
        else:
            nearest_natural = self.parallel

        base_intervals = nearest_natural.intervals
        scale_character = []
        for iv_self, iv_base in zip(self.intervals, base_intervals):
            if iv_self != iv_base:
                scale_character.append(iv_self)
        if verbose:
            print(f'Character of {self.name} scale: (with respect to {nearest_natural.name})')
        return IntervalList(scale_character)

    @property
    def is_natural(self):
        # True for natural major and minor scales, False for everything else
        if (self.intervals == MajorScale.intervals) or (self.intervals == MinorScale.intervals):
            return True
        else:
            return False

    @property
    def blues(self):
        """returns the hexatonic blues subscale of the natural major or minor scales.
        will probably not function at all for other scales."""
        if self.quality.major and self.is_natural:
            hex_scale = self.subscale(degrees=[1,2,3,5,6], chromatic_intervals=[m3])
        elif self.quality.minor and self.is_natural:
            hex_scale = self.subscale(degrees=[1,3,4,5,7], chromatic_intervals=[Dim5])
        else:
            raise Exception(f'No blues subscale defined for {self}')
        return hex_scale

    def get_higher_interval(self, idx):
        """from root to this scale degree, which is NOT in the range 1-7,
        return the relevant extended interval without modding the degree.
        e.g. Scale('major').get_higher_interval(9) returns MajorNinth"""
        octave_span = (idx-1) // 7 # or ?(len(self.degree_intervals))
        # deg_mod = mod_degree(idx)
        flat_interval = self[idx]
        if not self.is_subscale:
            interval_deg = idx
        else: # subscale degrees are not associated with the degrees of their intervals
            interval_deg = None
        ext_interval = Interval.from_cache(flat_interval.value + (12*octave_span), degree=interval_deg)
        return ext_interval

    def chord(self, degree, order=3, chromatic=False):
        """returns an AbstractChord built on a desired degree of this Scale,
        and of a desired order (where triads are order=3, tetrads are order=4, etc.).
        optionally accepts chord modifiers in addition, to modify the chord afterward.
        if chromatic=True, the chord is built over scale intervals rather than scale degrees,
        which affects chord construction in scales with chromatic tones like the blues or bebop scales."""
        root_degree = degree
        # calculate chord degrees by successively applying thirds:
        if not chromatic:
            desired_degrees = range(1, (2*order), 2)
            chord_degrees = [root_degree] + [root_degree+(o*2) for o in range(1, order)] # e.g. third and fifth degrees for order=3
            root_interval = self[root_degree]
            # note we use self.get_higher_interval(d) instead of self[d] to avoid the mod behaviour:
            chord_intervals = [self.get_higher_interval(d) - root_interval for d in chord_degrees]

            chord_interval_offsets = [i.offset_from_degree(d) for i,d in zip(chord_intervals, desired_degrees)]
            chord_factors = ChordFactors({d: o for d,o in zip(desired_degrees, chord_interval_offsets)})

        else:
            # root_interval_place  ### TBI: fix this
            pass

        return AbstractChord(factors=chord_factors)

    def on_tonic(self, tonic):
        """returns a Key object corresponding to this Scale built on a specified tonic"""
        if isinstance(tonic, str):
            tonic = notes.Note.from_cache(tonic)
        # lazy import to avoid circular dependencies:
        from .keys import Key
        return Key(intervals=self.diatonic_intervals, tonic=tonic, chromatic_intervals=self.chromatic_intervals, alias=self.assigned_name)

    def chords(self, order=3, chromatic_roots=False):
        """returns the list of chords built on every degree of this Scale."""
        chord_dict = {}
        if not chromatic_roots:
            for d, iv in self.degree_intervals.items():
                chord_dict[d] = self.chord(d, order=order)
        else:
            for iv in self.intervals:
                chord_dict[iv] = self.chord(interval=iv, order=order)
        return chord_dict

    def triad(self, degree):
        """wrapper for self.chord() to create a tetrad (i.e. 7-chord)
        on the chosen degree of this scale"""
        return self.chord(degree, order=3)

    def tetrad(self, degree):
        """wrapper for self.chord() to create a tetrad (i.e. 7-chord)
        on the chosen degree of this scale"""
        return self.chord(degree, order=4)

    def subscale(self, degrees=None, omit=None, chromatic_intervals=None, name=None):
        """returns a Subscale initialised from this Scale with the desired degrees"""
        return Subscale(parent_scale=self, degrees=degrees, omit=omit, chromatic_intervals=chromatic_intervals, assigned_name=name) # [self[s] for s in degrees]

    def get_neighbouring_scales(self):
        """return a list of Scale objects that differ from this one by only a semitone"""
        assert not self.is_subscale, "Cannot get neighbouring scales of a Subscale"
        neighbours = {}
        for degree, intv in self.degree_intervals.items(): # try modifying each interval in this scale
            if degree != 1: # (but not the tonic)
                if not intv.quality.minor_ish: # don't flatten minor/dim degrees (they're already flat)
                    flat_deg_intervals = IntervalList(self.diatonic_intervals)
                    interval_to_modify = flat_deg_intervals[degree-2]
                    new_value = interval_to_modify.value -1
                    if (new_value not in flat_deg_intervals) and (new_value % 12 != 0):
                        new_interval = Interval.from_cache(new_value, degree=degree)
                        flat_deg_intervals[degree-2] = new_interval

                        flat_deg_modifier = ChordModifier(modify={degree:-1})
                        try:
                            flat_deg_scale = Scale(intervals=flat_deg_intervals)
                            neighbours[flat_deg_modifier] = flat_deg_scale
                        except KeyError as e:
                            log(f'Could not find neighbour of {self.name} with alteration {flat_deg_modifier.name}: {e}')

                if not intv.quality.augmented: # and don't raise augmented degrees (they're already sharp)
                    sharp_deg_intervals = IntervalList(self.diatonic_intervals)
                    interval_to_modify = sharp_deg_intervals[degree-2]
                    new_value = interval_to_modify.value +1
                    if (new_value not in sharp_deg_intervals) and (new_value % 12 != 0): # don't raise intervals to a degree that's already in the scale
                        new_interval = Interval.from_cache(new_value, degree=degree)
                        sharp_deg_intervals[degree-2] = new_interval
                        # sharp_deg_intervals[degree] = Interval(sharp_deg_intervals[degree-2]+1, degree)
                        sharp_deg_modifier = ChordModifier(modify={degree:+1})
                        try:
                            sharp_deg_scale = Scale(intervals=sharp_deg_intervals)
                            neighbours[sharp_deg_modifier] = sharp_deg_scale
                        except KeyError as e:
                            log(f'Could not find neighbour of {self.name} with alteration {sharp_deg_modifier.name}: {e}')
        return neighbours
    @property
    def neighbouring_scales(self):
        return self.get_neighbouring_scales()


    def valid_chords(self, degree, order=None, min_order=2, max_order=4, min_likelihood=0.4, min_consonance=0, max_results=None, sort_by='likelihood', inversions=False, display=True, _root_note=None, no5s=False):
        """For a specified degree, returns all the chords that can be built on that degree
        that fit perfectly into this scale."""

        root_interval = self[degree]
        degrees_above_this_degree = [d for d in self.higher_degrees if d > degree]
        intervals_from_this_degree = IntervalList([self.get_higher_interval(d) - root_interval for d in degrees_above_this_degree])

        if self.chromatic_intervals is not None:
            # add chromatic intervals to the intervallist
            intervals_from_this_degree = IntervalList(list(intervals_from_this_degree) + list(self.chromatic_intervals))

        if order is not None:
            # overwrite min and max order:
            min_order = max_order = order

        # built a list of matching candidates as we go:
        shortlist = []
        for rarity, chord_names in chord_names_by_rarity.items():
            # for name in [c for c in chord_names if '(no5)' not in c]: # ignore no5 chords (no longer needed, no5s are not in that list:)
            for name in chord_names:

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
                        if _root_note is not None: # for easy inheritance by Key class
                            candidate = candidate.on_bass(_root_note)
                        shortlist.append(candidate)

                        if no5s:
                            # also add the no5 version of this chord if it is at least a tetrad (but not for inversions)
                            if (inversion == 0) and (candidate.order >= 4) and (5 in candidate):
                                no5_candidate = AbstractChord(candidate.suffix + '(no5)')
                                shortlist.append(no5_candidate)

        # apply statistical minimums and maximums to our shortlist to decide what to keep:
        candidate_stats = {}
        # (and initialise sets containing 'normal' chord intervals for pruning):
        if inversions:
            non_inverted_intervals = set()
        if no5s:
            non_no5_intervals = set()

        for candidate in shortlist:
            if candidate.order <= max_order and candidate.order >= min_order:
                if candidate.likelihood >= min_likelihood and candidate.consonance >= min_consonance:
                    candidate_stats[candidate] = {'order': candidate.order,
                                                  'likelihood': round(candidate.likelihood,2),
                                                  'consonance': round(candidate.consonance,3)}
                    # add normal chords' intervals to the pruning comparison sets:
                    if inversions and (candidate.inversion == 0):
                        non_inverted_intervals.add(candidate_intervals)
                    if no5s and (5 in candidate):
                        non_no5_intervals.add(candidate.intervals)

        # if inversions were allowed, we prune the candidate list to remove inversions that have the same intervals as a non-inverted candidate:
        # TBI: we could prune repeated inversions having the same intervals too, by pruning for each inversion-place starting from the highest?
        # (idea: we could keep a dict that maps intervals to chords matching those intervals, and take the least rare from each)
        if inversions:
            # non_inverted_intervals = {c.intervals for c in candidate_stats if c.inversion == 0}
            pruned_candidates = {c:v for c,v in candidate_stats.items() if (c.inversion == 0) or (c.intervals not in non_inverted_intervals)}
            candidate_stats = pruned_candidates
        if no5s: # prune no5s as well:
            # non_no5_intervals = {c.intervals for c in candidate_stats if '(no5)' not in c.suffix}
            pruned_candidates = {c:v for c,v in candidate_stats.items() if (5 in c) or (c.intervals not in non_no5_intervals)}
            candidate_stats = pruned_candidates

        # sort result: (always by chord size first)
        if sort_by=='likelihood':
            sort_key = lambda c: (-candidate_stats[c]['order'], candidate_stats[c]['likelihood'], candidate_stats[c]['consonance'])
        elif sort_by=='consonance':
            sort_key = lambda c: (-candidate_stats[c]['order'], candidate_stats[c]['consonance'], candidate_stats[c]['likelihood'])
        else:
            raise ValueError(f"valid_chords sort_by arg must be one of: 'likelihood', 'consonance', not: {sort_by}")

        sorted_cands = sorted(candidate_stats, key=sort_key, reverse=True)[:max_results]

        if display:
            longest_result_len = max([len(str(c)) for c in sorted_cands])+3
            # longest_intvs_len = max([len(str(c.intervals)) for c in sorted_cands])+3
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
                    # suffix = chord.suffix if chord.suffix != '' else 'maj'
                    sort_str = f"L:{chord.likelihood:.2f} C:{chord.consonance:.3f}" if sort_by=='likelihood' else f"C:{chord.consonance:.3f} L:{chord.likelihood:.2f}"
                    print(f'    {str(chord):{longest_result_len}} {sort_str}')

        else:
            return sorted_cands


    def intervals_from_degree(self, deg):
        """for a given degree in this scale, return all the ascending intervals
        from this degree (up to an octave higher) that belong in this scale"""
        lower_intervals = []
        assert deg in self.degree_intervals
        deg_interval = self.degree_intervals[deg]
        # upward to octave:
        degrees_in_octave = [d for d in self.higher_degrees if deg < d < 8]
        for d in degrees_in_octave:
            lower_intervals.append(self.degree_intervals[d])
        # for iv in range(deg-1, len(self.diatonic_intervals)):
        #     lower_intervals.append(self.diatonic_intervals[iv])
        # and chromatic intervals:
        if self.chromatic_intervals is not None:
            for iv in self.chromatic_intervals:
                if iv > deg_interval:
                    lower_intervals.append(iv)

        # exceeding the octave:
        higher_intervals = []
        if deg > 1:
            degrees_in_octave_above = [d for d in self.higher_degrees if 8 <= d < deg+14]
            # num_degrees_in_scale = len(self.degree_intervals)
            # for d in range(1, deg):
            for d in degrees_in_octave_above:
                higher_iv = self.get_higher_interval(d) # num_degrees_in_scale + d)
                higher_intervals.append(higher_iv)

            if self.chromatic_intervals is not None:
                for iv in self.chromatic_intervals:
                    if iv < deg_interval:
                        # raise the chromatic interval by an octave:
                        higher_intervals.append((iv+12))
        all_intervals = IntervalList(sorted(lower_intervals + higher_intervals))
        return all_intervals

    # we define consonance for scales a little different to how we do for chords
    # instead of looking at every pairwise interval, we look at every second-and-third interval
    # for each degree in the scale. i.e. the intervals 1-2, 1-3, 2-3, 2-4, etc.


    def get_pairwise_intervals(self, extra_tonic=False):
        pairwise = {}

        # outer loop is across degree intervals:
        for deg, left_iv in self.base_degree_intervals.items(): # range(1, len(self.degree_intervals)+1):  # (is this equivalent to mode rotation?)
            # left = self[deg]
            # inner loop is across all intervals from that degree, including chromatics:
            ivs = self.intervals_from_degree(deg)
            for right_iv in ivs:
                pairwise[(left_iv, right_iv)] = right_iv - left_iv
                if extra_tonic and (deg == 1):
                    pairwise[('tonic', right_iv)] = right_iv - left_iv # extra value for tonic, to upweight in weighted sum
        return pairwise
    @property
    def pairwise_intervals(self):
        return self.get_pairwise_intervals(extra_tonic=False)


    def get_pairwise_consonances(self, extra_tonic=False):
        # simply lifted from AbstractChord class:
        return AbstractChord.get_pairwise_consonances(self, extra_tonic=extra_tonic)
        # (this internally calls self.pairwise_intervals, which is defined above)
    @property
    def pairwise_consonances(self):
        return self.get_pairwise_consonances(extra_tonic=True)

    @property
    def consonance(self):
        """simply the mean of pairwise interval consonances"""
        if self in cached_consonances:
            return cached_consonances[self]
        else:
            cons_list = list(self.get_pairwise_consonances(extra_tonic=True).values())
            raw_cons = sum(cons_list) / len(cons_list)
            # return raw_cons
            # the raw consonance comes out as maximum=0.7231 for the most consonant scale (natural major)
            # and 0.6731 for the most dissonant scale, the half-diminished scale (mode 6 of melodic minor)
            # so we set the former to be just below 1 and the latter to be just above 0,
            # and rescale the entire raw consonance range within those bounds:
            max_cons = 0.76 # 0.7231 0.6584752093299405
            min_cons = 0.62 # 0.6731 0.6347743068389496

            rescaled_cons = (raw_cons - min_cons) / (max_cons - min_cons)
            if _settings.DYNAMIC_CACHING:
                cached_consonances[self] = rescaled_cons
            return rescaled_cons

    @property
    def rarity(self):
        scale_name = interval_mode_names[self.intervals][-1]

        if scale_name in natural_scale_names:
            # natural major and minor scales are most common:
            return 1
        elif scale_name in base_scale_names:
            # followed by harmonic/melodic minor, and harmonic major:
            return 2
        else:
            base, mode = mode_lookup[scale_name]
            if base == 'natural major':
                # modes of the major scale are the next most common:
                return 3
            else:
                # weird modes
                return 4

    @property
    def likelihood(self):
        # inverse of rarity
        return 1.1 - (0.2*(self.rarity))

    def roman_numeral(self, degree):
        """returns the roman numeral associated with the Chord on the desired degree of this scale"""
        chord = self.chord(degree)
        roman = numerals_roman[degree] # uppercase by default
        if chord.quality.major:
            pass # remain uppercase
            suffix = chord.suffix
        elif chord.quality.minor:
            roman = roman.lower()
            # exclude the 'm' suffix from minor chords - their minor-ness is indicated by the numeral case
            suffix = chord.suffix if chord.suffix != 'm' else ''
        else:
            # use upside down numerals instead of upper or lower case: ?
            # replacements = {'I': 'ı', 'V': 'ʌ'}
            # roman = ''.join(util.reduce_aliases(roman, replacements))
            # rare case of neither-major-nor-minor chord; maybe fall back on default assumptions of scale instead of this?
            roman = roman.lower() if ((scale.chord(1).quality.minor and degree in {1,4,5}) or (scale.chord(1).quality.major and degree in {2,3,6,7})) else roman
            suffix = chord.suffix
        return f'{roman}{suffix}'

    def play(self, on='G3', up=True, down=False, **kwargs):
        ## if duration is not set, use a smaller default duration than that for chords:
        if 'duration' not in kwargs:
            kwargs['duration'] = 0.5
        # Scales don't have tonics, but we can just pick one arbitrarily:
        starting_note = notes.OctaveNote(on)
        assert up or down, "Scale must be played up or down or both, but not neither"
        notes_up = notes.NoteList([starting_note + iv for iv in self.intervals.pad(left=True, right=True)], strip_octave=False)
        full_notes = notes_up if up else NoteList([])
        if down:
            notes_down = full_notes[-2::-1]
            full_notes.extend(notes_down)
        full_notes.play(**kwargs)

    def show(self, tuning='EADGBE'):
        """just a wrapper around the Guitar.show method, which is generic to most musical classes,
        so this method is also inherited by all Scale subclasses"""
        from .guitar import Guitar
        Guitar(tuning).show(self)
    @property
    def fretboard(self):
        # just a quick accessor for guitar.show in standard tuning
        return self.show()

    @property
    def suffix(self):
        return self.get_suffix()
    def get_suffix(self):
        """suffix of a Scale is the first entry in interval_scale_names for its intervals,
        or simply self.name if it does not exist in interval_scale_names (being a mode)"""
        # for use in Keys, so that Key('Cm') is listed as Cm, and not C natural minor
        if self.intervals in interval_scale_names:
            return interval_scale_names[self.intervals][0] # first item in interval_scale_names is the short suffix form
        elif self.intervals in interval_mode_names:
            return interval_mode_names[self.intervals][-1]
        elif self.diatonic_intervals in interval_scale_names:
            # call this an chromatic form of a diatonic scale
            return interval_scale_names[self.diatonic_intervals][0] + ' [chromatic]'
        elif self.diatonic_intervals in interval_mode_names:
            return interval_mode_names[self.diatonic_intervals][-1] + ' [chromatic]'
        else:
            return '(?)'

    @property
    def name(self):
        return self.get_name()
    def get_name(self):
        """name of a Scale is the last entry in interval_mode_names for its intervals"""
        if self.intervals in interval_mode_names:
            return interval_mode_names[self.intervals][-1]
        elif self.assigned_name is not None:
            # fall back on alias if one was provided
            return self.assigned_name
        elif self.diatonic_intervals in interval_mode_names:
            # otherwise call this a chromatic version of its diatonic parent:
            return interval_mode_names[self.diatonic_intervals][-1] + ' [chromatic]'
        else:
            return 'unknown'

    def __str__(self):
        lb, rb = self.intervals._brackets
        if self.chromatic_intervals is None:
            iv_names = [iv.short_name for iv in self.intervals]
        else:
            # show diatonic intervals as in normal interval list, and chromatic intervals in square brackets
            iv_names = [f'[{iv.short_name}]' if iv in self.chromatic_intervals  else iv.short_name  for iv in self.intervals]
        iv_str = f'{lb}{", ".join(iv_names)}{rb}'
        return f'{self._marker}{self.name}  {iv_str}'

    def __repr__(self):
        return str(self)

    # Scale object unicode identifier:
    _marker = _settings.MARKERS['Scale']


### TBI: should Subscale and DiatonicScale be subclasses of a GenericScale class?
class Subscale(Scale):
    """a scale that contains a subset of the diatonic 7 intervals,
    such as a pentatonic or hexatonic scale.
    not all Scale methods are well-defined on Subscales, but some will work fine.

    can be initialised by a subscale name as first arg, e.g. 'major pentatonic' or 'blues minor',
    or otherwise by providing a parent_scale object and some desired degrees to pull from it.

    accepts an extra optional init argument, chromatic_degrees: None, or iterable.
    if not None, should contain a list of Intervals that don't belong to the base scale, like blues notes.
    chords using those notes are valid, though they are never chord roots"""

    def __init__(self, subscale_name=None, parent_scale=None, degrees=None, omit=None, intervals=None, chromatic_intervals=None, assigned_name=None):

        if subscale_name is not None:
            assert assigned_name is None
            # init by subscale name; reject all other input args
            assert parent_scale is None and degrees is None and chromatic_intervals is None
            subscale_obj = subscales_by_name[subscale_name] # access the pre-initialised subscale with this name and re-initialise it
            parent_scale, degrees, chromatic_intervals = subscale_obj.parent_scale, subscale_obj.borrowed_degrees, subscale_obj.chromatic_intervals
            self.assigned_name = subscale_name
        elif intervals is not None:
            # init by interval kwarg alone
            self.intervals = IntervalList(intervals).strip()
            parent_scale = self.most_likely_parent
            chromatic_intervals = parent_scale.chromatic_intervals
            degrees = [parent_scale.interval_degrees[iv] for iv in intervals.pad(left=True, right=False)]
            self.assigned_name = assigned_name
        elif parent_scale is not None:
            assert (degrees is not None) or (omit is not None), f"Subscale initialised by parent scale must have a 'degrees' or 'omit' arg"
            self.assigned_name = assigned_name
        else:
            raise Exception(f'Subscale init must have either a subscale name, a set of intervals, or a combination of parent scale and degrees/omit')


        # if we're initialised from a parent scale, we require either its degrees or their ommission:
        if parent_scale is not None:
            if degrees is None:
                assert omit is not None
                degrees = [d for d in range(1,8) if d not in omit]
                self.omit = sorted(omit)
            else:
                assert omit is None
                self.omit = [d for d in range(1,8) if d not in degrees]

        assert 1 in degrees, "Subscale sub-degrees must include the tonic"
        self.parent_scale = parent_scale
        self.borrowed_degrees = sorted(degrees)
        # the higher-octave degrees defined for this subscale: (for chord generation)
        self.higher_degrees = self.borrowed_degrees + [d+7 for d in self.borrowed_degrees] + [d+14 for d in self.borrowed_degrees]

        # base degrees and degrees are the same for Scale objects,
        # but may differ for Subscales depending on which degrees are borrowed:
        self.base_degree_intervals = {d: parent_scale[d] for d in self.borrowed_degrees}
        self.interval_base_degrees = reverse_dict(self.base_degree_intervals)

        ### TBI: figure out consistency between scale/subscale degrees (should 'degrees' always be continuous, or always have a 5th, etc.)

        # as in Scale.init
        # ordered dict of this subscale's degrees with respect to parent, with gaps:
        self.intervals = IntervalList(list(self.base_degree_intervals.values())).strip()

        # ordered dict of this subscale's degrees with no gaps:
        self.sub_degree_intervals = {1: Unison}
        self.sub_degree_intervals.update({d+2: self.intervals[d] for d in range(len(self.intervals))})

        self.degree_intervals = self.base_degree_intervals # this equivalence is intended for compatibility with Scale methods but may cause problems

        self.degrees = list(self.degree_intervals.keys())

        self.diatonic_intervals = self.intervals
        if chromatic_intervals is not None: # chromatic intervals are intervals without a degree
            self.intervals = self._add_chromatic_intervals(chromatic_intervals)
            self.chromatic_intervals = IntervalList(chromatic_intervals) # these exist in the list of intervals, but no degree maps onto them
        else:
            self.chromatic_intervals = None

        # subscales can have indeterminate quality if they lack a major/minor third:
        if 3 in self.borrowed_degrees:
            self.quality = self.base_degree_intervals[3].quality
        else:
            self.quality = Quality('ind')


        self.is_subscale = True

    # def __str__(self):
    #     # return f'{self._marker} {self.name}  {self.intervals.pad()}'
    #     return f'{self._marker} {self.name}'

    def __len__(self):
        return len(self.intervals) + 1

    def contains_degree_chord(self, degree, abs_chord, degree_interval=None):
        """checks whether a given AbstractChord on a given Degree of this Scale belongs in this Subscale"""
        if isinstance(abs_chord, str):
            abs_chord = AbstractChord(abs_chord)
        # assert type(abs_chord) == AbstractChord, "Scales can only contain AbstractChords"
        assert 1 <= degree <= 7, "Scales can only contain chords built on degrees between 1 and 7"
        if degree not in self.self.borrowed_degrees:
            return False # this subscale does not even have that degree
        if degree_interval is not None:
            if self.degree_intervals[degree] != degree_interval:
                return False # this subscale does not have that interval
        intervals_from_root = IntervalList([self.base_degree_intervals[degree] + iv for iv in abs_chord.intervals])
        # call __contains__ on resulting iv list:
        return intervals_from_root in self

    def __getitem__(self, idx):
        """returns the (flattened) Interval or Intervals from root to this scale degree"""
        if isinstance(idx, int):
            return self.base_degree_intervals[self.mod_degree(idx)]
        else:
            return IntervalList([self.base_degree_intervals[self.mod_degree(d)] for d in idx])

    @property
    def _marker(self):
        "unicode marker for Subscale class"
        return '𝄳'

    @property
    def name(self):
        ### overwrites Scale.name
        return self.get_name()

    def get_name(self):
        """name of a Subscale is the first entry in interval_subscale_names for its intervals"""
        if self.intervals in interval_subscale_names:
            aliases = interval_subscale_names[self.intervals]
            proper_name = aliases[0]
            return proper_name
        elif self.assigned_name is not None:
            # if we can't find a name in interval_subscale_names, use whatever was given at init:
            return self.assigned_name
        else:
            return 'unknown'

    @property
    def suffix(self):
        """suffix of a Subscale is just the same as its name"""
        # overwrites Scale.suffix
        return self.get_name()


    # def get_higher_interval(self, idx):
    #     """from root to this scale degree, which is NOT in the range 1-7,
    #     return the relevant extended interval without modding the degree.
    #     e.g. Scale('major').get_higher_interval(9) returns MajorNinth"""
    #     octave_span = (idx-1) // 7
    #     # deg_mod = mod_degree(idx)
    #     flat_interval = self[idx]
    #     ext_interval = Interval(flat_interval.value + (12*octave_span), degree=idx)
    #     return ext_interval

    def chord(self, degree, order=3, sub_degree=False):
        """returns an AbstractChord built on a desired degree of this Subscale,
        and of a desired order (where triads are order=3, tetrads are order=4, etc.).
        for Subscales this is poorly defined, since triad degrees cannot be guaranteed,
        so instead we try and make the most consonant chord we can from the degrees available.

        if sub_degree=True, we construct chords by the "skip-one-play-one" principle,
        which means that, for example, the second chord of Am pentatonic becomes Am/C, instead of Cm"""


        if sub_degree:
            # use the sub-degrees of this subscale, instead of the base degrees
            # i.e. play-one-skip-one style triad chords
            log(f'Building chord in subscale: {self.name} off of sub-degree: {degree}')
            assert degree in self.sub_degree_intervals
            # to allow usage of chromatic notes, we find the place of the chord root in our interval attribute:
            root_interval_place = [i for (i,(d,iv)) in enumerate(self.sub_degree_intervals.items()) if d == degree][0]
            padded_intervals = self.intervals.pad(left=True, right=False)
            padded_compound_intervals = list(padded_intervals) + list(padded_intervals + 12) + list(padded_intervals + 24)
            root_interval = padded_compound_intervals[root_interval_place]

            higher_places = [root_interval_place + (2*o) for o in range(1, order)]
            higher_intervals = [padded_compound_intervals[p] for p in higher_places]
            chord_intervals = IntervalList([root_interval] + higher_intervals) - root_interval
            return AbstractChord(intervals=chord_intervals)

        else:
            # use the base degrees, and try to build the most likely/consonant chords from those
            # (preferring chords with 3rds and 5ths if possible)
            log(f'Building chord in subscale: {self.name} off of base degree: {degree}')
            assert degree in self.degree_intervals, f'{self.name} does not have a degree {degree}'
            root_degree = degree
            desired_factors = range(1, (2*order), 2) # i.e. chord factors 1, 3, 5, etc.
            desired_degrees = [f + (root_degree-1) for f in desired_factors]
            all_degrees_available = True
            for d in desired_degrees:
                if d not in self.higher_degrees:
                    all_degrees_available = False
                    log(f'Degree {d} not available in this subscale, so we cannot build an ordinary triad')
                    break
            if all_degrees_available:
                # simply build a triad chord since we have all the notes needed:
                log(f'All desired degrees {list(desired_degrees)} are available, so we can build an ordinary triad')
                root_interval = self.degree_intervals[root_degree]
                chord_intervals = IntervalList([self.get_higher_interval(d) for d in desired_degrees])
                log(f'With root interval: {root_interval} and chord intervals: {chord_intervals}, resulting in: {chord_intervals - root_interval}')
                return AbstractChord(intervals=chord_intervals - root_interval)
            else:
                ### otherwise, fall back on valid_chords method:
                valid_chords_on_root = self.valid_chords(root_degree, min_likelihood=0.7, min_consonance=0.5, min_order=order, max_order=order, no5s=False, inversions=False, display=False)
                log(f'Instead choosing a consonant chord from the valid chords that can be built on this degree:\n {valid_chords_on_root}')

                if len(valid_chords_on_root) == 0:
                    log(f'Did not find any with initial parameters, so expanding search parameters')
                    valid_chords_on_root = self.valid_chords(root_degree, min_likelihood=0.5, min_consonance=0.4, min_order=order, max_order=order, no5s=True, inversions=False, display=False)
                    if len(valid_chords_on_root) == 0:
                        log(f'Did not find any with expanded parameters, so dropping all search constraints except subscale membership')
                        valid_chords_on_root = self.valid_chords(root_degree, min_likelihood=0, min_consonance=0, min_order=order, max_order=order, no5s=True, inversions=False, display=False)
                        assert len(valid_chords_on_root) > 0, f"Could somehow not make any chords at all of order={order} on degree {degree} of subscale: {self.name}"
                # secondary filtering step:
                shortlist = []
                for c in valid_chords_on_root:
                    # prefer chords with 3rds and 5th if possible:
                    if (3 in c) and (5 in c):
                        log(f'Found a potential chord that contains a 3rd and a 5th: {c}')
                        shortlist.append(c) # (since valid_chords is already sorted, shortlist is sorted by extension)
                if len(shortlist) >= 1:
                    # return the most likely/consonant
                    return shortlist[0]
                else:
                    # just return the most likely/consonant valid one
                    log(f'Did not find any chords that contain a 3rd and 5th, so just taking the first match')
                    return valid_chords_on_root[0]

        # potential_factor_degrees = {}
        # possible_factor_degrees = {}
        # for f in desired_factors:
        #     potential_factor_degrees[f] = [f, f-1, f+1]
        #     possible_factor_degrees[f] = [pd for pd in potential_factor_degrees if pd in self.degree_intervals]
        #
        # for f,d in possible_factor_degrees:
        #     if len(d) == 0:
        #         raise Exception(f'Cannot build any viable chords of order={order} on degree {degree} of subscale: {self.name}')
        #
        # root_interval = self[root_degree]
        # # try all possible permutations of our N-order chord:
        # factor_intervals = []
        # for f in desired_factors[1:]:
        #


    # def chords(self, order=3):
    #     """returns the list of chords built on every degree of this Subscale."""
    #     chord_list = []
    #     for d, iv in self.degree_intervals.items():
    #         chord_list.append(self.chord(d, order=order))
    #     return chord_list

    def get_possible_parents(self, fast=False, sort=True):
        """returns a list of Scales that are also valid parents for this Subscale"""
        parents = []
        if fast:
            # only search scales (not modes)
            lookup_dict = interval_scale_names
        else:
            lookup_dict = interval_mode_names

        stripped_intervals = self.intervals.strip()
        for scale_intervals, scale_names in lookup_dict.items():
            possible = True
            for iv in stripped_intervals:
                if iv not in scale_intervals:
                    possible = False
                    break
            if possible:
                parents.append(Scale(scale_names[0]))
        # sort by likelihood: (and then by consonance)
        if sort:
            parents = sorted(parents, key=lambda x: (x.likelihood, x.consonance), reverse=True)
        return parents
    @property
    def possible_parents(self):
        return self.get_possible_parents(fast=False)
    @property
    def most_likely_parent(self):
        return self.get_possible_parents(fast=False, sort=True)[0]


    def on_tonic(self, tonic):
        """returns a Subkey object corresponding to this Subscale built on a specified tonic"""
        if isinstance(tonic, str):
            tonic = notes.Note.from_cache(tonic)
        # lazy import to avoid circular dependencies:
        from .keys import Subkey
        return Subkey(intervals=self.intervals, tonic=tonic)



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
    e.g.: (M2, M3, P4, P5, M6, M7),
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
        mode_intervals_from_tonic = IntervalList([Interval.from_cache(i.value, d+2) for d, i in enumerate(mode_intervals_from_tonic)])

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
            from ipdb import set_trace; set_trace(context=30)
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

# initialise empty caches:
cached_consonances = {}
cached_pentatonics = {}

# pre-initialised scales for efficient import by other modules instead of re-init:
NaturalMajor = MajorScale = Scale('major')
Dorian = DorianScale = Scale('dorian')
Phrygian = PhrygianScale = Scale('phrygian')
Lydian = LydianScale = Scale('lydian')
Mixolydian = MixolydianScale = Scale('mixolydian')
NaturalMinor = MinorScale = Aeolian = AeolianScale = Scale('minor')
Locrian = LocrianScale = Scale('locrian')

HarmonicMinor = HarmonicMinorScale = Scale('harmonic minor')
HarmonicMajor = HarmonicMajorScale = Scale('harmonic major')
MelodicMinor = MelodicMinorScale = Scale('melodic minor')
MelodicMajor = MelodicMajorScale = Scale('melodic major')

BebopScale = Scale('major', chromatic_intervals = [m6])

# dict mapping parallel major/minor scales:
parallel_scales = {NaturalMajor: NaturalMinor,
                   HarmonicMajor: HarmonicMinor,
                   MelodicMajor: MelodicMinor}
# parallel scales are symmetric:
parallel_scales.update(reverse_dict(parallel_scales))

# special 'full minor' scale that includes notes of natural, melodic and harmonic minors:
FullMinor = FullMinorScale = Scale('minor', chromatic_intervals=[M6, M7], alias='full minor')
# and full major equivalent for symmetry:
FullMajor = FullMajorScale = Scale('major', chromatic_intervals=[m6, m7], alias='full major')

# subscale definitions:
subscales_to_aliases = {  # major pentatonic type omissions:
                            NaturalMajor.subscale([1,2,3,5,6]): ['major pentatonic', 'pentatonic major', 'major pent', 'pent major', 'pentatonic', 'pent', 'major5', 'maj pentatonic'],
                            NaturalMinor.subscale([1,2,3,5,6]): ['hirajoshi', 'japanese minor pentatonic', 'japanese minor'],
                                  Dorian.subscale([1,2,3,5,6]): ['dorian pentatonic'],
                            NaturalMajor.subscale([1,2,3,5,6], chromatic_intervals=[m3]): ['blues major', 'major blues', 'maj blues', 'major blues hexatonic', 'blues major hexatonic'],

                          # minor pentatonic type omissions:
                            NaturalMinor.subscale([1,3,4,5,7]): ['minor pentatonic', 'pentatonic minor', 'minor pent', 'pent minor', 'm pent', 'minor5', 'm pentatonic'],
                            NaturalMajor.subscale([1,3,4,5,7]): ['okinawan pentatonic'],
                            NaturalMinor.subscale([1,3,4,5,7], chromatic_intervals=[d5]): ['blues minor', 'minor blues', 'blues minor hexatonic', 'minor blues hexatonic', 'm blues hexatonic', 'm blues'],

                          # other types:
                            NaturalMajor.subscale([1,2,4,5,6]): ['blues major pentatonic (omit:3,7)'],
                                Phrygian.subscale([1,2,4,5,6]): ['kumoijoshi', 'kumoi', 'japanese pentatonic', 'japanese mode', 'japanese'],

                            NaturalMajor.subscale([1,2,3,5,7]): ['blues major pentatonic (omit:4,6)'],
                              Mixolydian.subscale([1,2,3,5,7]): ['dominant pentatonic', 'pentatonic dominant', 'dom pentatonic'],

                            NaturalMajor.subscale([1,2,4,5,7]): ['egyptian', 'egyptian pentatonic', 'suspended pentatonic', 'suspended'],
                                 Locrian.subscale([1,2,4,5,7]): ['iwato'],

                            NaturalMinor.subscale([1,3,4,6,7]): ['blues minor pentatonic', 'minor blues pentatonic', 'blues minor pent', 'minor blues pent', 'm blues pent', 'man gong', 'm blues pentatonic'],


                       }
subscales_by_name = unpack_and_reverse_dict(subscales_to_aliases)
interval_subscale_names = {sc.intervals: aliases for sc, aliases in subscales_to_aliases.items()}
subscale_name_intervals = unpack_and_reverse_dict(interval_subscale_names)
######################

MajorPentatonic = MajorPentatonicScale = MajorPent = MajPent = Subscale('major pentatonic')
MinorPentatonic = MinorPentatonicScale = MinorPent = MinPent = Subscale('minor pentatonic')

common_scales = [MajorScale, Dorian, Phrygian, Lydian, Mixolydian, Aeolian, Locrian, HarmonicMajor, HarmonicMinor, MelodicMajor, MelodicMinor]
common_subscales = list(subscales_to_aliases.keys())

# cached scale attributes for performance:
if _settings.PRE_CACHE_SCALES:
    cached_consonances.update({c: c.consonance for c in (common_scales + common_subscales)})
    cached_pentatonics.update({c: c.pentatonic for c in common_scales})
