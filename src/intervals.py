from .qualities import Quality #, Major, Minor, Perfect, Augmented, Diminished
from .parsing import degree_names, span_names, multiple_names, num_suffixes, offset_accidentals
from .util import rotate_list, least_common_multiple, euclidean_gcd, numeral_subscript, log
from .conversion import value_to_pitch
from . import _settings
import math
from functools import cached_property

# interval instances are cached for fast init, since they get called a lot:
cached_intervals = {}

class Interval:
    """a signed distance between notes, defined in semitones and degrees (whole-tones).
    infers degree from semitone distance automatically,
    but degree can be specified explicitly to infer an
    augmented or diminished interval etc."""

    # this class specifically covers 'diatonic' Intervals intended for use with
    # scales where the 8th and 1st degrees are unisons.
    # it is overwritten by the IrregularInterval class where that is not the case.
    max_degree = 7
    span_size = 12 # i.e. semitones per 'octave'
    def __init__(self, value, degree=None):
        value, degree = self._re_parse_args(value, degree)
        self.value = value
        self._set_values()
        # detect this interval's degree if it has not been given, and set it either way:
        self._set_degree(degree)
        # set various attribute flags:
        self._set_flags()
        # determine this interval's quality:
        self._set_quality()

    def _re_parse_args(self, value, degree):
        if isinstance(value, Interval):
            # accept re-casting from another interval object:
            if degree is None:
                degree = value.extended_degree
            # changed this to let degree kwarg overwrite init by interval
            value = value.value
        return value, degree

    def _set_values(self):
        # value is directional, but width is absolute:
        self.width = abs(self.value)
        # whole-octave width, and interval width-within-octave (both strictly positive)
        self.octave_span, self.mod = divmod(self.width, self.span_size)
        # unison intervals are those that are some multiple of 12: (or other span size)
        self.unison = (self.mod == 0)


    def _set_degree(self, degree):
        if degree is None:
            # no degree provided, so auto-detect degree by assuming ordinary diatonic intervals:
            self.degree = default_interval_degrees[self.mod] # * self.sign

            # self.extended_degree is >=8 if this is a ninth or eleventh etc,
            # but self.degree is always mod-7,
            # and both are strictly positive
            self.extended_degree = (self.degree + (self.max_degree*self.octave_span))

        else:
            assert degree > 0, "Interval degree must be non-negative"

            if degree == 1:
                assert self.value == 0, f"Degree 1 must always have semitone value of 0, but got: {self.value}"

            # degree has been provided; we validate it here
            self.extended_degree = degree # * self.sign
            self.degree = (self.extended_degree - (self.max_degree*self.octave_span)) #  * self.sign
            if self.unison:
                assert self.degree == 1, f'Interval of value={self.value} and extended_degree={self.extended_degree} is unison (since {self.value} %{self.span_size}=0) and so ought to have degree=1, but got degree={self.degree}'
                assert ((self.extended_degree -1) % self.max_degree) == 0, f'Extended degree of a unison (mod{self.span_size}) interval must (-1) mod to 0, but was: {self.extended_degree}'
            assert 0 < self.degree <= self.max_degree
            # should not be more than 1 away from the default:
            default_degree = (default_interval_degrees[self.mod] + (self.max_degree*self.octave_span)) #* self.sign
            degree_distance_from_default = abs(degree - default_degree)

            if degree_distance_from_default <= 3:
                # all good - interval fits to the desired degree
                pass
                # self.extended_degree = abs(degree) * self.sign
                # self.degree = (abs(self.extended_degree) - (7*self.octave_span)) * self.sign
            elif degree_distance_from_default in {self.max_degree+1,self.max_degree+2,self.max_degree+3}:
                # interval has been asked to correspond to a degree one octave higher or lower than default
                # maybe this is fine fine: we can quietly re-init?
                raise ValueError(f'Interval init specified that interval of semitone distance {self.value}' +
                f' should correspond to degree={degree}, but that appears to be an octave up or down from default degree: {default_degree}')

            else:
                raise ValueError(f'Interval init specified that interval of semitone distance {self.value}' +
                f' should correspond to degree={degree}, but that is too far from default degree: {default_degree}')

    def _set_flags(self):
        # intervals are directional, so even though degree is strictly-positive we store the sign here:
        # if (self.value, self.extended_degree) in cached_intervals:
        #     cached = cached_intervals[self.value, self.extended_degree]
        #     self.sign, self.ascending, self.descending, self.unison, self.compound = cached.sign, cached.ascending, cached.descending, cached.unison, cached.compound
        # else:
        self.sign = -1 if self.value < 0 else 1 # technically "non-negative" rather than "sign"
        self.ascending = (self.sign == 1)
        self.descending = (self.sign == -1)
        # compound intervals span more than an octave:
        self.compound = (self.width >= self.span_size)

    def _set_quality(self):
        """uses mod-value and mod-degree to determine the quality of this interval"""
        # recovering the quality of cached intervals where available is slightly more efficient:
        if (self.value, self.extended_degree) in cached_intervals and self.max_degree == 7:
            self.quality = cached_intervals[(self.value, self.extended_degree)].quality
        else:
            default_value = default_degree_intervals[self.degree]
            offset = (self.mod - default_value)

            if self.degree in self.perfect_degrees:
                self.quality = Quality.from_offset_wrt_perfect(offset)
            else: # non-perfect degree, major by default
                self.quality = Quality.from_offset_wrt_major(offset)

    @cached_property
    def ratio(self):
        if self.value in interval_ratios:
            return interval_ratios[self.value]
        else:
            # this is an extended interval that we don't have a just ratio for,
            # but we can say it's just the ratio of its mod, with the left side
            # raised by 2 to the power of the octave span
            left, right = interval_ratios[self.mod]
            left *= (2**self.octave_span)
            # reduce to simple form:
            gcd = euclidean_gcd(left, right)
            return (left // gcd, right // gcd)

    @cached_property
    def consonance(self):
        """consonance of an interval, defined as
        the base2 log of the least common multiple of
        the sides of that interval's ratio"""
        l, r = self.ratio
        # calculate least common multiple of simple form:
        lcm = least_common_multiple(l,r)
        # log2 of that multiple:
        dissonance = math.log(lcm, 2)
        # this ends up as a number that ranges from 0 (for perfect unison)
        # to just under 15, (for the 7-octave compound minor second, of width 85)

        # so we invert it into a consonance between 0-1:
        return (15 - dissonance) / 15


    @staticmethod
    def from_degree(degree, quality=None, offset=None, max_degree=7):
        """alternative init method: given a degree (and an optional quality)
        initialise the appropriate Interval object.
        degree is assumed to be appropriately major/perfect if not specified"""

        # retrieve a cached interval, unless what we're trying to produce is irregular
        # (since irregular intervals are never cached)
        if max_degree == 7 and (degree, quality, offset) in cached_intervals_by_degree:
            return cached_intervals_by_degree[(degree, quality, offset)]
        else:
            extended_degree = degree
            if degree > max_degree:
                octave_span, degree = divmod(degree - 1, max_degree)
                degree += 1
            else:
                octave_span = 0

            if quality is not None:
                assert offset is None, f'Interval.from_degree received mutually exclusive quality and offset args'
                # cast to quality object if it is not one:
                quality = Quality(quality)
                if degree in self.perfect_degrees:
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
            interval_obj = Interval.from_cache(interval_value, extended_degree, max_degree)
            if _settings.DYNAMIC_CACHING and max_degree==7:
                cached_intervals_by_degree[(extended_degree, quality, offset)] = interval_obj
            return interval_obj

    @property
    def offset_from_default(self):
        """how many semitones this interval is from its default/canonical (perfect/major) degree"""
        perfect_degree = self.degree in self.perfect_degrees
        offset = self.quality.offset_wrt_perfect if perfect_degree else self.quality.offset_wrt_major
        return offset
        # return self.offset_from_default_degree(self.degree)

    def offset_from_degree(self, degree):
        """how many semitones this interval is from some chosen (perfect/major) degree"""
        assert degree > 0
        deg_oct, mod_degree = (divmod(degree-1, self.max_degree))
        mod_degree += 1
        default_value = default_degree_intervals[mod_degree] + (self.span_size*deg_oct)
        offset = self.width - default_value
        return offset

    def __int__(self):
        return self.value

    # interval constructor methods:
    def __add__(self, other):
        # if isinstance(other, Interval):
        #     operand = other.value
        # elif isinstance(other, int):
        #     operand = other
        other_value = int(other)

        # if isinstance(other, (int, Interval)):
        new_value = self.value + other_value
        # result = Interval(new_value)
        # catch special case: addition/subtraction by octaves preserves this interval's degree/quality,
        # (except if there's been a sign change)
        if (self.mod == 0):
            # (but don't worry about it for addition/subtraction of two unisons themselves)
            return self.re_cache(new_value)
        elif int(other) % self.span_size == 0:
            octave_of_addition = int(other) // self.span_size
            # new_degree = ((((self.sign * self.extended_degree) + octave_of_addition) - 1) % 7) + 1
            new_sign = -1 if new_value < 0 else 1
            # invert the degree if there's been a sign change
            new_degree = self.degree if (new_sign == self.sign) else ((self.max_degree+2)-self.degree)
            new_ext_degree = new_degree + (self.max_degree*(abs(new_value) // self.span_size))
            #
            # # new degree is an octave less if there's been a sign change:
            # new_sign = -1 if new_value < 0 else 1
            # if new_sign != self.sign:
            #     new_degree -= 7

            result = self.re_cache(new_value, new_ext_degree)
        else:
            result = self.re_cache(new_value)
        return result
        # elif isinstance(other, int):
        #     # cast to interval and call again recursively:
        #     return Interval(self.value + other)
        # else:
        #     raise TypeError('Intervals can only be added to integers or other Intervals')

    def __radd__(self, other):
        # if isinstance(other, (int, Interval)):
        return self + other
        # else:
        #     return other + self

    def __sub__(self, other):
        if isinstance(other, (int, Interval)):
            # call __add__ method recursively:
            return self + (-other)
        #     return Interval(self.value - other.value)
        # elif isinstance(other, int):
        #     return Interval(self.value - other)
        else:
            raise TypeError('Intervals can only be subtracted from integers or other Intervals')

    def __mod__(self, m):
        """performs modulo on self.value and returns resulting interval"""
        return self.re_cache(self.value % m)

    def __neg__(self):
        if self.value == 0:
            return self
        else:
            return self.re_cache(-self.value, self.extended_degree)

    def __invert__(self):
        """returns the inverted interval, which is distinct from the negative interval.
        negative of Interval(7) (perfect fifth) is Interval(-7) (perfect fifth descending),
        but the inverse, ~Interval(7) is equal to Interval(-5) (perfect fourth descending)"""
        new_mod = (-(self.span_size-self.mod)) * self.sign
        # stretch to higher octave if necessary:
        new_value = new_mod + (self.span_size * self.octave_span)* -(self.sign)
        new_degree = ((self.max_degree+2)-self.degree) + (self.max_degree*self.octave_span) # * self.sign
        # new_degree = new_degree + (7 * self.octave_span) # * -(self.sign)
        return self.re_cache(new_value, new_degree)

    def __pow__(self, octave):
        """An interval to the nth power is the interval raised by that many octaves,
        where intervals in the starting octave (0-12) are in octave 0.
        So that always: iv**0 == iv,
        and iv**1 == iv+12, iv**2 == iv+24,
        iv**-1 == iv-12, etc."""
        # this interval's degree is preserved due to the logic in Interval.__add__
        # pertaining to addition/subtraction of unison intervals
        return self + ((octave)*self.span_size)

    def __abs__(self):
        if self.value > 0:
            return self
        else:
            return self.re_cache(-self.value)

    def flatten(self, octaves=1):
        """returns Interval object corresponding to this interval's mod-value and mod-degree"""
        if self.value < 0:
            # invert before flattening:
            return (~self).flatten(octaves=octaves)
        else:
            # allow for flattening into multiple octaves:
            mod_value = self.value % (self.span_size * octaves)
            mod_degree = ((self.extended_degree - 1) % (self.max_degree * octaves)) + 1
            return self.re_cache(mod_value, mod_degree)

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
            return self.mod == (other % self.span_size)
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

    # def __gt__(self, other):
    #     return self > other

    def __int__(self):
        return self.value

    def __rsub__(self, other):
        return other - self.value

    def __hash__(self):
        """intervals only hash their values, not their degrees"""
        return hash(self.value)

    @property
    def common_degrees(self):
        """returns a list of the degrees that this interval is commonly used as.
        usually this is only one possibility (i.e. m3 and M3 both return [3]),
        but dim5s will return [4,5]"""
        if self.mod == 6:
            return [4,5]
        else:
            return [self.degree]

    @property
    def possible_degrees(self):
        """returns a list of the degrees that this interval could conceivably
        be used as, up to singly augmented/diminished (but not doubly)"""
        return allowable_interval_degrees[self.mod]
    # convenience alias:
    allowable_degrees = possible_degrees

    @cached_property
    def name(self):
        if self.mod == 0 and self.value > 0:
            # this is a 'span', like an octave
            degree_name = span_names[self.max_degree+1].capitalize()
            call_compound = False
            if self.octave_span > 1:
                # it spans more than ONE octave, so we call it double/triple etc:
                if self.octave_span in multiple_names:
                    degree_name = f'{multiple_names[self.octave_span].capitalize()} {degree_name}'
                else:
                    # no name for this multiple, so just call it a "5x Octave" etc.
                    degree_name = f'{octave_span}x {degree_name}'

        elif self.extended_degree in degree_names:
            # interval degree is at most a thirteenth:
            degree_name = degree_names[self.extended_degree].capitalize()
            call_compound = False
        else:
            # greater than a thirteenth, so we just call it an extended whatever:
            degree_name = degree_names[self.degree].capitalize()
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

        return f'{self.quality.full_name.capitalize()} {degree_name}{qualifier_string}'

    @cached_property
    def short_name(self):
        lb, rb = self._brackets
        if self.value == 0:
            return f'{lb}Rt{rb}'
        else:
            sign_str = '-' if self.sign == -1 else ''
            short_deg = f'{self.extended_degree}'
            return f'{lb}{sign_str}{self.quality.short_name}{short_deg}{rb}'


    # alternate str method:
    @cached_property
    def factor_name(self):
        # display this interval as an accidental and a degree:
        acc = offset_accidentals[self.offset_from_default][0]
        sign_str = '' if self.sign == 1 else '-'
        return f'{sign_str}{acc}{self.extended_degree}'

    def __str__(self):
        lb, rb = self._brackets
        return f'{lb}{self.value}:{self.name}{rb}'

    def __repr__(self):
        return str(self)

    @staticmethod
    def from_cache(value, degree=None, max_degree=7, span_size=12):
        """return a cached Interval object with this value if it exists,
        otherwise initialise a new one"""
        if max_degree != 7 or span_size != 12:
            # irregular intervals are not cached, just initialise one instead:
            return IrregularInterval(value, degree, max_degree, span_size)
        elif (value, degree) in cached_intervals:
            return cached_intervals[(value, degree)]
        elif _settings.DYNAMIC_CACHING:
            new_interval = Interval(value, degree)
            cached_intervals[(value,degree)] = new_interval
            return new_interval
        else:
            # no cache, so we must actually init
            return Interval(value, degree)

    def re_cache(self, value, degree=None):
        """Instantiate a new Interval object from cache, using the max_degree
        and span_size parameters of the current Interval object in case this Interval is Irregular"""
        return Interval.from_cache(value, degree, self.max_degree, self.span_size)

    _brackets = _settings.BRACKETS['Interval']

    perfect_degrees = {1,4,5,8} # true for diatonic intervals, but maybe not for irregular intervals?


class IrregularInterval(Interval):
    """Intervals that do not correspond to diatonic scales,
    allowing for Octave intervals of degrees other than 8"""

    # this allows for exotic interval types can have something other than 12 semitones in an octave,
    # or other than 8 notes in a 'span' (octave, nonave, etc.)

    # in practice even for Pentatonic scales it is more useful to use regular Intervals,
    # and the use of IrregularIntervals is reserved for exotic things like Bebop scales

    def __init__(self, value, degree, max_degree, span_size=None):
        if max_degree == 7:
            raise Exception('IrregularInterval initialised with max_degree=7; this should be a normal Interval instead')
        self.max_degree = max_degree
        if span_size is None:
            if max_degree > 7:
                # if more than 7 degrees, keep the 12 semitone span:
                span_size = 12
            else:
                # otherwise pick a sensible default
                span_size = default_degree_intervals[max_degree]
        self.span_size = span_size

        self.subscript = numeral_subscript(self.max_degree) # clarifying marker for printing

        # initialise the rest as Interval class does:
        self.value = value
        self._set_values()
        self._set_degree(degree)
        self._set_flags()
        self._set_quality()

    def __hash__(self):
        # IrregularIntervals hash separately to normal intervals:
        return hash((self.max_degree, self.span_size, self.value))

    @property
    def short_name(self):
        lb, rb = self._brackets
        if self.value == 0:
            return f'{lb}Rt{self.subscript}{rb}'
        else:
            sign_str = '-' if self.sign == -1 else ''
            short_deg = f'{self.extended_degree}'
            return f'{lb}{sign_str}{self.quality.short_name}{short_deg}{self.subscript}{rb}'

    # alternate str method:
    @property
    def factor_name(self):
        # display this interval as an accidental and a degree:
        acc = offset_accidentals[self.offset_from_default][0]
        sign_str = '' if self.sign == 1 else '-'
        return f'{sign_str}{acc}{self.extended_degree}'


    def __str__(self):
        lb, rb = self._brackets
        return f'{lb}{self.value}:{self.name}{self.subscript}{rb}'



class IntervalList(list):
    """List subclass that is instantianted with an iterable of Interval-like objects and forces them all to Interval type".
    useful for representing the attributes of e.g. AbstractChords and Scales."""
    def __init__(self, *items):
        if len(items) == 1 and isinstance(items[0], (list, tuple)):
            # been passed a list of items, instead of a series of list items
            items = items[0]
        interval_items = self._cast_intervals(items)

        super().__init__(interval_items)
        self.values_cached = False

    @staticmethod
    def _cast_intervals(items):
        interval_items = []
        for item in items:
            if isinstance(item, Interval):
                # add interval (preserving IrregularIntervals if present)
                interval_items.append(item)
            elif isinstance(item, int):
                # cast int to interval (using cache if it exists)
                interval_items.append(Interval.from_cache(item))
            else:
                raise Exception('IntervalList can only be initialised with Intervals, or ints that cast to Intervals')
        return interval_items

    def __add__(self, other):
        """adds a scalar to each interval in this list,
        concatenates with another IntervalList,
        or accepts another iterable and performs point-wise addition."""
        if isinstance(other, (int, Interval)):
            return IntervalList([i + other for i in self])
        elif isinstance(other, IntervalList):
            # concatenation with another IntervalList (as with normal list)
            return IntervalList(list(self) + list(other))
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

    def __abs__(self):
        """returns a new IntervalList where any negative intervals are inverted to be positive"""
        return IntervalList([~i if i < 0 else i for i in self])

    def __hash__(self):
        """IntervalLists hash as sorted tuples for the purposes of chord/key reidentification"""
        return hash(tuple(self.sorted()))

    def __contains__(self, item):
        """check if interval with a value (not degree) of item is contained inside this IntervalList"""
        # using self.value_set for efficient lookup"""
        if isinstance(item, Interval):
            item = item.value # lookup intervals by value, else just accept ints
        return item in self.value_set

    @cached_property
    def value_set(self):
        # for efficient use of __contains__
        self.values_cached = True # used to determine if cache needs to be cleared by mutation
        return set([s.value for s in self])

    @property
    def octave_span(self):
        """an IntervalList's octave span is the octave span between its min and max members"""
        span = max(self) - min(self)
        return span.octave_span

    def append(self, item):
        """as list.append, but updates our set object as well"""
        super().append(item)
        if self.values_cached:
            del self.value_set # clear value_set cache so it can be recomputed again later
            self.values_cached = False

    def remove(self, item):
        super().remove(item)
        if self.values_cached:
            del self.value_set # clear value_set cache so it can be recomputed again later
            self.values_cached = False

    def pop(self, item):
        popped_item = self[-1]
        del self[-1]
        if self.values_cached:
            del self.value_set # clear value_set cache so it can be recomputed again later
            self.values_cached = False

    def unique(self):
        """returns a new IntervalList, where repeated notes are dropped after the first"""
        unique_intervals = []
        unique_intervals_set = set() # for efficiency
        for iv in self:
             if iv not in unique_intervals_set:
                 unique_intervals.append(iv)
                 unique_intervals_set.add(iv)
        return IntervalList(unique_intervals)

    def repeated(self):
        """Opposite of self.unique - returns a new IntervalList containing only the
        intervals that are repeated more than once in this existing object"""
        repeated_intervals_set = set()
        unique_intervals_set = set() # for efficiency
        for iv in self:
             if iv not in unique_intervals_set:
                 unique_intervals_set.add(iv)
             else:
                 repeated_intervals_set.add(iv)
        # return in same order as original:
        return IntervalList([iv for iv in self if iv in repeated_intervals_set])

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
        iv_class = self[0].__class__
        if (self[0].mod != 0) and left:
            new_intervals = [iv_class.from_cache(0, None, self[0].max_degree)] + self[:]
        else:
            new_intervals = self[:]
        if (self[-1].mod != 0) and right:
            # add unison/octave above the last interval:
            octave_span = self[-1].octave_span + 1
            new_intervals = new_intervals + [iv_class.from_cache(self[0].span_size*(octave_span), None, self[0].max_degree)]
        return IntervalList(new_intervals)

    def strict_pad(self, left=True, right=False):
        """like IntervalList.pad, but strips beforehand, ensuring that the requested
        padding is the ONLY padding in the list.
        for example:
            IntervalList([2,7,12]).pad(left=True) gives intervals [0,2,7,12]
        but IntervalList([2,7,12]).strict_pad(left=True) gives intervals [0,2,7]  """
        return self.strip().pad(left, right)

    def flatten(self, octaves=1, duplicates=False):
        """flatten all intervals in this list and return them as a new (sorted) list.
        if duplicates=False, remove those that are non-unique. else, keep them. """
        new_intervals = [i.flatten(octaves=octaves) for i in self]
        if not duplicates:
            new_intervals = list(set(new_intervals))
        return IntervalList(sorted(new_intervals))

    def rotate(self, num_places, unstack=False, preserve_degrees=False):
        """returns the rotated IntervalList that begins num_steps up
        from the beginning of this one. used for inversions.
        if unstack=True, first unstacks, then rotates, then stacks again (used for modes)"""
        if not unstack:
            return IntervalList(rotate_list(self, num_places))
        else:
            original_degrees = [iv.extended_degree for iv in self]
            # preserve original padding:
            padded_left = (self[0] == 0)
            padded_right = (self[-1].mod == 0)
            # unstack, rotate, stack again:
            unstacked_intervals = self.strip().pad(left=False, right=True).unstack()
            rotated_intervals = IntervalList(rotate_list(unstacked_intervals, num_places))
            stacked_intervals = rotated_intervals.stack().strip().pad(left=padded_left, right=padded_right)
            if preserve_degrees:
                # restore the degrees of the original intervals:
                try:
                    stacked_intervals = IntervalList([iv.re_cache(iv.value, original_degrees[i]) for i, iv in enumerate(stacked_intervals)])
                except Exception as e:
                    raise Exception(f'Error rotating IntervalList: {e}\n (try rotating with preserve_degrees=False instead)')
            # pad to the original padding:
            return stacked_intervals

    def mode(self, n, preserve_degrees=True):
        """if this IntervalList is structured as the intervals of a scale,
        return the scale that is the Nth mode of that scale"""
        return self.rotate(n-1, unstack=True, preserve_degrees=preserve_degrees)

    def invert(self, position):
        """used for calculating inversions: rotates, then subtracts
        the value of the resulting first interval in list, and returns
        those inverted intervals as a new IntervalList"""
        if position >= len(self):
            # mod into own range: i.e. a list of 5 items, rotated 5 times, is the same as itself
            position = position % len(self)

        # first, rotate the interval list: (now it is non-sorted)
        rotated = self.rotate(position)
        # then add octaves where needed: (to make it sorted)
        ascending = rotated.make_ascending()
        # then recentre by subtracting by the first interval:
        recentred = ascending - ascending[0]
        # positive = abs(recentred) # inverts any negative intervals to their positive inversions
        # inverted = positive.unique().sorted()
        # inverted = recentred.flatten()   # inverts negative intervals to their correct values
        # inverted = IntervalList(list(set([~i if i < 0 else i for i in recentred]))).sorted()
        return recentred

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

    def _seems_stacked(self):
        """makes a best guess as to whether this is a list of stacked intervals (True),
        or a list of unstacked intervals (False).
        effective for Scale intervals, but NOT for Chord intervals"""
        if max(self) < 5:
            # every pentatonic scale has unstacked intervals of a major third at most
            return False
        elif len(self) != len(self.value_set):
            # repeated, non-unique intervals guarantee unstacked:
            return False
        else:
            # this is sufficient to distinguish between stacked and unstacked intervals
            # for all canonical scale names at least
            return True

    def is_sanitised(self):
        """returns True if no intervals in this list are double sharp or
        double flat, and no two intervals fall on the same degree.
        (intended to qualify an IntervalList for casting into a ScaleFactors object)"""
        degrees = []
        for iv in self:
            if abs(iv.offset_from_default) >= 2:
                return False
            degrees.append(iv.degree)
        if len(degrees) != len(set(degrees)):
            return False
        else:
            return True

    def _undouble_qualities(self):
        """returns a new IntervalList with the same values but where no interval
        is double sharp or double flat.
        (this is one half of the sanitise_degrees routine)"""
        new_ivs = []
        for iv in self:
            if abs(iv.offset_from_default) >= 2:
                new_iv = iv.re_cache(value=iv.value)
                new_ivs.append(new_iv)
            else:
                new_ivs.append(iv)
        return IntervalList(new_ivs)

    def _respace_degrees(self, backward=False):
        """returns a new IntervalList with the same values but spacing out degrees if
        any two intervals fall on the same one. This does not guarantee that the resulting
        intervals all fall on separate degrees, but repeated iterations of this method
        converge to that solution, provided there is enough empty space in the scale.
        (this is the second half of the sanitise_degrees routine)"""
        old_degrees = set([iv.degree for iv in self])
        new_degrees = set()
        new_ivs = []
        # reverse order of operations if going backward:
        iv_list = self if not backward else self[::-1]
        descending_offsets = [+1, -1] if not backward else [-1, +1]
        ascending_offsets = descending_offsets[::-1]

        for i, iv in enumerate(iv_list):
            if iv.degree not in new_degrees:
                # a degree that hasn't been used yet in this pass
                new_ivs.append(iv)
                new_degrees.add(iv.degree)
            else:
                # this degree has already been used in this pass, so re-allocate to a new one
                reallocated = False
                for offset in descending_offsets:
                    possible_new_degree = iv.degree + offset
                    if possible_new_degree not in old_degrees:
                        # a slot for a degree that won't be filled later
                        new_iv = iv.re_cache(value=iv.value, degree=possible_new_degree)
                        new_ivs.append(new_iv)
                        new_degrees.add(new_iv.degree)
                        reallocated = True
                        break
                if not reallocated:
                    # no nearby degrees that won't be filled, so use one that
                    # might be filled later anyway (to correct on a later iteration)
                    for offset in ascending_offsets:
                        possible_new_degree = iv.degree + offset
                        if possible_new_degree not in new_degrees:
                            new_iv = iv.re_cache(value=iv.value, degree=possible_new_degree)
                            new_ivs.append(new_iv)
                            new_degrees.add(new_iv.degree)
                            reallocated = True
                            break
                if not reallocated:
                    # failure case
                    raise Exception(f'Terminal failure to respace degrees in interval list: {self}')
        if backward:
            new_ivs = new_ivs[::-1]
        return IntervalList(new_ivs)


    def sanitise_degrees(self):
        """return a new IntervalList with the same values but with degrees altered
        such that nothing is doubly augmented/diminished, and no two intervals fall on
        the same degree"""
        cur_list = IntervalList(self)
        max_iter = 10 # just in case of infinite loop
        iter_num = 0
        backward = False
        log(f'Sanitising interval degrees for: {cur_list}')
        while not cur_list.is_sanitised():
            # perform iterative sanitisation steps:
            cur_list = cur_list._undouble_qualities()
            log(f'Iteration {iter_num}a: undoubling: {cur_list}')
            cur_list = cur_list._respace_degrees(backward=backward)
            log(f'           {iter_num}b: respacing: {cur_list} {"(backward)" if backward else ""}')

            # increment iteration num to catch infinite loop,
            # and swap order of operations for degree respacing on each iteration:
            backward = not backward
            iter_num += 1
            if iter_num >= max_iter:
                raise Exception(f'Reached max number of iterations while trying to sanitise interval list: {self}')
        log(f'\nFinished after {iter_num} iterations: {cur_list}')
        return cur_list

    def make_ascending(self):
        """return another version of this IntervalList where all intervals
        have the same mod value, but are in strictly ascending order
        by looping through and raising each one by an octave if it is smaller than the previous"""
        new_ivs = [self[0]]
        for iv in self[1:]:
            if iv < new_ivs[-1]:
                # previous interval is larger than this one
                # so figure out how many octaves we need to raise this one by:
                octave_diff = (new_ivs[-1] - iv).octave_span + 1
                new_ivs.append(iv ** octave_diff)
            else:
                new_ivs.append(iv)
        return IntervalList(new_ivs)

    def to_factors(self):
        # alternate string method, reports raised/lowered factor integers instead of major/minor/perfect degrees
        return [iv.factor_name for iv in self]

    @property
    def as_factors(self):
        return self.to_factors()

    def __str__(self):
        lb, rb = self._brackets
        return f'{lb}{", ".join([i.short_name for i in self])}{rb}'

    # # alternative str method:
    # def as_factors(self):
    #     """returns this list's intervals represented as numeric degree factors instead of quality-intervals"""
    #     lb, rb = self._brackets
    #     return f'{lb}{", ".join([i.factor_name for i in self])}{rb}'

    def __repr__(self):
        return str(self)

    # IntervalList object unicode identifier:
    _brackets = _settings.BRACKETS['IntervalList']

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
# perfect_intervals = {0, 5, 7}
# major_intervals = {2, 4, 9, 11}
# minor_intervals = [1, 3, 8, 10]

# which degrees are considered perfect:
# perfect_degrees = {1, 4, 5}

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

allowable_interval_degrees = {
                0: [1],
                1: [2],
                2: [2,3],
                3: [2,3],
                4: [3,4],
                5: [3,4,5],
                6: [4,5],
                7: [5,6],
                8: [5,6],
                9: [6,7],
                10: [6,7],
                11: [7],
}

# defaults of degrees in higher octaves, just in case:
higher_defaults = {k+(7*o):v+(12*o) for k,v in default_degree_intervals.items() for o in range(1,3)}
default_degree_intervals.update(higher_defaults)


# interval aliases:

Unison = PerfectFirst = Perfect1st = Perfect1 = Per1 = Per1st = P1 = Rt = Interval(0)

MinorSecond = MinSecond = Minor2nd = Minor2 = Min2 = Min2nd = m2 = Interval(1)
MajorSecond = MajSecond = Major2nd = Major2 = Maj2 = Maj2nd = M2 = Interval(2)

DiminishedThird = DimThird = Diminished3rd = Dim3rd = Dim3 = d3 = Interval(2, degree=3)
MinorThird = MinThird = Minor3rd = Minor3 = Min3 = Min3rd = m3 = Interval(3)
MajorThird = MajThird = Major3rd = Major3 = Maj3 = Maj3rd = M3 = Interval(4)
AugmentedThird = AugThird = Augmented3rd = Aug3rd = Aug3 = A3 = Interval(5, degree=3)

DiminishedFourth = DimFourth = Diminished4th = Dim4th = Dim4 = d4 = Interval(4, degree=4)
PerfectFourth = PerFourth = Perfect4th = Perfect4 = Fourth = Per4 = Per4th = P4 = Interval(5)
AugmentedFourth = AugFourth = Augmented4th = Aug4th = Aug4 = A4 = Interval(6, degree=4)

DiminishedFifth = DimFifth = Diminished5th = Dim5th = Dim5 = d5 = Interval(6, degree=5)
PerfectFifth = PerFifth = Perfect5th = Perfect5 = Fifth = Per5 = Per5th = P5 = Interval(7)
AugmentedFifth = AugFifth = Augmented5th = Aug5th = Aug5 = A5 = Interval(8, degree=5)

DiminishedSixth = DimSixth = Diminished6th = Dim6th = Dim6 = d6 = Interval(7, degree=6)
MinorSixth = MinSixth = Minor6th = Minor6 = Min6 = Min6th = m6 = Interval(8)
MajorSixth = MajSixth = Major6th = Major6 = Maj6 = Maj6th = M6 = Interval(9)
AugmentedSixth = AugSixth = Augmented6th = Aug6th = Aug6 = A6 = Interval(10, degree=6)

DiminishedSeventh = DimSeventh = Diminished7th = Dim7th = Dim7 = d7 = Interval(9, degree=7)
MinorSeventh = MinSeventh = Minor7th = Minor7 = Min7 = Min7th = m7 = Interval(10)
MajorSeventh = MajSeventh = Major7th = Major7 = Maj7 = Maj7th = M7 = Interval(11)

Octave = Eightth = PerfectEightth = PerEightth = Perfect8th = Per8 = Per8th = P8 = Interval(12)

# compound seconds
MinorNinth = MinNinth = Minor9th = Minor9 = Min9 = Min9th = m9 = Interval(13)
MajorNinth = MajNinth = Major9th = Major9 = Maj9 = Maj9th = M9 = Interval(14)
AugmentedNinth = AugNinth = Augmented9th = Aug9th = Aug9 = Interval(15, degree=9)

# compound thirds
DiminishedTenth = DimTenth = Diminished10th = Dim10th = Dim10 = d10 = Interval(14, degree=10)
MinorTenth = MinTenth = Minor10th = Minor10 = Min10 = Min10th = m10 = Interval(15)
MajorTenth = MajTenth = Major10th = Major10 = Maj10 = Maj10th = M10 = Interval(16)
AugmentedTenth = AugTenth = Augmented10th = Aug10th = Aug10 = A10 = Interval(17, degree=10)

# compound fourths
DiminishedEleventh = DimEleventh = Diminished11th = Dim11th = Dim11 = d11 = Interval(16, degree=11)
PerfectEleventh = PerEleventh = Perfect11th = Perfect11 = Per11 = P11 = Interval(17)
AugmentedEleventh = AugEleventh = Augmented11th = Aug11th = Aug11 = A11 = Interval(18, degree=11)

# compound fifths
DiminishedTwelfth = DimTwelfth = Diminished12th = Dim12th = Dim12 = d12 = Interval(18, degree=12)
PerfectTwelfth = PerTwelfth = Perfect12th = Perfect12 = Per12 = P12 = Interval(19)
AugmentedTwelfth = AugTwelfth = Augmented12th = Aug12th = Aug12 = A12 = Interval(20, degree=12)

# compound sixths
DiminishedThirteenth = DimThirteenth = Diminished13th = Dim13th = Dim13 = d13 = Interval(19, degree=13)
MinorThirteenth = MinThirteenth = Minor13th = Minor13 = Min13 = Min13th = m13 = Interval(20)
MajorThirteenth = MajThirteenth = Major13th = Major13 = Maj13 = Maj13th = M13 = Interval(21)
AugmentedThirteenth = AugThirteenth = Augmented13th = Aug13th = Aug13 = A13 = Interval(22, degree=13)

common_intervals = [P1, m2, M2, m3, M3, P4, d5, P5, m6, M6, m7, M7, P8, m9, M9, m10, M10, P11, P12, m13, M13]
# cache common intervals by semitone value and scale degree for efficiency:
cached_intervals = {(iv.value, iv.extended_degree):iv for iv in common_intervals}
# None is also a valid degree index for the default/common intervals:
cached_intervals.update({(iv.value, None):iv for iv in common_intervals})
# also cache interval init by degree, plus one of quality or offset
cached_intervals_by_degree = {(iv.extended_degree, None, iv.offset_from_default):iv for iv in common_intervals}
cached_intervals_by_degree.update({(iv.extended_degree, iv.quality, None):iv for iv in common_intervals})

# interval whole-number ratios according to five-limit just-intonation:
interval_ratios = {0: (1,1),  1: (16,15),  2: (9,8),    3: (6,5),
                   4: (5,4),  5: (4,3),    6: (25,18),  7: (3,2),
                   8: (8,5),  9: (5,3),   10: (16,9),  11: (15,8),
                   12: (2,1)}
