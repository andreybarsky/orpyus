from .chords import AbstractChord
from . import parsing
from .config import settings
from .util import reduce_aliases, log
from .qualities import Quality, Major, Minor, Ind, minor_mod, parse_chord_modifiers, ChordModifier
from .intervals import Interval, IntervalList
from .parsing import auto_split

from math import ceil
from functools import cached_property

### class representing roman numerals as used in ScaleChords and Progressions,
### can contain chord information (as ChordModifiers after numeral) but no
### intrinsic scale understanding (which is reserved for ScaleChord class)
class RomanNumeral:
    """RomanNumerals are initialised with a single argument: a string that
    starts with a roman numeral, for example 'I' or 'iii' or 'VII',
    and can additionally have any or all of the following properties:
    - case is distinguished, so that III is parsed as maj3 and iii as m3
    - leading accidentals are allowed, so that bIII is parsed as maj2.5 (equivalent to m3)
    - inversions are allowed, as a slash followed by an integer, such as: V/1 (maj5, first inversion)
    - secondary chords are allowed, as a slash followed by a numeral, such as: V/V (maj5 of the dominant key)
    - both inversions AND secondary chords at the same time, such as: V/1/V or V/V/1
    - chord modifiers can be used after the primary chord, such as: V7 or IVsus4/V

    note that RomanNumerals do not point at an interval-from-root, but at a scale degree.
        (that is, a iii in the key of C is Em, but a iii in Cm is E♭m)
    and that flat/sharp numerals are considered relative to 'default' major degrees,
        so that a iii in Cm is E♭m, and so is a ♭iii
        and a IV in C lydian is F♯, and so is a ♯IV
    """

    # this class uses singleton instances of each individual numeral type
    # which are stored in this class attribute dict:
    singleton_numerals = {}
    def __new__(cls, name):
        """constructor method to enforce singleton instances of each numeral"""

        # catch re-casting:
        if isinstance(name, RomanNumeral):
            # i.e. if passed a RomanNumeral as first arg, just quietly return it
            return name

        if name in cls.singleton_numerals:
            return cls.singleton_numerals[name]
        else:
            obj = object.__new__(cls)

            # instance 'initialisation', setting object attributes:#
            if not parsing.begins_with_roman_numeral(name):
                raise ValueError(f'init arg to RomanNumeral does not seem to start with a numeral: {name}')

            obj.primary_numeral, obj.inversion, obj.secondary_numeral = obj._separate_slashes(name)

            obj.primary_degree, obj.accidental, obj.modifiers = obj._parse_numeral_string(obj.primary_numeral)

            # natural degree is the same as the primary degree by default:
            obj.natural_degree = obj.primary_degree
            # unless this is a secondary chord:
            if obj.secondary_numeral is not None:
                # get the numeric value of the secondary numeral:
                obj.secondary_degree, sec_acc, sec_mod = obj._parse_numeral_string(obj.secondary_numeral)

                # but check that secondary numeral cannot contain accidentals or modifiers:
                assert sec_acc == 0, "secondary numeral cannot contain accidentals"
                if len(sec_mod) > 0:
                    assert sec_mod == [minor_mod], "secondary numeral cannot contain chord modifiers other than minor (representing the minor scale)"
                    obj.secondary_quality = Minor
                else:
                    obj.secondary_quality = Major

                # and use it to modify the natural degree:
                # (this assumes major-scale degree numbering for now)
                secondary_interval_offset = Interval.from_degree(obj.secondary_degree)
                primary_interval_from_tonic = Interval.from_degree(obj.natural_degree)
                major_degree = (primary_interval_from_tonic + secondary_interval_offset).degree
                obj.natural_degree = major_degree
            else:
                obj.secondary_degree = None
                obj.secondary_quality = None

            obj.quality = obj._determine_quality(obj.modifiers)

            # allocate singleton to class attribute instance dict:
            cls.singleton_numerals[name] = obj
            return obj

    @staticmethod
    def _separate_slashes(name):
        """separates out slashed parts of the init name into scale numeral,
        inversion, and secondary numeral, for example such that name='IV/1/V' returns:
        scale_numeral='IV', inversion=1, secondary_numeral='V'"""

        slashed_parts = name.split('/')
        if len(slashed_parts) == 1: # simple numeral, no inversion or secondary tonicisation
            numeral = slashed_parts[0]
            inversion = 0
            secondary_numeral = None
        elif len(slashed_parts) == 2: # either an inversion or a secondary chord
            left, right = slashed_parts
            if right.isnumeric():
                # seems to be an inversion
                numeral, inversion = left, right
                secondary_numeral = None
            elif parsing.begins_with_roman_numeral(right):
                # seems to be a secondary chord
                inversion = 0
                numeral, secondary_numeral = left, right
            else:
                raise ValueError(f'RomanNumeral did not understand slashed component that seems to be neither an inversion nor a secondary key: {right}')
        elif len(slashed_parts) == 3: # assume both!
            left, mid, right = slashed_parts
            numeral = left
            if mid.isnumeric():
                # middle part is the inversion
                assert parsing.begins_with_roman_numeral(right)
                inversion = mid
                secondary_numeral = right
            elif right.isnumeric():
                # right part is the inversion
                assert mid.isnumeric(), f"Received multiple slashes in ScaleChord init and expected the middle part to be an inversion, but was: {mid}"
                numeral, inversion, secondary_numeral = left, mid, right
            else:
                raise ValueError('Invalid slashed input to RomanNumeral - three components, of which more than one denotes an inversion')
        else:
            raise ValueError(f'Too many slashes ({len(slashed_parts)-1}) in ScaleChord name: {numeral}')

        return numeral, int(inversion), secondary_numeral

        # # recursive function call to understand the tonicised chord:
        # secondary_degree, secondary_quality_str = reduce_aliases(numeral, parsing.progression_aliases)[0]
        # secondary_quality = Quality.from_cache(name=secondary_quality_str)
        # secondary_scale = MajorScale if secondary_quality.major else MinorScale

    @staticmethod
    def _parse_numeral_string(numeral, ignore_alteration=False, return_chord=False):
        """given a (string) roman numeral, in upper or lower case,
        with a potential chord modifier at the end,
        parse into a (degree, AbstractChord) tuple, where degree is an int between 1-7.

        also understands slashes as either inversions or secondary chords or both.

        if return_chord is True, returns the AbstractChord object itself.
            if False, returns a list of the ChordModifiers needed to initialise it."""

        if ignore_alteration and parsing.is_accidental(numeral[0]):
            # if required, disregard accidentals in the start of this degree, like bIII -> III
            numeral = numeral[1:]

        out = reduce_aliases(numeral, parsing.progression_aliases)
        assert isinstance(out[0], tuple), f"expected an (int, acc, qual) tuple but got: {out[0]}" # an integer, accidental, quality tuple
        deg, acc, quality_str = out[0]
        quality = Quality(quality_str)

        modifiers = []
        inversion = 0

        if quality.minor:
            modifiers.append(minor_mod)

        if len(out) > 1: # got one or more additional modifiers as well
            rest = ''.join(out[1:])

            # inversion detection is legacy code from an earlier design
            # but left here just in case:
            rest_inv = rest.split('/')
            if len(rest_inv) > 1:
                assert len(rest_inv) == 2 # chord part and inversion part
                rest, inversion = rest_inv[0], int(rest_inv[1])

            if len(rest) > 0:
                rest_mods = parse_chord_modifiers(rest, catch_duplicates=True)
                modifiers.extend(rest_mods)

        if return_chord:
            chord = AbstractChord.from_cache(modifiers=modifiers, inversion=inversion)
            return deg, acc, chord
        else:
            return deg, acc, modifiers

    @staticmethod
    def _determine_quality(modifiers):
        """determines the 'quality' of this numeral, for the purposes of deciding
        whether it is upper or lower case, depending on the modifiers supplied"""
        # determine the 'quality' of this numeral, for upper/lowercase:
        quality = None
        # if any indeterminate-quality modifiers are in this numeral, it is ind now:
        for m in modifiers:
            if m.quality.indeterminate:
                quality = Ind
                break
        # otherwise, it could be minor:
        if quality is None:
            if minor_mod in modifiers:
                quality = Minor
            else:
                quality = Major
        return quality


    @staticmethod
    def _integer_to_prefix(integer, quality=None, accidental_value=0):
        # recast quality arg to Quality object:
        if quality is None:
            quality = Major
        elif isinstance(quality, (str, int)):
            quality = Quality(quality)
        if isinstance(quality, Quality):
            if not quality.major and (quality.major_ish or quality.perfect):
                # indeterminate quality gets uppercase by default
                quality = Major
            elif not quality.minor and quality.minor_ish:
                quality = Minor
        else:
            raise TypeError(f"'quality' arg must be Quality object, or object that casts to Quality")

        if accidental_value != 0:
            acc_str = parsing.preferred_accidentals[accidental_value]
        else:
            acc_str = ''

        if quality.major:
            prefix_str = acc_str + parsing.numerals_roman[integer].upper()
        else:
            prefix_str = acc_str + parsing.numerals_roman[integer].lower()

        return prefix_str


    @staticmethod
    def from_integer(integer, quality=None, accidental_value=0, inversion=0, modifiers=None):
        """alternative constructor method for integer input, with optional
        quality and accidental_value arguments. (default major and natural respectively)"""
        # # just cast to string and initialise as that:
        # prefix = RomanNumeral._integer_to_prefix(integer, quality, accidental_value)
        # return RomanNumeral(prefix)
        # # more efficient constructor that skips string parsing:
        obj = object.__new__(RomanNumeral)
        if quality is None:
            # major by default
            quality = Major
        elif isinstance(quality, str):
            quality = Quality(quality)

        # assign attributes:
        obj.primary_numeral = RomanNumeral._integer_to_prefix(integer, quality, 0)
        obj.accidental = accidental_value
        obj.inversion = inversion
        obj.quality = quality
        obj.natural_degree = obj.primary_degree = integer

        # this constructor doesn't allow for secondary attributes:
        obj.secondary_numeral = obj.secondary_degree = obj.secondary_quality = None

        # cast modifiers if needed:
        obj.modifiers = [minor_mod] if quality.minor else []
        if modifiers is not None:
            if not isinstance(modifiers, (list, tuple)):
                modifiers = [modifiers]
            for mod in modifiers:
                if not isinstance(mod, ChordModifier):
                    mod = ChordModifier(mod)
                if mod != minor_mod: # minor modifier is already included
                    obj.modifiers.append(mod)

        # finish construction:
        return obj

    @staticmethod
    def from_chord(chord, natural_degree=None, accidental_value=None):
        """alternative constructor method for a Chord input.
        natural_degree is required for an AbstractChord or Chord input,
        but it can be inferred from a ScaleChord or KeyChord."""
        if natural_degree is None:
            # auto detect degree
            from .scales import ScaleChord
            from .keys import KeyChord
            assert type(chord) in (ScaleChord, KeyChord), "must provide natural_degree for RomanNumeral constructor from non-scale/key chord"
            natural_degree = chord.root_degree

        if natural_degree == int(natural_degree):
            integer_degree = int(natural_degree)
            if accidental_value is None:
                accidental_value = 0
        else:
            # float degrees are rounded up by default
            assert accidental_value != 0, "Conflicting accidental_value arg to RomanNumeral.from_chord constructor"
            if accidental_value is None:
                # round up by default, i.e. 2.5 is interpreted as bIII
                accidental_value = -1

            if accidental_value == -1:
                integer_degree = int(ceil(natural_degree))
            elif accidental_value == 1:
                integer_degree = int(floor(natural_degree))

        prefix = RomanNumeral._integer_to_prefix(integer_degree, chord.quality, accidental_value)
        suffix = chord.suffix
        # special case: omit solitary 'm'
        if suffix[0] == 'm':
            suffix = suffix[1:]
        # now just initialise from string:
        return RomanNumeral(prefix + suffix)

    def __add__(self, other):
        """adding a roman numeral with an int transposes the numeral
        up by that many degrees"""
        if isinstance(other, int):
            # return new numeral with all the same attributes
            # except primary degree is shifted up:
            new_degree = self.natural_degree + other
            # mod to range (1,7):
            new_degree = ((new_degree - 1) % 7) + 1
            return self.from_integer(new_degree, self.quality, self.accidental, self.inversion, self.modifiers)
        else:
            raise TypeError(f'addition not defined between RomanNumeral and {type(other)}')

    def __sub__(self, other):
        if isinstance(other, int):
            # just addition with the negation:
            return self + (-other)
        else:
            raise TypeError(f'subtraction not defined between RomanNumeral and {type(other)}')


    @property
    def degree(self):
        """a RomanNumeral's degree is a ScaleDegree object if it does not have an accidental,
        or a float (multiple of 0.5) if accidental."""
        if self.accidental == 0:
            from .scales import ScaleDegree
            return ScaleDegree(self.natural_degree)
        else:
            deg = self.natural_degree + (self.accidental / 2)
            deg = round(deg, 1) # to e.g. 2.5, avoid floating point errors
            return deg

    @cached_property
    def chord(self):
        """returns the AbstractChord associated with this numeral's modifiers"""
        return AbstractChord.from_cache(modifiers=self.modifiers)

    def get_intervals_from_tonic(self, scale='major'):
        """returns the intervals from tonic corresponding to the
        chord that this RomanNumeral represents and its position
        in the scale (assuming major numerals by default)"""

        scale_chord = self.in_scale(scale)
        chord_intervals = scale_chord.intervals_from_tonic
        return chord_intervals

    def in_scale(self, scale=None):
        """interprets this numeral with respect to a scale and returns
        the corresponding ScaleChord"""

        base_chord = AbstractChord.from_cache(modifiers=self.modifiers,
                                              inversion=self.inversion)

        # if scale is not given, guess it:
        if scale is None:
            from .scales import infer_chord_scale
            scale = infer_chord_scale(self.degree, self.quality)

        # catch a special case: have we been given flat degrees (like bVI) in a minor key,
        # which cannot be found because e.g. the minor VI is already flat?
        base_degree = self.degree
        if isinstance(self.degree, float) and self.degree not in scale.fractional_degree_intervals:
            log(f'Tried to get altered root from: {self} but that altered root is already in scale')
            base_degree = self.natural_degree

        # call chord constructor from scale (using integer, so this doesn't get livelocked)
        return base_chord.in_scale(scale, degree=base_degree)


    def in_key(self, key):
        from .keys import Key
        if not isinstance(key, Key):
            key = Key(key)
        scale_chord = self.in_scale(key.scale)
        return scale_chord.on_tonic(key.tonic)

    @cached_property
    def prefix(self):
        """returns the prefix for this numeral, which consists of the accidental
        and the roman numeral itself.
        for example, the numeral bIIIsus2's prefix is ♭III."""
        parts = []
        # first, choose an accidental if needed:
        if self.accidental != 0:
            acc_part = parsing.preferred_accidentals[self.accidental]
            parts.append(acc_part)

        # next, decide whether the numeral should be upper or lowercase:
        if self.quality.major_ish:
            uppercase = True
        elif self.quality.minor_ish:
            uppercase = False
        elif self.quality.indeterminate:
            # ScaleRomanNumeral can override this for Ind chords to be more intelligent
            # but in the RomanNumeral class that doesn't know what scale it's in,
            # we just presuppose ind chords are uppercase by default:
            uppercase = True

        if uppercase:
            num_part = parsing.numerals_roman[self.primary_degree].upper()
        else:
            num_part = parsing.numerals_roman[self.primary_degree].lower()
        parts.append(num_part)

        return ''.join(parts)

    @cached_property
    def suffix(self):
        """returns the abbreviated suffix for the chord type corresponding to this numeral.
        for example, the numeral viidim's suffix is: ° """
        relevant_mods = [mod for mod in self.modifiers if mod != minor_mod]
        if len(relevant_mods) == 0:
            return '' # empty suffix
        elif len(relevant_mods) == 1:
            # naming a chord is easy if it has exactly 1 modifier
            mod = relevant_mods[0]
            mod_str = ''.join(reduce_aliases(mod.name, parsing.modifier_marks))
            return mod_str
        else:
            # otherwise we must instantiate the chord itself to use its logic.
            # this includes collapsing the (maj7, add9) sequence into (maj9),
            # as well as translating chord suffix strings into shortened superscripts etc.
            mod_str = ''.join(reduce_aliases(self.chord.suffix, parsing.modifier_marks))
            return mod_str

    def __eq__(self, other):
        if isinstance(other, RomanNumeral):
            return (    (self.primary_degree == other.primary_degree)
                    and (self.accidental == other.accidental)
                    and (self.quality == other.quality)
                    and (self.inversion == other.inversion)
                    and (self.secondary_degree == other.secondary_degree)
                    and (self.modifiers == other.modifiers)
                   )

    def __hash__(self):
        return hash(repr(self))

    def __str__(self):
        """prints this roman numeral as it would be written"""
        parts = [self.prefix, self.suffix]

        # # first, choose an accidental if needed:
        # if self.accidental != 0:
        #     acc_part = parsing.preferred_accidentals[self.accidental]
        #     parts.append(acc_part)
        #
        # # next, decide whether the numeral should be upper or lowercase:
        # if self.quality.major_ish:
        #     uppercase = True
        # elif self.quality.minor_ish:
        #     uppercase = False
        # elif self.quality.indeterminate:
        #     # ScaleRomanNumeral can override this for Ind chords to be more intelligent
        #     # but in the RomanNumeral class that doesn't know what scale it's in,
        #     # we just presuppose ind chords are uppercase by default:
        #     uppercase = True
        #
        # if uppercase:
        #     num_part = parsing.numerals_roman[self.primary_degree].upper()
        # else:
        #     num_part = parsing.numerals_roman[self.primary_degree].lower()
        # parts.append(num_part)


        # turn each ChordModifier in this numeral into a string,
        # preferentially superscript shorthands like ° where available,
        # but ignore the minor modifier specifically because it's already accounted for:

        # relevant_mods = [mod for mod in self.modifiers if mod != minor_mod]
        # if len(relevant_mods) <= 1:
        #     # naming a chord is easy if it has 0 or 1 modifiers:
        #     for mod in relevant_mods:
        #         mod_str = ''.join(reduce_aliases(mod.name, parsing.modifier_marks))
        #         parts.append(mod_str)
        # else:
        #     # otherwise we must instantiate the chord itself to use its logic.
        #     # this includes collapsing the (maj7, add9) sequence into (maj9),
        #     # as well as translating chord suffix strings into shortened superscripts etc.
        #     abs_chord = AbstractChord.from_cache(modifiers=self.modifiers)
        #     chord_part = ''.join(reduce_aliases(abs_chord.suffix, parsing.modifier_marks))
        #     parts.append(chord_part)

        # then, if this is an inversion, add that too:
        if self.inversion != 0:
            parts.append(f'/{self.inversion}')

        # finally, if this is a secondary chord, add the secondary numeral too:
        if self.secondary_numeral is not None:
            if self.secondary_quality.major:
                secondary_num_part = parsing.numerals_roman[self.secondary_degree].upper()
            elif self.secondary_quality.minor:
                secondary_num_part = parsing.numerals_roman[self.secondary_degree].lower()
            parts.append(secondary_num_part)

        # combine them all to form the finished roman numeral string:
        return ''.join(parts)

    def __repr__(self):
        """same as str, but with brackets around the output"""
        lb, rb = self._brackets
        return lb + str(self) + rb

    _brackets = settings.BRACKETS['RomanNumeral']



RN = Roman = RomanNumeral # convenience alias

class NumeralList(list):
    def __init__(self, *items):
        valid_numerals = []
        if len(items) == 1:
            if isinstance(items[0], str):
                # been passed a single string as input, split it into a list:
                items = auto_split(items[0])
            elif isinstance(items[0], (list, tuple)):
                # been passed an iterable as single input, unpack it:
                items = items[0]

        # now 'items' is guaranteed to be a list of numerals or numeral strings
        valid_numerals = []
        for item in items:
            if not isinstance(item, RomanNumeral):
                item = RomanNumeral(item)
            valid_numerals.append(item)

        # initialise as list:
        super().__init__(valid_numerals)

    # outer brackets for this container class:
    _brackets = settings.BRACKETS['NumeralList']


    def __str__(self, brackets=True):
        # return f'𝄃{super().__repr__()}𝄂'
        numeral_names = [str(rn) for rn in self]
        if brackets:
            lb, rb = self._brackets
        else:
            lb = rb = ''
        sep_char = ' - '
        return f'{lb}{sep_char.join(numeral_names)}{rb}'

    def __repr__(self):
        return str(self)

    def get_intervals_from_tonic(self, scale='major', **kwargs):
        """returns the intervals of the chords in this NumeralList
        relative to the tonic of their scale (implied major by default),
        as an IntervalList (but with optional kwargs
        passed to IntervalList constructor)"""
        all_intervals = IntervalList([])
        for rn in self:
            all_intervals.extend(rn.get_intervals_from_tonic(scale=scale))
        return all_intervals

Numerals = NumeralList
