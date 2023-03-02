from muse.util import log, test
import pdb

# bug: inversion of ExtendedIntervals doesn't seem to work

class Interval:

    """a distance between notes, in semitones"""
    def __init__(self, value):
        """Interval init accepts a value as well as an optional degree (position in whole tones relative to tonic=1).
        if degree is not given, we infer whether it is a major or minor chord from its interval.
        otherwise, we detect it as 'diminished' or 'augmented' etc.

        if absolute value is greater than 12, this is regarded as a voicing of the equivalent mod-interval
        e.g. if value= 16, this is considered to be a major third, played an octave above,
        instead of a major 10th. if we DO want this to be a major 10th, see the CompoundInterval class."""

        self.value = value
        self.width = abs(value)

        # whole-octave width, and interval width-within-octave (both strictly positive)
        self.octave_span, self.mod = divmod(self.width, 12)

        self.compound = (self.width >= 12)
        self.extended = False # only False for Inteval class; made True by ExtendedInterval
        self.factor_value = self.mod # these are always the same for Interval class, but different for ExtendedInterval

        self.degree = None # only true for Interval class; overwritten for IntervalDegree

        self.expected_degree = default_interval_degrees[self.mod] # degree is always in the range(1,8) for non-Extended intervals
        self.quality = default_interval_qualities[self.mod]

        self._set_flags()
        self._set_name()

    def _set_flags(self):
        """Intended to be used after value and degree have been assigned;
        sets relevant boolean flags on self.
        Inherited by DegreeInterval and ExtendedInterval."""

        self.minor = (self.quality == 'minor')
        self.major = (self.quality == 'major')
        self.perfect = (self.quality == 'perfect')
        self.diminished = (self.quality in ['diminished', 'double diminished'])
        self.augmented = (self.quality in ['augmented', 'double augmented'])

        self.ascending = (self.value > 0)
        self.descending = (self.value < 0)
        self.unison = (self.mod == 0)

        # deduce whether interval is im/perfectly consonant:
        if self.mod in [1, 6, 11]:
            self.consonant = False
            self.imperfect = False
            self.consonance = 0
        elif self.mod in [0, 5, 7]:
            self.consonant = True
            self.imperfect = False
            self.consonance = 1
        else:
            self.consonant = True
            self.imperfect = True
            # self.consonance = 0.5
            ### we assign consonance rating as 1/d+1,
            # where d is the distance from a perfect 5th (or 4th?)
            # self.consonance = round(1 / min([abs(5 - self.mod), abs(7 - self.mod)]), 1)
            self.consonance = round(1 / (1+(abs(5-self.mod))), 1)
        self.dissonant = not self.consonant

    def _set_name(self):
        """Intended to be used after value and degree have been assigned;
        Sets self.name and self.interval_name to appropriate values given value and degree.
        Inherited by DegreeInterval and ExtendedInterval."""

        interval_name, qualifiers = self._get_interval_name()

        qual_string = f' ({", ".join(qualifiers)})' if len(qualifiers) > 0 else ''

        self.interval_name = interval_name
        self.name = interval_name + qual_string

    def _get_octave_interval_name(self):
        """Finds out what interval name should be in the case that self.mod is 0"""
        if self.octave_span == 0:
            interval_name = 'Unison'
        else:
            number_names = {1: '', 2: 'Double ', 3: 'Triple '}
            if self.octave_span in number_names.keys():
                # single, double, triple octave:
                interval_name = f'{number_names[self.octave_span]}Octave'
            else:
                # 4 octaves, 5 octaves etc.
                interval_name = f'{num_octaves} Octaves'

        qualifiers = ['descending'] if self.descending else []
        return interval_name, qualifiers

    def _get_interval_name(self):
        """Called internally by set_name to figure out what to name this interval.
        Inherited by IntervalDegree or ExtendedInterval.

        In the Interval class, intervals can only be major, minor, perfect. (or dim5)
            but IntervalDegree sets self.quality differently, so this method still works there."""

        if self.mod != 0:
            degree = self.expected_degree if self.degree is None else self.degree
            if degree in degree_names.keys():
                degree_name = degree_names[degree]
            else:
                mod_degree = ((degree - 1) % 8) + 1
                degree_name = degree_names[mod_degree]
            # degree_name = degree_names[degree_to_name] if degree_to_name in degree_names.keys() else degree_names[((degree_to_name-1) % 12)+1]
            interval_name = f'{self.quality.capitalize()} {degree_name.capitalize()}'

            qualifiers = []
            if self.descending:
                qualifiers.append('descending')
            if self.compound and not self.extended:
                qualifiers.append('compound')

            return interval_name, qualifiers
        else:
            return self._get_octave_interval_name()

    def _get_flags(self):
        """Returns a list of the boolean flags associated with this object"""
        flags_names = {
                       'unison': self.unison,
                       'minor': self.minor,
                       'major': self.major,
                       'perfect': self.perfect,
                       'diminished': self.diminished,
                       'augmented': self.augmented,
                       'ascending': self.ascending,
                       'descending': self.descending,
                       'compound': self.compound,
                       'extended': self.extended,
                       'consonant': self.consonant,
                       'imperfect': self.imperfect,
                       'dissonant': self.dissonant,
                       }
        return [string for string, attr in flags_names.items() if attr]

    # interval constructor methods:
    def __add__(self, other):
        if isinstance(other, Interval):
            new_val = self.value + other.value
            if abs(new_val) <= 12:
                return Interval(new_val)
            else:
                return ExtendedInterval(new_val)
        elif isinstance(other, int):
            # cast to interval and call again recursively:
            return self + Interval(other)
        else:
            raise TypeError('Intervals can only be added to integers or other Intervals')

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        if isinstance(other, Interval):
            new_val = self.value - other.value
            if abs(new_val) <= 12:
                return Interval(new_val)
            else:
                return ExtendedInterval(new_val)
        elif isinstance(other, int):
            # cast to interval and call again recursively:
            return self - Interval(other)
        else:
            raise TypeError('Intervals can only be subtracted from integers or other Intervals')

    def __mod__(self, m):
        """performs module on self.value and returns resulting interval"""
        return Interval(self.value % m)

    def __neg__(self):
        """returns the inverted interval, which is distinct from the negative interval.
        negative of Interval(7) (perfect fifth) is Interval(-7) (perfect fifth descending),
        but the inverse of Interval(7) is Interval(-5) (perfect fourth descending)"""
        return Interval(-(12-self.value))

    def __abs__(self):
        if self.value > 0:
            return self
        else:
            return Interval(-self.value)

    def __eq__(self, other):
        """Value equivalence comparison for intervals - returns True if both have
        same value (but disregard degree)"""
        if isinstance(other, Interval):
            return self.value == other.value
        elif isinstance(other, int):
            return self.value == other
        else:
            raise TypeError('Intervals can only be compared to integers or other Intervals')

    def __and__(self, other):
        """Enharmonic equivalence comparison for intervals - returns True if both have
        same mod attr (but disregard degree and signed distance value)"""
        if isinstance(other, Interval):
            return self.value % 12 == other.value % 12
        elif isinstance(other, int):
            return self.value % 12 == other % 12
        else:
            raise TypeError('Intervals can only be compared to integers or other Intervals')

    def __ge__(self, other):
        if isinstance(other, Interval):
            return self.value >= other.value
        elif isinstance(other, int):
            return self.value >= other
        else:
            raise TypeError('Intervals can only be compared to integers or other Intervals')

    def __lt__(self, other):
        if isinstance(other, Interval):
            return self.value < other.value
        elif isinstance(other, int):
            return self.value < other
        else:
            raise TypeError('Intervals can only be compared to integers or other Intervals')

    def __int__(self):
        return self.value

    def __rsub__(self, other):
        return other - self.value

    def __hash__(self):
        """hash this interval in a way that preserves both its degree and value properties"""
        # unlike equality comparison, which compares only semitones,
        # we want the hash function to correctly distinguish between different chords,
        # e.g. to know that a (Aug3, Per5) chord is a sus4,
        # but a mystery chord with explicitly-defined (Per4, Per5) degrees is something else.
        # so we include degree as well as value for hashing purposes
        deg = self.expected_degree if self.degree is None else self.degree
        string_to_hash = f'D{deg}V{self.value}'
        return hash(string_to_hash)

    def __str__(self):
        return f'<{self.value}:{self.name}>'

    def __repr__(self):
        return str(self)


    #### boolean validity checks for chord construction:
    def valid_degree(self, deg):
        return self.mod in degree_valid_intervals[deg]

    def valid_third(self):
        return self.valid_degree(3)

    def valid_fifth(self):
        return self.valid_degree(5)

    def common_seventh(self):
        """special case: common 7-degree intervals (value 10 or 11) need to be
        considered more common than 6ths, which are themselves more common than
        the uncommon dim7 (value9). used by automatic chord detection."""
        return self.mod in [10,11]

    def valid_seventh(self):
        return self.valid_degree(7)

    #### summary helper function:
    def properties(self):
        degree_str = f'{self.expected_degree}' if self.degree is None else self.degree
        degree_name_str = degree_names[self.expected_degree] if self.degree is None else degree_names[self.degree]
        degree_qualifier = '(Expected)' if self.degree is None else ''

        flags = ', '.join(self._get_flags())

        return f"""
        {str(self)}
        Type:       {type(self)}
        Value:      {self.value} semitones
        Mod Value:  {self.mod}
        Degree:     {degree_name_str} ({degree_str}) {degree_qualifier}
        OctaveSpan: {self.octave_span}
        Quality:    {self.quality}
        Consonance: {self.consonance}
        Flags:      {flags}
        ID:         {id(self)}"""

    def summary(self):
        print(self.properties())

class NullInterval:
    """has the attributes that an Interval has, but they are all None
    (mostly used for defaultdict default values in chord factor detection)"""
    def __init__(self):
        self.value = None
        self.mod = None
        self.width = None
        self.degree = None
        self.quality = None

class IntervalDegree(Interval):
    """a distance between notes in semitones, that is also associated with a particular degree in a scale

    the primary difference between this and the Interval class is in having
    a self.degree attribute set (usually by init arg), which then determines
    the self.quality attribute (which can be diminished or augmented, etc.)"""

    def __init__(self, arg1=None, arg2=None, value=None, degree=None, quality=None, extended=False):
        """initialises an IntervalDegree object from one of the following:
        value, degree: integer denoting the semitone distance of this interval.
               plus an optional second arg, another integer denoting the interval's scale degree or chord factor.
               if degree is not given, assume it is the major/perfect degree corresponding to the value.

        degree, quality: integer denoting the scale degree or chord factor of this interval,
                plus an optional second arg, a string denoting the interval's quality
                if quality is not given, assume it is 'major' or 'perfect' (depending on degree)

        we assume that this method is called with arg1 or arg2 as positional args,
        or with value/degree or degree/quality as keyword args.
        """
        self.extended = extended
        # determine value, degree and quality from input args:
        self.value, self.degree, self.quality = self._parse_input(arg1, arg2, value, degree, quality, extended=extended)

        self.width = abs(self.value)

        # whole-octave width, and interval width-within-octave (both strictly positive)
        self.octave_span, self.mod = divmod(self.width, 12)
        self.factor_value = self.mod

        # must have this attr set for compatibility with parent class:
        self.expected_degree = default_interval_degrees[self.mod] # degree is always in the range(1,8) for non-Extended intervals

        self.compound = (self.width >= 12)

        self._set_flags()
        self._set_name()

    #### main input/arg-parsing private method:

    def _parse_input(self, arg1, arg2, value, degree, quality, extended=False):
        """returns the correct value, degree, and quality, given either:
        value and (optional) degree,
          or
        degree and (optional) quality,
        whether provided positionally as arg1, or as explicit keywords.
        """

        if arg1 is not None:
            # parse positional arg1, arg2 pair
            # assert (value is None and degree is None and quality is None), "Received keyword arguments to IntervalDegree.__init__, but positional arguments have already been passed"

            if arg2 is not None:
                # determine whether arg1 is a value or a degree,
                # depending on if arg2 is an integer (implying arg2 is degree and arg1 is value)
                # or a string (implying arg2 is quality and arg1 is degree)
                if isinstance(arg2, int):
                    # arg2 is degree, so arg1 must be value
                    value = arg1
                    degree = arg2
                    # determine quality:
                    quality, degree = self._get_quality_and_degree(value, degree, extended=extended)
                elif isinstance(arg2, str):
                    # arg2 is quality, so arg1 must be degree
                    quality = arg2
                    degree = arg1
                    # determine value:
                    value, quality = self._get_value_and_quality(degree, quality)

            elif arg2 is None:
                # arg2 is not None, so we default to reading arg1 as an interval value
                value = arg1
                # check if we've been passed degree as keyword:
                quality, degree = self._get_quality_and_degree(value, degree=degree, extended=extended)

        else:
            # use keyword arguments instead of positionals
            assert (arg1 is None and arg2 is None), "Received positional arguments to IntervalDegree.__init__, but keyword arguments have already been passed"
            if value is not None:
                # value has been given, so rely on degree arg (if given) to determine quality:
                assert quality is None, "Received value keyword arg to IntervalDegree.__init__, as well as quality keyword arg, which is incompatible"
                quality, degree = self._get_quality_and_degree(value, degree, extended=extended)

            elif degree is not None:
                # initialise from degree without value,
                # but use quality if it is given:
                value, quality = self._get_value_and_quality(degree, quality)

        return value, degree, quality

    ## private input-parsing subroutines:
    @staticmethod
    def _get_quality_and_degree(value, degree, extended=False):
        """determines correct degree given value and optional quality (default major/perfect)

        this is the main distinguishing method of IntervalDegree class,
        but it also works for ExtendedInterval."""

        # differing behaviour for extended and non-extended chords:
        mod_value = abs(value) % 12
        if extended:
            ext_value = abs(value) % 24
        else:
            ext_value = mod_value

        expected_degree = default_interval_degrees[ext_value] if ext_value in default_interval_degrees.keys() else default_interval_degrees[mod_value]

        if degree is None:
            # base case: fall back on major/perfect quality if degree is unspecified
            degree = expected_degree
            quality = default_interval_qualities[mod_value]
            return quality, degree

        else:
            # main use case again: degree has been given,
            # and we must auto-determine whether this is a dim or aug interval, etc.

            # figure out the expected interval width for this degree
            expected_major_interval = degree_major_intervals[degree]
            # and calculate how far this interval is from the major/perfect interval value for that degree

            diff = ext_value - expected_major_interval
            # diff = quality_determining_value - expected_major_interval  # this line seems to break Aug9ths specifically, not sure why

            if is_perfect_degree(degree):
                diff_names = {  -2: 'double diminished',
                                -1: 'diminished',
                                 0: 'perfect',
                                 1: 'augmented',
                                 2: 'double augmented'}

                log(f'Interval of mod-width {mod_value} corresponds to a perfect {expected_degree}th which has interval width: {expected_major_interval}')
            else:
                diff_names = {  -3: 'double diminished',
                                -2: 'diminished',
                                -1: 'minor',
                                 0: 'major',
                                 1: 'augmented',
                                 2: 'double augmented'}
                log(f'Interval has mod-width {mod_value}, asked to correspond to a {degree}th (where major has interval width:{expected_major_interval})')

            if diff in diff_names.keys():
                quality = diff_names[diff]
                log(f'but is shifted by {diff} relative to {diff_names[0].lower()}, making it {quality}')
                return quality, degree
            else:
                ### should never ever happen given other value-checks
                raise ValueError(f'This error should never happen, but: Difference from expected major interval of {diff} is too large to be considered valid for this degree')
                return 'invalid'

    @staticmethod
    def _get_value_and_quality(deg, quality=None):
        """determines correct value given degree and optional quality (default major/perfect)"""
        major_value = degree_major_intervals[deg]

        if quality is None:
            quality = 'perfect' if is_perfect_degree(deg) else 'major'

        if is_perfect_degree(deg):
            modifier_qualities = {  -2: ['double diminished', 'ddim', 'dd'],
                                    -1: ['diminished', 'dim', 'd'],
                                     0: ['perfect', 'perf', 'per', 'p'],
                                     1: ['augmented', 'augm', 'aug', 'a', '+'],
                                     2: ['double augmented', 'daug', 'da', '++']}
        else:
            modifier_qualities = {  -3: ['double diminished', 'ddim', 'dd'],
                                    -2: ['diminished', 'dim', 'd'],
                                    -1: ['minor', 'min', 'm', '-'],
                                     0: ['major', 'maj', 'M', ''],
                                     1: ['augmented', 'augm', 'aug', 'a', '+'],
                                     2: ['double augmented', 'daug', 'da', '++']}

        # inverse dict mapping all accepted chord quality names to lists of their intervals:
        quality_modifiers = {}
        for modifier, names in modifier_qualities.items():
            for name in names:
                quality_modifiers[name] = modifier

        modifier = quality_modifiers[quality]
        value = major_value + modifier
        return value, quality

    def valid_degree(self, deg):
        """IntervalDegree specific behaviour: is only considered valid for the degree it is defined to be"""
        return deg == self.degree

    #### operators and magic methods that overwrite parent class:
    def __neg__(self):
        # overwrites parent class: preserves degree of the negated interval
        """returns the inverted interval, which is distinct from the negative interval.
        negative of Interval(7) (perfect fifth) is Interval(-7) (perfect fifth descending),
        but the inverse of Interval(7) is Interval(-5) (perfect fourth descending)"""
        conv_degree = self.degree - 1
        mod_degree = (conv_degree % 7)
        inv_mod_degree = 7 - mod_degree
        inv_degree = inv_mod_degree + 1

        inv_value = (12-self.value)
        return IntervalDegree(-inv_value, inv_degree)

    def __abs__(self):
        if self.value > 0:
            return self
        else:
            return IntervalDegree(-self.value, degree=self.degree)

    def __str__(self):
        return f'«{self.value}:{self.name}»'
        # log(f'Initialised interval of width {self.value} and degree {self.degree} with name: {self.name}')



class ExtendedInterval(IntervalDegree):
    """Intervals that are explicitly of degrees greater than 8, (but never more than 16)
    such as 9ths and 11ths for swanky jazz chords"""
    def __init__(self, arg1=None, arg2=None, value=None, degree=None, quality=None):
        self.extended = True
        super().__init__(arg1, arg2, value, degree, quality, True)
        assert abs(self.value) > 12; "Intervals narrower than 13 semitones cannot be called 'Extended'"


        ### ExtendedInterval specific behaviour: assign degree by value instead of mod
        self.expected_degree = default_interval_degrees[abs(self.value)] # degree can now be up to 11
        self.compound = False

        # the value used for uniqueness in chord factors is specifically not self.mod for ExtendedIntervals
        self.factor_value = self.value


        self._set_flags()
        self._set_name()

    def __str__(self):
        return f'«<{self.value}:{self.name}>»'

    # def __neg__(self):
    #     return ExtendedInterval(-self.value, self.degree)

# from a list of intervals-from-tonic (e.g. a key specification), get the corresponding stacked intervals:
def stacked_intervals(tonic_intervals):
    stack = [tonic_intervals]
    for i, interval in enumerate(tonic_intervals[1:]):
        prev_interval = stack[-1]
        next_interval = interval - prev_interval
        stack.append(next_interval)
    return stack
# opposite operation: from a list of stacked intervals, get the intervals-from-tonic:
def intervals_from_tonic(interval_stack):
    tonic_intervals = [interval_stack[0]]
    for i in interval_stack[1:]:
        tonic_intervals.append(tonic_intervals[-1] + i)
    return tonic_intervals

# various useful mappings used in interval initialisation/parsing:

degree_names = {1: 'unison',  2: 'second', 3: 'third',
                4: 'fourth', 5: 'fifth', 6: 'sixth', 7: 'seventh',
                8: 'octave', 9: 'ninth', 10: 'tenth', 11: 'eleventh'}

default_interval_qualities = {
                0: 'perfect',
                1: 'minor', 2: 'major',
                3: 'minor', 4: 'major',
                5: 'perfect',
                6: 'diminished', 7: 'perfect',
                8: 'minor', 9: 'major',
                10: 'minor', 11: 'major',
                12: 'perfect',
                13: 'minor', 14: 'major',
                15: 'minor', 16: 'major',
                17: 'perfect',
                18: 'minor'
                }

# how many whole tones does each semitone interval correspond to (by default):
default_interval_degrees = {
                0: 1,     # e.g. unison (0 semitones) )is degree 1
                1:2, 2:2,   # seconds (1 or 2 semitones) are degree 2, etc.
                3:3, 4:3,
                5:4,
                6:5,  # by convention: dim5 is more common than aug4
                7:5,
                8:6, 9:6,
                10:7, 11:7,
                12:8,
                13:9, 14:9,
                15:10, 16:10,
                17: 11,
                18: 12,
                }

# and the reverse mapping
degree_major_intervals = {
                1: 0, # unison
                2: 2, # maj2
                3: 4, # maj3
                4: 5, # per4
                5: 7, # per5
                6: 9, # maj6
                7: 11, # maj7
                8: 12, # octave
                9: 14, # maj9
                10: 16, # maj10
                11: 17, # per11
                }

# mapping intervals to the (default) names of their corresponding degrees:
interval_degree_names = {i: degree_names[default_interval_degrees[i]] for i in range(1, 12)}

# mapping degrees to whether their 'default' representation is major or perfect
default_degree_qualities = {deg: default_interval_qualities[degree_major_intervals[deg]] for deg in range(1,9)}

### mapping scale degrees to valid semitone intervals for those degrees:
degree_valid_intervals = {
                 1: [0],
                 2: [1,2], # min/maj 2nd
                 3: [2,3,4,5], # dim/min/maj/aug 3rd
                 4: [4,5,6], # dim/per/aug 4th
                 5: [6,7,8], # dim/per/aug 5th
                 6: [7,8,9,10], # dim/min/maj/aug 6th
                 7: [9,10,11], # dim/min/maj 7th
                 8: [12], # per8
                 9: [13, 14], # min/maj 9th
                 10: [14,15,16,17], # dim/min/maj/aug 10th
                 11: [16,17,18], # dim/per/aug 11th
                 }

#### utility functions:

def is_perfect_degree(deg):
    # unisons, fourths, and fifths are perfect
    # as are their extended variants (octaves, 11ths, 12ths)
    mod_deg = ((deg-1) % 7 ) + 1
    if mod_deg in [1,4,5]:
        return True
    else:
        return False

# sort intervals by their mod values, rather than their raw values:
def mod_sort(intervals):
    # verify we've been given an iterable:
    assert isinstance(intervals, (list, tuple)), "expected an iterable to mod_sort"
    # verify that it contains only Interval objects:
    assert False not in [isinstance(i, Interval) for i in intervals], "expected an iterable of Interval objects to mod_sort"
    return sorted(intervals, key=lambda x: x.mod)

# interval aliases:

Unison = PerfectFirst = Perfect1st = Perfect1 = Per1 = Per1st = P1 = IntervalDegree(0)

MinorSecond = MinSecond = Minor2nd = Minor2 = Min2 = Min2nd = m2 = IntervalDegree(1)
MajorSecond = MajSecond = Major2nd = Major2 = Maj2 = Maj2nd = M2 = IntervalDegree(2)

DiminishedThird = DimThird = Diminished3rd = Dim3rd = Dim3 = IntervalDegree(2, degree=3)
MinorThird = MinThird = Minor3rd = Minor3 = Min3 = Min3rd = m3 = IntervalDegree(3)
MajorThird = MajThird = Major3rd = Major3 = Maj3 = Maj3rd = M3 = IntervalDegree(4)
AugmentedThird = AugThird = Augmented3rd = Aug3rd = Aug3 = IntervalDegree(5, degree=3)

DiminishedFourth = DimFourth = Diminished4th = Dim4th = Dim4 = IntervalDegree(4, degree=4)
PerfectFourth = PerFourth = Perfect4th = Perfect4 = Fourth = Per4 = Per4th = P4 = IntervalDegree(5)
AugmentedFourth = AugFourth = Augmented4th = Aug4th = Aug4 = IntervalDegree(6, degree=4)

DiminishedFifth = DimFifth = Diminished5th = Dim5th = Dim5 = IntervalDegree(6, degree=5)
PerfectFifth = PerFifth = Perfect5th = Perfect5 = Fifth = Per5 = Per5th = P5 = IntervalDegree(7)
AugmentedFifth = AugFifth = Augmented5th = Aug5th = Aug5 = IntervalDegree(8, degree=5)

DiminishedSixth = DimSixth = Diminished6th = Dim6th = Dim6 = IntervalDegree(7, degree=6)
MinorSixth = MinSixth = Minor6th = Minor6 = Min6 = Min6th = m6 = IntervalDegree(8)
MajorSixth = MajSixth = Major6th = Major6 = Maj6 = Maj6th = M6 = IntervalDegree(9)
AugmentedSixth = AugSixth = Augmented6th = Aug6th = Aug6 = IntervalDegree(10, degree=6)

DiminishedSeventh = DimSeventh = Diminished7th = Dim7th = Dim7 = IntervalDegree(9, degree=7)
MinorSeventh = MinSeventh = Minor7th = Minor7 = Min7 = Min7th = m7 = IntervalDegree(10)
MajorSeventh = MajSeventh = Major7th = Major7 = Maj7 = Maj7th = M7 = IntervalDegree(11)

Octave = Eightth = PerfectEightth = PerEightth = Perfect8th = Per8 = Per8th = P8 = IntervalDegree(12)

MinorNinth = MinNinth = Minor9th = Minor9 = Min9 = Min9th = m9 = ExtendedInterval(13)
MajorNinth = MajNinth = Major9th = Major9 = Maj9 = Maj9th = M9 = ExtendedInterval(14)
AugmentedNinth = AugNinth = Augmented9th = Aug9th = Aug9 = ExtendedInterval(15, degree=9)

DiminishedTenth = DimTenth = Diminished10th = Dim10th = Dim10 = ExtendedInterval(14, degree=10)
MinorTenth = MinTenth = Minor10th = Minor10 = Min10 = Min10th = m10 = ExtendedInterval(15)
MajorTenth = MajTenth = Major10th = Major10 = Maj10 = Maj10th = M10 = ExtendedInterval(16)
AugmentedTenth = AugTenth = Augmented10th = Aug10th = Aug10 = ExtendedInterval(17, degree=10)

DiminishedEleventh = DimEleventh = Diminished11th = Dim11th = Dim11 = ExtendedInterval(16, degree=11)
PerfectEleventh = PerEleventh = Perfect11th = Perfect11 = Per11 = P11 = ExtendedInterval(17)
AugmentedEleventh = AugEleventh = Augmented11th = Aug11th = Aug11 = ExtendedInterval(18, degree=11)

common_intervals = [P1, m2, M2, m3, M3, P4, Dim5, Per5, m6, M6, m7, M7, P8, m9, M9, m10, M10, P11]
