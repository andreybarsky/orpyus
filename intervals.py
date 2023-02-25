from util import log, test

# import constants as con

# possibly replace this dict with a procedural method that just parses value and quality?
# interval_names = {0: 'Unison',
# 1: 'Minor Second',
# 2: 'Major Second',
# 3: 'Minor Third',
# 4: 'Major Third',
# 5: 'Perfect Fourth',
# 6: 'Diminished Fifth',
# 7: 'Perfect Fifth',
# 8: 'Minor Sixth',
# 9: 'Major Sixth',
# 10: 'Minor Seventh',
# 11: 'Major Seventh',
# 12: 'Octave',
# 13: 'Minor Ninth',
# 14: 'Major Ninth'
# 17:'}
default_qualities = {0: 'perfect',
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
                    11: 'major',}

# how many whole tones does each semitone interval correspond to:
interval_degrees = {0: 1,
                    1:2, 2:2,
                    3:3, 4:3,
                    5:4,
                    6:5,  # ??? dim5 is more common than aug4 but both are weird
                    7:5,
                    8:6, 9:6,
                    10:7, 11:7,
                    12:8,
                    13:9, 14:9
                    }

interval_degree_names = {0: 'unison',
                        1: 'second', 2: 'second',
                        3: 'third', 4: 'third',
                        5: 'fourth',
                        6: 'fifth', 7: 'fifth',
                        8: 'sixth', 9: 'sixth',
                        10: 'seventh', 11: 'seventh',
                        12: 'octave',
                        13: 'ninth', 14: 'ninth'}

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

# reverse mapping
major_intervals = {1: 0, # unison
                        2: 2, # maj2
                        3: 4, # maj3
                        4: 5, # per4
                        5: 7, # per5
                        6: 9, # maj6
                        7: 11, # maj7
                        8: 12, # octave
                        9: 14 # maj9
                        }


class Interval:

    """a distance between notes, in semitones"""
    def __init__(self, value, degree=None):
        """Interval init accepts a value as well as an optional degree (position in whole tones relative to tonic=1).
        if degree is not given, we infer whether it is a major or minor chord from its interval.
        otherwise, we detect it as 'diminished' or 'augmented' etc."""

        self.value = value
        self.width = abs(value)
        self.mod = abs(value) % 12

        self.compound = False

        self.ascending = (value > 0)
        self.descending = (value < 0)

        if degree is None:
            # auto detect degree and quality:
            if self.value in interval_degrees.keys():
                self.degree = interval_degrees[self.value]
            elif -self.value in interval_degrees.keys():
                self.degree = interval_degrees[-self.value]
            else:
                self.degree = interval_degrees[self.mod]
            self.quality = default_qualities[self.mod]
        else:
            self.degree = degree
            # degree is specified, auto detect quality:
            if self.value in interval_degrees.keys():
                major_degree = interval_degrees[self.value]
            else:
                major_degree = interval_degrees[self.mod]

            expected_major_interval = major_intervals[degree]
            diff = self.mod - expected_major_interval
            if major_degree in [4,5]:
                diff_names = {  -2: 'double diminished',
                                -1: 'diminished',
                                 0: 'perfect',
                                 1: 'augmented',
                                 2: 'double augmented'}

                # log(f'Interval of mod-width {self.mod} corresponds to a perfect {major_degree}th')
            elif major_degree in [2,3,6,7]:
                diff_names = {  -3: 'double diminished',
                                -2: 'diminished',
                                -1: 'minor',
                                 0: 'major',
                                 1: 'augmented',
                                 2: 'double augmented'}
                # log(f'Interval has mod-width {self.mod}, asked to correspond to a {major_degree}th (where major has interval width:{expected_major_interval})')

            if diff in diff_names.keys():
                self.quality = diff_names[diff]
                # log(f'but is shifted by {diff} relative to {diff_names[0].lower()}, making it {self.quality}')

            else:
                degree_name = degree_names[degree]
                raise ValueError('Interval of mod-width {self.mod} cannot correspond to a {degree_name} whole-tone degree')

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


        # name this interval:
        if self.degree in degree_names.keys():
            degree_name = degree_names[self.degree] # name ninths, 11ths, etc.
            self.componud = False  # interval is called 'compound' if it doesn't have another name
        else:
            degree_name = degree_names[self.degree % 12] # name basic intervals inside the octave
            self.compound = True

        # quality = self.quality[0].upper() + self.quality[1:].lower()

        # interval names for non octaves:
        if self.mod != 0:
            interval_name = f'{self.quality.capitalize()} {degree_name.capitalize()}'
        # separate case for octaves:
        elif self.mod == 0:
            num_octaves = self.value // 12
            if num_octaves is 0:
                interval_name = 'Unison'
            else:
                number_names = {1: '', 2: 'Double ', 3: 'Triple '}
                if num_octaves in number_names.keys():
                    # single, double, triple octave:
                    interval_name = f'{number_names[num_octaves]}Octave'
                else:
                    # 4 octaves, 5 octaves etc.
                    interval_name = f'{num_octaves} Octaves'



        qualifiers = []
        # if self.mod == 0 and self.value != 0:
        #     qualifiers.append('octave')
        if self.descending:
            qualifiers.append('descending')
        if self.compound:
            qualifiers.append('compound')

        qual_string = f' ({", ".join(qualifiers)})' if len(qualifiers) > 0 else ''
        # we can name 9ths, 11ths, etc. explicitly:
        if abs(value) in interval_degrees.keys():
            self.name = interval_name + qual_string
        else:
            self.name = interval__name + qual_string

        # log(f'Initialised interval of width {self.value} and degree {self.degree} with name: {self.name}')



    def __add__(self, other):
        if isinstance(other, Interval):
            return Interval(self.value + other.value)
        elif isinstance(other, int):
            return self.value + other
        else:
            raise TypeError('Intervals can only be added to integers or other Intervals')

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        if isinstance(other, Interval):
            return Interval(self.value - other.value)
        elif isinstance(other, int):
            return self.value - other
        else:
            raise TypeError('Intervals can only be subtracted from integers or other Intervals')

    def __and__(self, other):
        """Enharmonic comparison for intervals: returns True if both have the same mod value"""
        if isinstance(other, Interval):
            return self.mod == other.mod
        else:
            raise TypeError('The & operator for Intervals can only be used to compare enharmonic equivalence to other intervals')

    def __eq__(self, other):
        """Equality comparison for intervals - returns True if both have same number of semitones (but not )"""
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
            return Interval(self.value > other)
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
        return hash(str(self))

    def __str__(self):
        return f'<{self.value}:{self.name}>'

    def __repr__(self):
        return str(self)

# interval aliases:

Unison = PerfectFirst = Perfect1st = P1 = Interval(0)

MinorSecond = Minor2nd = Min2 = m2 = Interval(1)
MajorSecond = Major2nd = Maj2 = M2 = Interval(2)

DiminishedThird = DimThird = Diminished3rd = Dim3rd = Dim3 = Interval(2, degree=3)
MinorThird = Minor3rd = Min3 = m3 = Interval(3)
MajorThird = Major3rd = Maj3 = M3 = Interval(4)
AugmentedThird = AugThird = Augmented3rd = Aug3rd = Aug3 = Interval(5, degree=3)

DiminishedFourth = DimFourth = Diminished4th = Dim4th = Dim4 = Interval(4, degree=4)
PerfectFourth = Perfect4th = Fourth = Per4 = P4 = Interval(5)
AugmentedFourth = AugFourth = Augmented4th = Aug4th = Aug4 = Interval(6, degree=4)

DiminishedFifth = DimFifth = Diminished5th = Dim5th = Dim5 = Interval(6, degree=5)
PerfectFifth = Perfect5th = Fifth = Per5 = P5 = Interval(7)
AugmentedFifth = AugFifth = Augmented5th = Aug5th = Aug5 = Interval(8, degree=5)

DiminishedSixth = Diminished6th = Dim6 = Interval(7, degree=6)
MinorSixth = Minor6th = Min6 = m6 = Interval(8)
MajorSixth = Major6th = Maj6 = M6 = Interval(9)
AugmentedSixth = AugSixth = Augmented6th = Aug6th = Aug6 = Interval(10, degree=6)

DiminishedSeventh = Diminished7th = Dim7 = Interval(9, degree=7)
MinorSeventh = Minor7th = Min7 = m7 = Interval(10)
MajorSeventh = Major7th = Maj7 = M7 = Interval(11)

Octave = Eightth = PerfectEigtth = Perfect8th = P8 = Interval(12)

MinorNinth = Minor9 = Min9 = m9 = Interval(13)
MajorNinth = Major9 = Maj9 = M9 = Interval(14)
