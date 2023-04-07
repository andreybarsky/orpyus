from qualities import Quality #, Major, Minor, Perfect, Augmented, Diminished
from progressions import ScaleDegree
from util import test
import pdb

class Interval:
    """a signed distance between notes, defined in semitones and degrees (whole-tones).
    infers degree from semitone distance automatically,
    but degree can be specified explicitly to infer an
    augmented or diminished interval etc."""

    def __init__(self, value:int, degree=None):
        if isinstance(value, Interval):
            # casting from another interval object:
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
            # auto-detect degree by assuming ordinary diatonic intervals:
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
    def from_degree(degree, quality=None):
        """alternative init method: given a degree (and an optional quality)
        initialise the appropriate Interval object.
        degree is assumed to be appropriately major/perfect if not specified"""

        default_value = default_degree_intervals[degree]

        if quality is not None:
            # cast to quality object if it is not one:
            quality = Quality(quality)

            # modify interval value up or down depending on quality:
            if degree in perfect_degrees:
                value = default_value + quality.offset_wrt_perfect
            else:
                value = default_value + quality.offset_wrt_major
            return Interval(value, degree=degree)

        else:
            # auto assume perfect or major - no adjustment needed to default
            return Interval(default_value)

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
        """intervals only hash their values, not their degrees"""
        return hash(self.value)

    def __str__(self):
        return f'«{self.value}:{self.name}»'

    def __repr__(self):
        return str(self)

    # #### boolean validity checks for chord construction:
    # def valid_degree(self, deg):
    #     return self.mod in degree_valid_intervals[deg]
    #
    # @property
    # def valid_third(self):
    #     return self.valid_degree(3)
    #
    # @property
    # def valid_fifth(self):
    #     return self.valid_degree(5)
    #
    # @property
    # def valid_seventh(self):
    #     return self.valid_degree(7)
    #
    # @property
    # def common_seventh(self):
    #     """special case: common 7-degree intervals (value 10 or 11) need to be
    #     considered more common than 6ths, which are themselves more common than
    #     the uncommon dim7 (value9). used by automatic chord detection."""
    #     return self.mod in [10,11]


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

degree_names = {1: 'unison',  2: 'second', 3: 'third',
                4: 'fourth', 5: 'fifth', 6: 'sixth', 7: 'seventh',
                8: 'octave', 9: 'ninth', 10: 'tenth',
                11: 'eleventh', 12: 'twelfth', 13: 'thirteenth'}

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

common_intervals = [P1, m2, M2, m3, M3, P4, Dim5, Per5, m6, M6, m7, M7, P8, m9, M9, m10, M10, P11]

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


if __name__ == '__main__':
    unit_test()
