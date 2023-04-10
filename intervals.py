from qualities import Quality #, Major, Minor, Perfect, Augmented, Diminished
from parsing import degree_names, num_suffixes
from util import rotate_list, test
import pdb

class Interval:
    """a signed distance between notes, defined in semitones and degrees (whole-tones).
    infers degree from semitone distance automatically,
    but degree can be specified explicitly to infer an
    augmented or diminished interval etc."""

    def __init__(self, value:int, degree=None):
        if isinstance(value, Interval):
            # accept re-casting from another interval object:
            degree = value.extended_degree
            value = value.value

        self.value = value # signed integer semitone distance

        # value is directional, but width is absolute:
        self.width = abs(value)

        # compound intervals span more than an octave:
        self.compound = (self.width >= 12)

        # whole-octave width, and interval width-within-octave (both strictly positive)
        self.octave_span, self.mod = divmod(self.width, 12)

        # intervals are directional (but unison remains positive, it's a weird hack):
        self.sign = -1 if self.value < 0 else 1
        self.ascending = (self.sign == 1)
        self.descending = (self.sign == -1)
        self.unison = (self.mod == 0)

        if degree is None:
            # no degree provided, so auto-detect degree by assuming ordinary diatonic intervals:
            self.degree = default_interval_degrees[self.mod] * self.sign

            # self.extended_degree is >=8 if this is a ninth or eleventh etc,
            # but self.degree is always mod-7
            self.extended_degree = (self.degree + (7*self.octave_span)) * self.sign

        else:
            # degree has been provided; we validate it here
            default_degree = (default_interval_degrees[self.mod] + (7*self.octave_span)) * self.sign
            # should not be more than 1 away from the default:
            if abs(degree - default_degree) <= 1:
                self.extended_degree = abs(degree) * self.sign
                self.degree = (abs(self.extended_degree) - (7*self.octave_span)) * self.sign
            else:
                raise ValueError(f'Interval init specified that interval of semitone distance {self.value}' +
                f' should correspond to degree={degree}, but that is too far from {default_degree}')



        # determine this interval's quality:
        self.quality = self._detect_quality()

    def _detect_quality(self):
        """uses mod-value and mod-degree to determine the quality of this interval"""

        default_value = default_degree_intervals[abs(self.degree)]
        offset = (self.mod - default_value)

        if abs(self.degree) in perfect_degrees:
            quality = Quality.from_offset_wrt_perfect(offset)
        else: # non-perfect degree, major by default
            quality = Quality.from_offset_wrt_major(offset)
        return quality

    @property
    def name(self):
        if abs(self.extended_degree) in degree_names:
            # interval degree is at most a thirteenth:
            degree_name = degree_names[abs(self.extended_degree)]
            call_compound = False
        else:
            # greater than a thirteenth, so we just call it an extended whatever:
            degree_name = degree_names[abs(self.degree)]
            call_compound = True

        qualifiers = []
        if self.descending:
            qualifiers.append('descending')
        if call_compound:
            qualifiers.append('compound')

        if len(qualifiers) > 0:
            qualifier_string = ", ".join(qualifiers)
            qualifier_string = f' ({qualifier_string})'
        else:
            qualifier_string = ''

        return f'{self.quality.name.capitalize()} {degree_name.capitalize()}{qualifier_string}'

    @property
    def short_name(self):
        if self.value == 0:
            return '‹Rt›'
        else:
            sign_str = '-' if self.sign == -1 else ''
            short_deg = f'{abs(self.extended_degree)}'
            return f'‹{sign_str}{self.quality.short_name}{short_deg}›'

    @property
    def consonance(self):
        # a very fuzzy notion of interval consonance:
        if self.mod in [1, 6, 11]:
            consonance = 0 # dissonant
        elif self.mod in [0, 5, 7]:
            consonance = 1 # perfectly consonant
        else:
            # we assign consonance rating as 1/d+1,
            # where d is the distance from a perfect 5th (or 4th?)
            consonance = round(1 / (1+(abs(5-self.mod))), 1)
        return consonance

    @staticmethod
    def from_degree(degree, quality=None, offset=None):
        """alternative init method: given a degree (and an optional quality)
        initialise the appropriate Interval object.
        degree is assumed to be appropriately major/perfect if not specified"""

        extended_degree = degree
        if degree >= 8:
            octave_span, degree = divmod(degree - 1, 7)
            degree += 1
        else:
            octave_span = 0

        if quality is not None:
            assert offset is None, f'Interval.from_degree received mutually exclusive quality and offset args'
            # cast to quality object if it is not one:
            quality = Quality(quality)
            if degree in perfect_degrees:
                offset = quality.offset_wrt_perfect
            else:
                offset = quality.offset_wrt_major
        elif offset is not None:
            assert quality is None, f'Interval.from_degree received mutually exclusive quality and offset args'
        else:
            # neither quality nor offset given: assume major/perfect, with no offset
            offset = 0

        default_value = default_degree_intervals[degree] + (12*octave_span)
        interval_value = default_value + offset
        return Interval(interval_value, degree=extended_degree)

    @property
    def offset_from_default(self):
        """how many semitones this interval is from its default/canonical (perfect/major) degree"""
        perfect_degree = self.degree in [1,4,5]
        offset = self.quality.offset_wrt_perfect if perfect_degree else self.quality.offset_wrt_major
        return offset

    def __int__(self):
        return self.value

    # interval constructor methods:
    def __add__(self, other):
        if isinstance(other, Interval):
            return Interval(self.value + other.value)
        elif isinstance(other, int):
            # cast to interval and call again recursively:
            return Interval(self.value + other)
        else:
            raise TypeError('Intervals can only be added to integers or other Intervals')

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        if isinstance(other, Interval):
            return Interval(self.value - other.value)
        elif isinstance(other, int):
            return Interval(self.value - other)
        else:
            raise TypeError('Intervals can only be subtracted from integers or other Intervals')

    def __mod__(self, m):
        """performs modulo on self.value and returns resulting interval"""
        return Interval(self.value % m)

    def __neg__(self):
        return Interval(-self.value, -self.extended_degree)

    def __invert__(self):
        """returns the inverted interval, which is distinct from the negative interval.
        negative of Interval(7) (perfect fifth) is Interval(-7) (perfect fifth descending),
        but the inverse, ~Interval(7) is equal to Interval(-5) (perfect fourth descending)"""
        new_value = (-(12-self.mod)) * self.sign
        new_degree = (-(9-abs(self.degree))) * self.sign
        # stretch to higher octave if necessary:
        new_value = new_value + (12 * self.octave_span)* -(self.sign)
        new_degree = new_degree + (7 * self.octave_span)* -(self.sign)
        return Interval(new_value, new_degree)

    def __abs__(self):
        if self.value > 0:
            return self
        else:
            return Interval(-self.value)

    def flatten(self):
        """returns Interval object corresponding to this interval's mod-value and mod-degree"""
        if self.value < 0:
            # invert before flattening:
            return (~self).flatten()
        else:
            return Interval(self.mod, degree=self.degree)

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
            return self.mod == other.mod
        elif isinstance(other, int):
            return self.mod == (other % 12)
        else:
            raise TypeError('Intervals can only be compared to integers or other Intervals')

    def __ge__(self, other):
        if isinstance(other, Interval):
            return self.value >= other.value
        elif isinstance(other, int):
            return self.value >= other
        else:
            raise TypeError('Intervals can only be compared to integers or other Intervals')

    def __le__(self, other):
        return other >= self

    def __lt__(self, other):
        if isinstance(other, Interval):
            return self.value < other.value
        elif isinstance(other, int):
            return self.value < other
        else:
            raise TypeError('Intervals can only be compared to integers or other Intervals')

    def __gt__(self, other):
        return other < self

    def __int__(self):
        return self.value

    def __rsub__(self, other):
        return other - self.value

    def __hash__(self):
        """intervals only hash their values, not their degrees"""
        return hash(self.value)

    def __str__(self):
        return f'«{self.value}:{self.name}»'

    def __repr__(self):
        return str(self)

class IntervalList(list):
    """List subclass that is instantianted with an iterable of Interval-like objects and forces them all to Interval type".
    useful for representing the attributes of e.g. AbstractChords and Scales."""
    def __init__(self, *items):
        if len(items) == 1 and isinstance(items[0], (list, tuple)):
            # been passed a list of items, instead of a series of list items
            items = items[0]
        interval_items = self._cast_intervals(items)

        super().__init__(interval_items)

    @staticmethod
    def _cast_intervals(items):
        interval_items = []
        for item in items:
            if isinstance(item, Interval):
                # add note
                interval_items.append(item)
            elif isinstance(item, int):
                # cast int to interval
                interval_items.append(Interval(item))
            else:
                raise Exception('IntervalList can only be initialised with Intervals, or ints that cast to Intervals')
        return interval_items

    def __str__(self):
        return f'𝄁{", ".join([i.short_name for i in self])} 𝄁'

    def __repr__(self):
        return str(self)

    def __add__(self, other):
        """adds a scalar to each interval in this list,
        or accepts an iterable and performs point-wise addition."""
        if isinstance(other, (int, Interval)):
            return IntervalList([i + other for i in self])
        elif isinstance(other, (list, tuple)):
            assert len(other) == len(self), f'IntervalLists can only be added with scalars or with other iterables of the same length'
            return IntervalList([i + j for i,j in zip(self, other)])
        else:
            raise TypeError(f'IntervalLists can only be added with ints, Intervals, or iterables of either, but got type: {type(other)}')

    def __iadd__(self, other):
        """add in place"""
        if isinstance(other, (int, Interval)):
            for i in self:
                i += other
            return self
        elif isinstance(other, (list, tuple)):
            assert len(other) == len(self), f'IntervalLists can only be added with scalars or with other iterables of the same length'
            for i,j in zip(self, other):
                i += j
            return self
        else:
            raise TypeError(f'IntervalLists can only be added with ints, Intervals, or iterables of either, but got type: {type(other)}')

    def __sub__(self, other):
        """subtracts a scalar from each interval in this list,
        or accepts an iterable of scalars and performs point-wise subtraction."""
        # if isinstance(other, (int, Interval)):
        #     return IntervalList([i - other for i in self])
        # elif isinstance(other, (list, tuple)):
        #     assert len(other) == len(self), f'IntervalLists can only be subtracted with scalars or with other iterables of the same length'
        #     return IntervalList([i - j for i,j in zip(self, other)])
        # else:
        #     raise TypeError(f'IntervalLists can only be subtracted with ints, Intervals, or iterables of either, but got type: {type(other)}')
        return self + (-other)

    def __isub__(self, other):
        self += (-other)
        return self

    def __neg__(self):
        """pointwise negation"""
        return IntervalList([-i for i in self])

    def __hash__(self):
        """IntervalLists hash as sorted tuples for the purposes of chord/key reidentification"""
        return hash(tuple(self.sorted()))

    def sort(self):
        super().sort()

    def sorted(self):
        # note that sorted(IntervalList) returns a list, NOT an IntervalList.
        # we must use this instead
        return IntervalList(sorted(self))

    def strip(self):
        """remove unison intervals from start and end of this list"""
        if self[0].mod == 0:
            new_intervals = self[1:]
        else:
            new_intervals = self[:]
        if self[-1].mod == 0:
            new_intervals = new_intervals[:-1]
        return IntervalList(new_intervals)

    def pad(self, left=True, right=False):
        """if this list does NOT start and/or end with unisons, add them where appropriate"""
        assert self == self.sorted(), f'non-sorted IntervalLists should NOT be padded'
        if (self[0].mod != 0) and left:
            new_intervals = [Interval(0)] + self[:]
        else:
            new_intervals = self[:]
        if (self[-1].mod != 0) and right:
            # add unison/octave above the last interval:
            octave_span = self[-1].octave_span + 1
            new_intervals = new_intervals + [Interval(12*(octave_span))]
        return IntervalList(new_intervals)

    def flatten(self, duplicates=False):
        """flatten all intervals in this list and return them as a new (sorted) list.
        if duplicates=False, remove those that are non-unique. else, keep them. """
        new_intervals = [i.flatten() for i in self]
        if not duplicates:
            new_intervals = list(set(new_intervals))
        return IntervalList(sorted(new_intervals))

    def rotate(self, num_places):
        """returns the rotated IntervalList that begins num_steps up
        from the beginning of this one. used for inversions."""
        return IntervalList(rotate_list(self, num_places))

    def invert(self, position):
        """used for calculating inversions: rotates, then subtracts
        the value of the resulting first interval in list, and returns
        those inverted intervals as a new IntervalList"""
        rotated = self.rotate(position)
        recentred = rotated - rotated[0] # centres first interval to be root again
        inverted = recentred.flatten()   # inverts negative intervals to their correct values
        return inverted

    def stack(self):
        """equivalent to cumsum: returns a new IntervalList based on the successive
        sums of this one, as intervals from tonic.
        e.g. [M3, m3, M3, M3].stack() returns [M3, P5, M7, m10]"""
        interval_stack = self[:1]
        for i in self[1:]:
            interval_stack.append(i + interval_stack[-1])
        return IntervalList(interval_stack)

    def unstack(self):
        """inverse operation - assume we are already stacked as intervals from tonic,
        and recover the original stacked intervals.
        e.g. [M3, P5, M7, m10].unstack() returns [M3, m3, M3, M3]"""
        assert self == self.sorted(), f'Cannot unstack an un-ordered IntervalList: {self}'
        interval_unstack = self[:1]
        for i in range(1, len(self)):
            interval_unstack.append(self[i] - self[i-1])
        return IntervalList(interval_unstack)

# quality-of-life alias:
Intervals = IntervalList

# # from a list of intervals-from-tonic (e.g. a key specification), get the corresponding stacked intervals:
# def stacked_intervals(tonic_intervals):
#     stack = [tonic_intervals[0]]
#     steps_traversed = 0
#     for i, interval in enumerate(tonic_intervals[1:]):
#         prev_interval_value = stack[-1].value
#         next_interval_value = interval.value - prev_interval_value- steps_traversed
#         steps_traversed += prev_interval_value
#         stack.append(Interval(next_interval_value))
#     return stack
# # opposite operation: from a list of stacked intervals, get the intervals-from-tonic:
# def intervals_from_tonic(interval_stack):
#     tonic_intervals = [interval_stack[0]]
#     for i in interval_stack[1:]:
#         tonic_intervals.append(tonic_intervals[-1] + i)
#     return tonic_intervals

# which intervals are considered perfect/major:
perfect_intervals = [0, 5, 7]
major_intervals = [2, 4, 9, 11]
# minor_intervals = [1, 3, 8, 10]

# which degrees are considered perfect:
perfect_degrees = [1, 4, 5]

# how many whole tones does each semitone interval correspond to (by default):
default_interval_degrees = {
                0: 1,          # e.g. unison (0 semitones) is degree 1
                1:2, 2:2,      # seconds (1 or 2 semitones) are degree 2, etc.
                3:3, 4:3,
                5:4,
                6:5,           # by convention: dim5 is more common than aug4
                7:5,
                8:6, 9:6,
                10:7, 11:7,
                }

# and the reverse mapping
default_degree_intervals = {
                1: 0, # unison
                2: 2, # maj2
                3: 4, # maj3
                4: 5, # per4
                5: 7, # per5
                6: 9, # maj6
                7: 11, # maj7
                # 8: 12, # octave
                }





# interval aliases:

Unison = PerfectFirst = Perfect1st = Perfect1 = Per1 = Per1st = P1 = Interval(0)

MinorSecond = MinSecond = Minor2nd = Minor2 = Min2 = Min2nd = m2 = Interval(1)
MajorSecond = MajSecond = Major2nd = Major2 = Maj2 = Maj2nd = M2 = Interval(2)

DiminishedThird = DimThird = Diminished3rd = Dim3rd = Dim3 = Interval(2, degree=3)
MinorThird = MinThird = Minor3rd = Minor3 = Min3 = Min3rd = m3 = Interval(3)
MajorThird = MajThird = Major3rd = Major3 = Maj3 = Maj3rd = M3 = Interval(4)
AugmentedThird = AugThird = Augmented3rd = Aug3rd = Aug3 = Interval(5, degree=3)

DiminishedFourth = DimFourth = Diminished4th = Dim4th = Dim4 = Interval(4, degree=4)
PerfectFourth = PerFourth = Perfect4th = Perfect4 = Fourth = Per4 = Per4th = P4 = Interval(5)
AugmentedFourth = AugFourth = Augmented4th = Aug4th = Aug4 = Interval(6, degree=4)

DiminishedFifth = DimFifth = Diminished5th = Dim5th = Dim5 = Interval(6, degree=5)
PerfectFifth = PerFifth = Perfect5th = Perfect5 = Fifth = Per5 = Per5th = P5 = Interval(7)
AugmentedFifth = AugFifth = Augmented5th = Aug5th = Aug5 = Interval(8, degree=5)

DiminishedSixth = DimSixth = Diminished6th = Dim6th = Dim6 = Interval(7, degree=6)
MinorSixth = MinSixth = Minor6th = Minor6 = Min6 = Min6th = m6 = Interval(8)
MajorSixth = MajSixth = Major6th = Major6 = Maj6 = Maj6th = M6 = Interval(9)
AugmentedSixth = AugSixth = Augmented6th = Aug6th = Aug6 = Interval(10, degree=6)

DiminishedSeventh = DimSeventh = Diminished7th = Dim7th = Dim7 = Interval(9, degree=7)
MinorSeventh = MinSeventh = Minor7th = Minor7 = Min7 = Min7th = m7 = Interval(10)
MajorSeventh = MajSeventh = Major7th = Major7 = Maj7 = Maj7th = M7 = Interval(11)

Octave = Eightth = PerfectEightth = PerEightth = Perfect8th = Per8 = Per8th = P8 = Interval(12)

# compound seconds
MinorNinth = MinNinth = Minor9th = Minor9 = Min9 = Min9th = m9 = Interval(13)
MajorNinth = MajNinth = Major9th = Major9 = Maj9 = Maj9th = M9 = Interval(14)
AugmentedNinth = AugNinth = Augmented9th = Aug9th = Aug9 = Interval(15, degree=9)

# compound thirds
DiminishedTenth = DimTenth = Diminished10th = Dim10th = Dim10 = Interval(14, degree=10)
MinorTenth = MinTenth = Minor10th = Minor10 = Min10 = Min10th = m10 = Interval(15)
MajorTenth = MajTenth = Major10th = Major10 = Maj10 = Maj10th = M10 = Interval(16)
AugmentedTenth = AugTenth = Augmented10th = Aug10th = Aug10 = Interval(17, degree=10)

# compound fourths
DiminishedEleventh = DimEleventh = Diminished11th = Dim11th = Dim11 = Interval(16, degree=11)
PerfectEleventh = PerEleventh = Perfect11th = Perfect11 = Per11 = P11 = Interval(17)
AugmentedEleventh = AugEleventh = Augmented11th = Aug11th = Aug11 = Interval(18, degree=11)

# compound fifths
DiminishedTwelfth = DimTwelfth = Diminished12th = Dim12th = Dim12 = Interval(18, degree=12)
PerfectTwelfth = PerTwelfth = Perfect12th = Perfect12 = Per12 = P12 = Interval(19)
AugmentedTwelfth = AugTwelfth = Augmented12th = Aug12th = Aug12 = Interval(20, degree=12)

# compound sixths
DiminishedThirteenth = DimThirteenth = Diminished13th = Dim13th = Dim13 = Interval(19, degree=13)
MinorThirteenth = MinThirteenth = Minor13th = Minor13 = Min13 = Min13th = m13 = Interval(20)
MajorThirteenth = MajThirteenth = Major13th = Major13 = Maj13 = Maj13th = M13 = Interval(21)
AugmentedThirteenth = AugThirteenth = Augmented13th = Aug13th = Aug13 = Interval(22, degree=13)

common_intervals = [P1, m2, M2, m3, M3, P4, Dim5, Per5, m6, M6, m7, M7, P8, m9, M9, m10, M10, P11, P12, m13, M13]

def unit_test():
    test(Interval(4) - Interval(2), Interval(2))
    test(Interval(4) + 10, Interval(14))
    test(Interval(4), Interval.from_degree(3))
    test(Maj3, Interval(4))
    test(Maj3 + Min3, Per5)
    test(Per5-Min3, Maj3)
    test(Interval(7).consonance, 1)
    test(Interval(6).consonance, 0)
    test(~Interval(-7), Per4)
    test(-Aug9, Interval(-15, degree=-9))
    test(~Dim12, -Aug11)

    test(Interval(14), Interval.from_degree(9))

    # test re-casting:
    test(Interval(Interval(14)), Interval(14))

    # test interval lists:
    test(IntervalList([M3, P5]).pad(left=True, right=True), IntervalList([P1, M3, P5, P8]))
    test(IntervalList([M3, P5]), IntervalList([P1, M3, P5, P8]).strip())
    test(IntervalList([M2, M3, P5]), IntervalList([M3, P5, M9]).flatten())



if __name__ == '__main__':
    unit_test()
