from qualities import Major, Minor, Perfect, Augmented, Diminished
from progressions import ScaleDegree



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

        # intervals are directional:
        self.ascending = (self.value > 0)
        self.descending = (self.value < 0)
        self.unison = (self.mod == 0)

        if degree is None:
            # auto-detect degree by assuming ordinary diatonic intervals:
            self.degree = default_interval_degrees[self.mod]
            if self.compound:
                # self.extended_degree is >=8 if this is a ninth or eleventh etc,
                # but self.degree is always mod-7
                self.extended_degree = default_interval_degrees[self.value]

        else:
            pass


        # determine this interval's quality:
        self.quality = self._detect_quality()

    def _detect_quality(self):
        """uses mod-value and mod-degree to determine the quality of this interval"""

        default_value = default_degree_intervals[degree]
        offset = self.value - default_value

        if self.degree in perfect_degrees:

            quality = Quality.from_offset_wrt_perfect(offset)

        else: # non-perfect degree, major by default
            ### TBI: PICK UP HERE


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
