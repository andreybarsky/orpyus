from util import log, test
import pdb

interval_degree_names = {
                0: 'unison',
                1: 'second', 2: 'second',
                3: 'third', 4: 'third',
                5: 'fourth',
                6: 'fifth', 7: 'fifth',
                8: 'sixth', 9: 'sixth',
                10: 'seventh', 11: 'seventh',
                12: 'octave',
                13: 'ninth', 14: 'ninth',
                15: 'tenth', 16: 'tenth',
                17: 'eleventh'}

degree_names = {1: 'unison',
                2: 'second',
                3: 'third',
                4: 'fourth',
                5: 'fifth',
                6: 'sixth',
                7: 'seventh',
                8: 'octave',
                9: 'ninth',
                10: 'tenth',
                11: 'eleventh'}

### we could replace this dict with a procedural method that just parses value and quality?
### update: we have, this is deprecated
# interval_names = {
#                 0: 'unison',
#                 1: 'minor mecond',
#                 2: 'major second',
#                 3: 'minor third',
#                 4: 'major third',
#                 5: 'perfect fourth',
#                 6: 'diminished fifth',
#                 7: 'perfect fifth',
#                 8: 'minor sixth',
#                 9: 'sajor sixth',
#                 10: 'minor seventh',
#                 11: 'major seventh',
#                 12: 'octave',
#                 13: 'minor ninth',
#                 14: 'major ninth',}

default_interval_qualities = {
                0: 'perfect',
                1: 'minor',
                2: 'major',
                3: 'minor',
                4: 'major',
                5: 'perfect',
                6: 'diminished',
                7: 'perfect',
                8: 'minor',
                9: 'major',
                10: 'minor',
                11: 'major',
                12: 'perfect',
                }

default_degree_qualities = {
                1: 'perfect',
                2: 'major',
                3: 'major',
                4: 'perfect',
                5: 'perfect',
                6: 'major',
                7: 'major',
                8: 'perfect'}

# how many whole tones does each semitone interval correspond to (by default):
default_interval_degrees = {
                0: 1,
                1:2, 2:2,
                3:3, 4:3,
                5:4,
                6:5,  # ??? dim5 is more common than aug4 but both are weird
                7:5,
                8:6, 9:6,
                10:7, 11:7,
                12:8,
                13:9, 14:9,
                15:10, 16:10,
                17: 11,
                18: 12,
                }

# reverse mapping
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
    return sorted(intervals, key=lambda x: x.mod)


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
            self.consonance = 0.5
        self.dissonant = not self.consonant

    def _get_octave_interval_name(self):
        """Finds out what interval name should be in the case that self.mod is 0,
        not inherited by subclasses"""
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
            degree_name = degree_names[self.expected_degree] if self.degree is None else degree_names[self.degree]
            interval_name = f'{self.quality.capitalize()} {degree_name.capitalize()}'

            qualifiers = []
            if self.descending:
                qualifiers.append('descending')
            if self.compound:
                qualifiers.append('compound')

            return interval_name, qualifiers
        else:
            return self._get_octave_interval_name()

    def _get_flags(self):
        """Returns a list of the boolean flags associated with this object"""
        flags_names = {
                       self.unison: 'unison',
                       self.minor: 'minor',
                       self.major: 'major',
                       self.perfect: 'perfect',
                       self.diminished: 'diminished',
                       self.augmented: 'augmented',
                       self.ascending: 'ascending',
                       self.descending:' descending',
                       self.compound: 'compound',
                       self.extended: 'extended',
                       self.consonant: 'consonant',
                       self.imperfect: 'imperfect',
                       self.dissonant: 'dissonant',
                       }
        return [string for attr, string in flags_names.items() if attr]


    def _set_name(self):
        """Intended to be used after value and degree have been assigned;
        Sets self.name and self.interval_name to appropriate values given value and degree.
        Inherited by DegreeInterval and ExtendedInterval."""

        interval_name, qualifiers = self._get_interval_name()

        qual_string = f' ({", ".join(qualifiers)})' if len(qualifiers) > 0 else ''

        self.interval_name = interval_name
        self.name = interval_name + qual_string

    # interval constructor methods:
    def __add__(self, other):
        if isinstance(other, Interval):
            new_val = self.value + other.value
            if abs(new_val) <= 12:
                return Interval(new_val)
            else:
                return ExtendedInterval(new_val)
        elif isinstance(other, int):
            return self.value + other
        else:
            raise TypeError('Intervals can only be added to integers or other Intervals')

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        if isinstance(other, Interval):
            new_val = self.value - other_value
            if abs(new_val) <= 12:
                return Interval(new_val)
            else:
                return ExtendedInterval(new_val)
        elif isinstance(other, int):
            return self.value - other
        else:
            raise TypeError('Intervals can only be subtracted from integers or other Intervals')

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
        """Equality comparison for intervals - returns True if both have same number of signed semitones (but disregard degree and mod value)"""
        if isinstance(other, Interval):
            return self.value == other.value
        elif isinstance(other, int):
            return self.value == other
        else:
            raise TypeError('Intervals can only be compared to integers or other Intervals')

    def __gt__(self, other):
        if isinstance(other, Interval):
            return self.value > other.value
        elif isinstance(other, int):
            return self.value > other
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
        # unlike equality comparison, which compares only semitones,
        # we want the hash function to correctly distinguish between different chords,
        # e.g. to know that a (Aug3, Per5) chord is a sus4,
        # but a mystery chord with explicitly-defined (Per4, Per5) degrees is something else.
        # so we include degree as well as value for hashing purposes
        deg = self.expected_degree if self.degree is None else self.degree
        string_to_hash = f'D{deg}V{self.value}'
        return hash(string_to_hash)


    ### boolean validity checks for chord construction:
    def valid_degree(self, deg):
        return self.mod in degree_valid_intervals[deg]

    def valid_third(self):
        return self.valid_degree(3)

    def valid_fifth(self):
        return self.valid_degree(5)

    def valid_seventh(self):
        return self.valid_degree(7)

    def __str__(self):
        return f'<{self.value}:{self.name}>'

    def __repr__(self):
        return str(self)

    # summary function:
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

    @staticmethod
    def from_degree(deg, quality=None):
        """returns an Interval object for some desired degree and quality"""
        major_value = degree_major_intervals(deg)

        if quality is None:
            quality = 'perfect' if is_perfect_degree(deg) else 'major'

        if is_perfect_degree(deg):
            name_variations = {'double diminished': -2,
                               'diminished': -1,
                               'perfect': 0,
                               'augmented': 1,
                               'double augmented': 2}
        else:
            name_variations = {'double diminished': -3,
                               'diminished': -2,
                               'minor': -1,
                               'major': 0,
                               'augmented': 1,
                               'double augmented': 2}

        modifier = name_variations[quality]
        value = major_value + modifier
        if deg > 8:
            return IntervalDegree(value, degree=deg)
        else:
            return ExtendedInterval(value, degree=deg)

class NullInterval:
    """has the attributes that an Interval has, but they are all None
    (useful for defaultdict default values in chord factor detection)"""
    def __init__(self):
        self.value = None
        self.mod = None
        self.width = None
        self.degree = None
        self.quality = None

class IntervalDegree(Interval):
    """a distance between notes, in semitones,
    that is also associated with a particular degree in a scale,
    which can be used to determine its quality.

    Primary deviation from Interval class is having a self.degree attribute set (usually by init arg),
    which then determines the object's self.quality attribute (that can be diminished or augmented, etc.)"""

    def __init__(self, value, degree=None):
        if isinstance(value, Interval):
            # cast existing Interval object to IntervalDegree:
            super().__init__(value.value)
        elif isinstance(value, int):
            super().__init__(value)
        else:
            raise TypeError(f'Expected integer or Interval as input arg to IntervalDegree init method, but got: {type(value)}')

        ### IntervalDegree specific behaviour: auto detect quality
        # if degree is None:
        #     # if degree left unspecified, auto detect both degree and quality:
        #     # (this is correctly inferred for all minor/major/perfect intervals, and assumes tritones to be dim5s)
        #     self.degree = self.expected_degree
        #     assert self.quality == default_interval_qualities[self.mod] # should have been set correctly by parent init method
        #
        # elif degree is not None:
        #     # main use case of this class: explicitly specifying a degree that this interval belongs to
        #     # (to distinguish between, for instance, a dim5 and an aug4, or an aug5 and a min6)
        #     if not self.extended:
        #         assert self.mod in degree_valid_intervals[degree], f"Interval of mod-width {self.mod} cannot be considered a {degree_names[degree]}"
        #     self.degree = degree
        self.degree = self.expected_degree if degree is None else degree
        self.quality = self._get_quality()

        # re-set name and flags to overwrite parent class behaviour:
        self._set_flags()
        self._set_name()


    def _get_quality(self):
        """Main distinguishing method of IntervalDegree class,
        but works as well for ExtendedInterval:
        computes and returns the quality of this interval (dim, min, perf, etc.)
        based on its degree and value"""

        # differing behaviour for extended and non-extended chords:
        if self.extended:
            quality_determining_value = self.value # true for ExtendedInterval
        else:
            quality_determining_value = self.mod  # true for IntervalDegree


        if self.degree == self.expected_degree:
            return self.quality # no need to change self.quality; it is already set correctly

        elif self.degree != self.expected_degree:
            # main use case again: we must auto-determine whether this is a dim or aug interval, etc.
            # figure out the expected interval width for this degree
            expected_major_interval = degree_major_intervals[self.degree]
            # and calculate how far this interval is from the major/perfect interval value for that degree

            diff = self.mod - expected_major_interval
            # diff = quality_determining_value - expected_major_interval  # this line seems to break Aug9ths specifically, not sure why

            if is_perfect_degree(self.degree):
                diff_names = {  -2: 'double diminished',
                                -1: 'diminished',
                                 0: 'perfect',
                                 1: 'augmented',
                                 2: 'double augmented'}

                log(f'Interval of mod-width {self.mod} corresponds to a perfect {self.expected_degree}th which has interval width: {expected_major_interval}')
            else:
                diff_names = {  -3: 'double diminished',
                                -2: 'diminished',
                                -1: 'minor',
                                 0: 'major',
                                 1: 'augmented',
                                 2: 'double augmented'}
                log(f'Interval has mod-width {self.mod}, asked to correspond to a {self.degree}th (where major has interval width:{expected_major_interval})')

            if diff in diff_names.keys():
                quality = diff_names[diff]
                log(f'but is shifted by {diff} relative to {diff_names[0].lower()}, making it {quality}')
                return quality
            else:
                ### should never ever happen given other value-checks
                # raise ValueError(f'This error should never happen, but: Difference from expected major interval of {diff} is too large to be considered valid for this degree')
                return 'invalid'

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

    def valid_degree(self, deg):
        """IntervalDegree specific behaviour: is only valid for the degree it is defined to be"""
        return deg == self.degree


class ExtendedInterval(IntervalDegree):
    """Intervals that are explicitly of degrees greater than 8,
    such as 9ths and 11ths for swanky jazz chords"""
    def __init__(self, value, degree=None):
        super().__init__(value, degree)
        self.extended = True

        assert abs(self.value) > 12; "Intervals narrower than 13 semitones cannot be called 'Extended'"

        # Extended intervals are only compound if they're even bigger than they're meant to be:


        ### ExtendedInterval specific behaviour: assign degree by value instead of mod
        self.expected_degree = default_interval_degrees[abs(self.value)] # degree can now be up to 11
        if degree is None:
            # if degree left unspecified, auto detect both degree and quality:
            # (this is correctly inferred for all minor/major/perfect intervals, and assumes tritones to be dim5s)
            self.degree = self.expected_degree
            assert self.quality == default_interval_qualities[self.mod] # should have been set correctly by parent init method

        elif degree is not None:
            # main use case of this class: explicitly specifying a degree that this interval belongs to
            # (to distinguish between, for instance, a dim5 and an aug4, or an aug5 and a min6)
            # assert self.mod in degree_valid_intervals[degree], "Interval of mod-width {self.mod} cannot be considered a {degree_names[degree]}"
            self.degree = degree
            self.quality = self._get_quality()

        self._set_flags()
        self._set_name()

    # def __neg__(self):
        # return ExtendedInterval(-self.value, self.degree)

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
# AugmentedNinth = AugNinth = Augmented9th = Aug9th = Aug9 = ExtendedInterval(15, degree=9)   # TBI bug to-be-fixed: Aug9 quality is wrongly detected as 'invalid'

# DiminishedTenth = DimTenth = Diminished10th = Dim10th = Dim10 = ExtendedInterval(14, degree=10)
MinorTenth = MinTenth = Minor10th = Minor10 = Min10 = Min10th = m10 = ExtendedInterval(15)
MajorTenth = MajTenth = Major10th = Major10 = Maj10 = Maj10th = M10 = ExtendedInterval(16)
# AugmentedTenth = AugTenth = Augmented10th = Aug10th = Aug10 = ExtendedInterval(17, degree=10)

# DiminishedEleventh = DimEleventh = Diminished11th = Dim11th = Dim11 = ExtendedInterval(16, degree=11)
PerfectEleventh = PerEleventh = Perfect11th = Perfect11 = Per11 = P11 = ExtendedInterval(17)
# AugmentedEleventh = AugEleventh = Augmented11th = Aug11th = Aug11 = ExtendedInterval(18, degree=11)
