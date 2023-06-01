### this progressions module is incomplete, very WIP at the moment

from .intervals import Interval
from .chords import Chord, AbstractChord
from .qualities import Major, Minor, Perfect, Diminished, parse_chord_qualifiers, ChordQualifier
from .scales import Scale, Subscale, scale_name_intervals, NaturalMajor, NaturalMinor, MelodicMinor, HarmonicMinor, MelodicMajor, HarmonicMajor
from .keys import Key, Subkey, matching_keys, most_likely_key
from .util import reduce_aliases, auto_split, check_all, reverse_dict, log
from .parsing import roman_numerals, numerals_roman
from . import parsing

from collections import Counter

# import numpy as np


# IDEA / TO DO: model movements not just of chord roots, but of _every_ note in triad/tetrad chords,
# to capture perfect/imperfect cadence based on bass/soprano voicings of chords etc.





### TBI: progression completion feature that incorporates T-S-D-T progression logic:
# I is tonic
# V and viio are dominant
# ii and IV are subdominant
# vi is pre-subdominant
# syntactic progressions go from tonic to subdominant to dominant to tonic
# the first subdominant in a T-S-D-T progression can optionally be preceded by a pre-subdominant
# "It is allowable to move between functionally identical chords only
#   when the root of the first chord lies a third above the root of the
#   second." (i.e. IV-ii, viio-V)
# "Dominant chords can also progress to vi as part of a 'deceptive' progression."

# c.f. root-motion theory (Meeus):
# root motion by fifth is primary: descending-fifth motion represents the
# prototypical “dominant” progression, while ascending-fifth motion is prototypically
# “subdominant.” Meeus additionally allows two classes of “substitute” progression:
# rootprogression by third can “substitute” for a fifth-progression in the same direction; and
# root-progression by step can “substitute” for a fifth-progression in the opposite direction



# functions of (major?) scale chords, indexed by interval (not degree)
scale_functions = { 0: "T", # 1st, tonic
                    2: "ST", # 2nd, supertonic
                    3: "M", # m3, mediant
                    4: "M", # M3, mediant
                    5: "S", # 4th, subdominant
                    7: "D", # 5th, dominant
                    8: "SM", # m6, submediant
                    9: "SM", # M6, submediant
                    10: "ST", # m7, subtonic
                    11: "L", # M7, leading tone
                    }

scale_function_names = {0: "tonic", # 1st
                        2: "supertonic", # 2nd
                        3: "mediant", # 3rd (minor)
                        4: "mediant", # 3rd (major)
                        5: "subdominant", # 4th
                        7: "dominant", # 5th
                        8: "submediant", # 6th (minor)
                        9: "submediant", # 6th (major)
                        10: "subtonic", # 7th (minor)
                        11: "leading tone", # 7th (major)
                        }


qualifier_marks = {'dim': '°',
                   'hdim': 'ø',
                   'aug': '+',
                   'maj7': 'Δ⁷',
                   '5': '⁵',
                   '7': '⁷',
                   '9': '⁹',
                   '11': '¹¹',
                   '13': '¹³',
                   'sus': 's'}

roman_degree_chords = {}
# render as an alias dict linking numerals to major/minor qualities:
for arabic,roman in numerals_roman.items():
    roman_degree_chords[roman] = (arabic, Major)
    roman_degree_chords[roman.lower()] = (arabic, Minor)
# and the reverse mapping, for SDC.__repr__:
degree_chords_roman = reverse_dict(roman_degree_chords)

progression_aliases = dict(roman_degree_chords)
# kludge: we have to specifically ignore 'dim' when reading roman numerals,
# because it contains a roman numeral ('i')
progression_aliases['dim'] = 'dim'

def parse_roman_numeral(numeral):
    """given a (string) roman numeral, in upper or lower case,
    with a potential chord qualifier at the end,
    parse into a (degree, AbstractChord) tuple, where degree is an int between 1-7"""
    out = reduce_aliases(numeral, progression_aliases)
    assert isinstance(out[0], tuple) # an integer, quality tuple
    deg, quality = out[0]

    qualifiers = []

    # should we should treat the quality (if minor) as a qualifier in its own right?
    if quality.minor:
        quality_qualifier = ChordQualifier('minor')
        qualifiers.append(quality_qualifier)

    if len(out) > 1: # got one or more additional qualifiers as well
        rest = ''.join(out[1:])
        quals = parse_chord_qualifiers(rest)
        qualifiers.extend(quals)

    chord = AbstractChord(qualifiers=qualifiers)

    return deg, chord


class DegreeMovement:
    """class representing (unsigned) movement between two notes,
    intended to model the movement of chord roots in a progression"""
    def __init__(self, start, end, scale=None):
        """accepts one of two input schemes:
            1. 'start' and 'end' should both be integers between 1 and 7,
                denoting the root degrees of the starting and ending scale chords.
            2. 'start' should be an integer, 'direction' should be either "D" or "S",
                and degree should be one of 2, 3, or 5.

            scale can optionally be provided, which matters only for the
            intervallic distance (not the scale-degree distance) involved
            in this movement. otherwise those attributes are left un-set."""

        if scale is not None:
            if isinstance(scale, str):
                # instantiate Scale object if it is not already instantiated
                scale = Scale(scale)
            assert isinstance(scale, Scale), f"DegreeMovement expected a Scale object, or string that casts to Scale, but got: {type(scale)}"
        self.scale = scale

        # if end is not None:
        assert (start in range(1,8)) and (end in range(1,8))
        self.start, self.end = start, end

        self._set_degree_distances()
        if scale is not None:
            self._set_interval_distances(scale)
        self._set_harmonic_functions()

    def _set_degree_distances(self):
        if self.start > self.end:
            # more down than up
            self.up = 7-(self.start - self.end)
            self.down = self.start - self.end
        elif self.start < self.end:
            # more up than down
            self.up = self.end - self.start
            self.down = 7-(self.end - self.start)
        else:
            self.up = self.down = 0

    def _set_interval_distances(self, scale_obj):
        self.start_iv, self.end_iv = (scale_obj.degree_intervals[d] for d in [self.start, self.end])
        if self.start > self.end:
            # more down than up
            self.iv_up = 12-(self.start_iv - self.end_iv)
            self.iv_down = self.start_iv - self.end_iv
        elif self.start < self.end:
            # more up than down
            self.iv_up = self.end_iv - self.start_iv
            self.iv_down = 12-(self.end_iv - self.start_iv)
        else:
            self.iv_up = self.iv_down = 0

    def _set_harmonic_functions(self):
        self.descending_fifth = self.down == 4
        self.descending_fourth = self.down == 3
        # self.function = ('primary ' if self.primary else 'substitute ') + ('dominant' if self.dominant else 'subdominant')

        # the 'size' of the movement: 2 to 1 has less magnitude than 5 to 1, but the same as 7 to 1
        self.magnitude = min([self.up, self.down])

        # experimental chord function flags: (based on major scale harmony theory, but should apply to minor as well?)
        self.dominant = self.down in {4,2} or self.up in {3,1} # descending by fifth or third
        self.subdominant = self.down in {3,1} or self.up in {4,2}
        self.primary = 4 in {self.down, self.up}
        self.substitute = not self.primary

        if self.scale is not None:
            self.start_function = scale_functions[self.start_iv]
            self.end_function = scale_functions[self.end_iv]

        self.resolved = (self.end == 1) and (self.start != 1) # maybe?
        self.hanging = self.end_function in {"D", "L"}

        self.authentic_cadence = (self.start in {5,7} and self.end == 1)
        self.authentic_half_cadence = (self.start in {1, 2, 4, 6}) and (self.end == 5)
        self.plagal_cadence = (self.start == 4 and self.end == 1)
        self.plagal_half_cadence = (self.start in {1, 2, 5, 6}) and (self.end == 4) # does this follow the same rules as authentic half cadences?
        self.deceptive_cadence = (self.start == 5) and (self.end not in {5,1})

    @property
    def cadence(self):
        if self.authentic_cadence:
            return 'authentic cadence'
        elif self.authentic_half_cadence:
            return 'authentic half cadence'
        elif self.plagal_cadence:
            return 'plagal cadence'
        elif self.plagal_half_cadence:
            return 'plagal half cadence'
        elif self.deceptive_cadence:
            return 'deceptive cadence'
        else:
            return False

    @property
    def cadence_short_name(self):
        if self.cadence:
            # capitalise first character of the words in the cadence name:
            words = self.cadence.split(' ')
            chars = [w[0].upper() for w in words]
            return ''.join(chars)
        else:
            return ''

    @property
    def function(self):
        """returns a string that describes the function of this DegreeMovement as a root movement,
        and names the cadence if this is a cadence that we know about."""
        func_str = []
        # dominant/subdominant direction:
        func_str.append(('primary ' if self.primary else 'substitute ') + ('dominant' if self.dominant else 'subdominant'))
        # cadence:
        if self.cadence:
            func_str.append(f'({self.cadence})')
        # tension/resolution:
        if self.hanging:
            func_str.append('(hanging)')
        return ' '.join(func_str)

    @property
    def function_char(self):
        if self.dominant:
            return 'D'
        elif self.subdominant:
            return 'S'
        else:
            return '='

    @property
    def _movement_marker(self):
        return '⇾ ' # '>'

    @property
    def _up_arrow(self):
        return '↿' #'↑' # '⇧'

    @property
    def _down_arrow(self):
        return '⇃' # '↓' # '⇩'

    @property
    def direction_str(self):
        if self.up == 0: # no direction
            return ' 0'
        if self.descending_fifth or self.descending_fourth:
            direction_char = self._down_arrow
        else:
            direction_char = self._down_arrow if self.down < self.up else self._up_arrow
        distance_char = 5 if self.magnitude == 3 else (self.magnitude+1)
        return f'{direction_char}{distance_char}'

    @property
    def degrees(self):
        return f'{self.start}{self._movement_marker}{self.end}'

    def __str__(self):
        return(f'[{self.function_char}]{self.degrees}:{self.direction_str}')

    def __repr__(self):
        return str(self)


class ChordList(list):
    """container for multiple Chord objects"""
    def __init__(self, *items):
        if len(items) == 1:
            arg = items[0]
            if isinstance(arg, str):
                # could be a dash-separated string of chord names or something, try auto-split:
                items = auto_split(arg, allow='°øΔ♯♭♮+𝄫𝄪#')
            else:
                assert isinstance(arg, (list, tuple)), f"Expected list or tuple of chord-like objects, but got single non-list/tuple arg: {type(arg)}"
                items = arg
        assert len(items) > 1, "ChordList must contain at least two Chords"

        valid_chords = []
        for c in items:
            # if is chord: add it to list
            if isinstance(c, Chord):
                valid_chords.append(c)
            elif isinstance(c, AbstractChord):
                valid_chords.append(c)
            # if is string: try parsing as chord name
            elif isinstance(c, str):
                if parsing.begins_with_valid_note_name(c):
                    # chord
                    valid_chords.append(Chord(c))
                else:
                    valid_chords.append(AbstractChord(c))

        # initialise as list:
        super().__init__(valid_chords)

    # outer brackets for this container class:
    @property
    def _brackets(self):
        return '𝄃', ' 𝄂'
        # return '╟', '╢'
        # return '𝄆', '𝄇'

    def __str__(self):
        # return f'𝄃{super().__repr__()}𝄂'
        lb, rb = self._brackets
        return f'{lb} {" ".join([n.name for n in self])} {rb}'

    def __repr__(self):
        return str(self)

    def append(self, c):
        """appends an item to self, ensuring it is a Chord or AbstractChord"""
        if isinstance(c, Chord):
            super().append(c)
        elif isinstance(c, AbstractChord):
            super().append(c)
        # if is string: try parsing as chord name
        elif isinstance(c, str):
            if parsing.begins_with_valid_note_name(c):
                # chord
                super().append(Chord(c))
            else:
                super().append(AbstractChord(c))
        else:
            raise TypeError(f'Tried to append to ChordList, expected Chord or str but got: {type(other)}')

    def __add__(self, other):
        # if other is a str, try and parse it as a chord:
        if isinstance(other, str):
            if parsing.begins_with_valid_note_name(other):
                other = Chord(other)
            else:
                other = AbstractChord(other)

        # appending a new chord:
        if isinstance(other, Chord):
            new_chords = list(self) + [other]
            return ChordList(new_chords)

        # concatenation of chordlists:
        elif isinstance(other, (tuple, list, ChordList)):
            # if this is a list or tuple, needs to be a list or tuple of chords or strings that cast to chords:
            if type(other) in {tuple, list}:
                other = ChordList(other)
            new_chords = list(self) + list(other)
            return ChordList(new_chords)

        # transpose every chord in this list by an interval:
        elif isinstance(other, (int, Interval)):
            new_chords = [c + int(other) for c in self]
            return ChordList(new_chords)

        else:
            raise TypeError(f'ChordList.__add__ not defined for type: {type(other)}')

    def abstract(self):
        """returns a new ChordList that is purely the AbstractChords within this existing ChordList"""
        abs_chords = [c.abstract() if (type(c) == Chord)  else c  for c in self]
        assert check_all(abs_chords, 'eq', AbstractChord)
        return ChordList(abs_chords)

    def matching_keys(self, *args, **kwargs):
        """just wraps around keys.matching_keys module function"""
        return matching_keys(self, *args, **kwargs)

    def root_degrees_in(self, key):
        if isinstance(key, str):
            key = Key(key)
        assert isinstance(key, Key), f"key input to ChordList.as_numerals must be a Key or string that casts to Key, but got: {type(key)})"
        root_intervals_from_tonic = [c.root - key.tonic for c in self]
        root_degrees = [key.interval_degrees[iv] for iv in root_intervals_from_tonic]
        return root_degrees

    def as_numerals_in(self, key, sep=' ', qualifiers=True):
        root_degrees = self.root_degrees_in(key)
        degree_chords = zip(root_degrees, self)
        numerals = [numerals_roman[d]  if c.quality.major_ish else numerals_roman[d].lower()  for d,c in degree_chords]
        # add suffixes: (we ignore the 'm' suffix because it is denoted by lowercase instead)
        if qualifiers:
            suffix_list = [c.suffix if c.suffix != 'm' else '' for c in self]
            roman_chords_list = [f'{numerals[i]}{suffix_list[i]}' for i in range(len(self))]
            # turn suffix qualifiers into superscript marks etc. where possible:
            roman_chords_list = [''.join(reduce_aliases(r, qualifier_marks)) for r in roman_chords_list]
        else:
            roman_chords_list = [f'{numerals[i]}' for i in range(len(self))]
        if sep is not None:
            roman_chords_str = sep.join(roman_chords_list)
            return roman_chords_str
        else:
            # just return the raw list, instead of a sep-connected string
            return roman_chords_list

    @property
    def progression(self):
        return ChordProgression(self)

    def find_key(self):
        """lightweight matching_keys reimplementation"""
        note_counts = Counter()

# alias for easy access:
Chords = ChordList

class Progression:
    """A theoretical progression between AbstractChords in a particular scale,
    initialised as list: e.g. Progression(['I', 'IV', 'iii', 'V'])
    or as string separated by dashes, e.g.: Progression('I-IV-iii-V')"""
    def __init__(self, *numerals, scale=None, chords=None, ignore_conflicting_case=False):
        """accepts one of three input schemes:
        1. 'numerals' input is a list (or demarcated string) of upper/lower-case roman numerals denoting scale chords,
            with optional 'scale' parameter.
                a. if scale is None, we automatically determine the scale from the case/quality of the chord numerals.
                b. if scale is provided, and 'ignore_conflicting_case' is False, we parse chords according to their case/quality,
                    even if they conflict with the scale given.
                c. if scale is provided, and ignore_conflicting_case is True, we ignore the case/quality of the chord numerals
                    and instantiate chords solely according to their root degree and qualifiers, in the scale given.
                        in either case (?), if 'auto_qualify' is True, we also qualify chords automatically as required by the scale,
                        for example making the 7-chord diminished in major.
        2. 'numerals' input is a list of integers denoting root degrees of chords, and 'scale' is a Scale object (or string that casts to Scale),
            in which case we allocate major/minor quality to the chords based on the scale provided.
        3. 'numerals' input is a list of integers denoting root degrees of chords, and 'chords' is an iterable of AbstractChord objects
            (or strings that cast to AbstractChords), in which case we automatically determine the scale from the qualities of the chords.
            """

        # unpack tuple arg:
        if len(numerals) == 1:
            numerals = numerals[0]

        if isinstance(numerals, str):
            split_numerals = auto_split(numerals, allow='°øΔ♯♭♮+𝄫𝄪#')
            assert len(split_numerals) > 1, f"Expected a string of roman numerals separated by dashes (or other obvious separator), but got: {numerals[0]}"
            numerals = split_numerals
        # is now an iterable of roman numeral strings OR of integers

        if check_all(numerals, 'isinstance', str):
            # roman numeral strings
            # which we parse into AbstractChords based on their case and suffixes
            base_degree_chords = [parse_roman_numeral(n) for n in numerals] # degree, AbstractChord tuples
            self.root_degrees = [d[0] for d in base_degree_chords]

            log(f'Base (unscaled) degree chords:')
            for r,c in base_degree_chords:
                log(f'{r}: {c}')

            if scale is None:
                # build chords as specified from numerals and detect scale afterward
                self.chords = ChordList([d[1] for d in base_degree_chords])
                self.scale = self._detect_scale(base_degree_chords)

            else:
                # scale is provided, so we simply instantiate it
                # and, if needed, check degree chords against it
                if isinstance(scale, str):
                    scale = Scale(scale)
                assert type(scale) in [Scale, Subscale]
                self.scale = scale
                scale_chords = ChordList([self.scale.chord(d) for d in self.root_degrees])

                if ignore_conflicting_case:
                    # ignore case (but not qualifiers) of roman numeral chords provided
                    # and instantiate them from scale instead:
                    self.chords = scale_chords
                    log(f'Ignoring conflicting case in chord numerals:')
                    for (d, bc), sc in zip(base_degree_chords, self.chords):
                        if bc == sc:
                            log(f'{d}: Provided {bc.short_name:{5}}, computed {sc.short_name:{5}}')
                        else:
                            log(f'{d}: Provided {bc.short_name:{5}}, computed {sc.short_name:{5}} [CONFLICT, using computed scale chord]')

                else:
                    # do not ignore case; instantiate chords in provided case
                    self.chords = ChordList([c for d,c in base_degree_chords])
                    log(f'Ignoring conflicting case in chord numerals:')
                    for (d, bc), sc in zip(base_degree_chords, scale_chords):
                        if bc == sc:
                            log(f'{d}: Provided {bc.short_name:{5}}, computed {sc.short_name:{5}}')
                        else:
                            log(f'{d}: Provided {bc.short_name:{5}}, computed {sc.short_name:{5}} [CONFLICT, using provided chord]')
                print()

        elif check_all(numerals, 'isinstance', int):
            assert scale is not None, f'Progression chords given as integers but scale arg not provided'
            if isinstance(scale, str):
                scale = Scale(scale)
            assert type(scale) in [Scale, Subscale]
            self.scale = scale
            self.root_degrees = numerals
            if chords is None:
                # compute scale chords:
                self.chords = ChordList([self.scale.chord(d) for d in self.root_degrees])
            else:
                # use the abstractchords we have been given (and cast them to abstract)
                self.chords = ChordList(chords).abstract()

        else:
            raise ValueError(f'Progression init ended up with an iterable of mixed types, expected all ints or all strings but got: {numerals}')

        self.abstract_chords = chords # true for Progression class, not for ChordProgression

        # scaledegree, chord pairs:
        self.degree_chords = [(self.root_degrees[i], self.chords[i]) for i in range(len(self))]

        self.numerals = self.as_numerals(sep=None)

        # note movements between each chord root:
        self.chord_root_intervals_from_tonic = [self.scale.degree_intervals[d] for d in self.root_degrees]
        self.root_movements = [DegreeMovement(self.root_degrees[i], self.root_degrees[i+1], scale=self.scale) for i in range(len(self)-1)]




    # TO DO: replace with a (simpler?) case statement?
    def _detect_scale(self, degree_chords):
        """from a provided list of chord tuples of form: (root_degree, AbstractChord)
        determine whether they most likely correspond to a major or minor scale by summing evidence
        and returns the resulting scale as an object"""
        major_evidence, minor_evidence = 0, 0
        for root, chord in degree_chords:
            if root == 1 and chord.quality.major_ish:
                major_evidence += 3
            elif root == 1 and chord.quality.minor_ish:
                minor_evidence += 3
            elif chord.quality.major:
                if root in {4,5}:
                    major_evidence += 1
                elif root in {2,3,6}:
                    minor_evidence += 1
            elif chord.quality.minor:
                if root in {4,5}:
                    minor_evidence += 1
                elif root in {3,6,7}:
                    major_evidence += 1
            elif chord.quality.diminished:
                if root == 2:
                    minor_evidence += 2
                elif root == 7:
                    major_evidence += 2
        log(f'For scale chords: {[(r,c.quality) for r,c in degree_chords]}')
        log(f'  Evidence for major scale: {major_evidence}')
        log(f'  Evidence for minor scale: {minor_evidence}')
        if major_evidence >= minor_evidence:
            log(f'    (inferred: natural major scale)\n')
            return NaturalMajor
        else:
            log(f'    (inferred: natural minor scale)\n')
            return NaturalMinor

    @property
    def analysis(self):
        """shows the harmonic functions of the chords in this progression"""
        out = []
        # sloppy for now: should be rolled into a dataframe from the Display module
        num1s, num2s, c1s, c2s, mvs, cads = [], [], [], [], [], []
        for i in range(len(self)-1):
            num1s.append(self.numerals[i])
            num2s.append(self.numerals[i+1])
            c1s.append(self.chords[i].short_name)
            c2s.append(self.chords[i+1].short_name)
            mvs.append(str(self.root_movements[i].direction_str))
            cad = self.root_movements[i].cadence
            cads.append(cad if cad != False else '')
        # determine max string len of each element:
        c1_len = max([len(c) for c in c1s])
        c2_len = max([len(c) for c in c2s])
        mv_len = max([len(mv) for mv in mvs])
        n1_len = max([len(n) for n in num1s])
        n2_len = max([len(n) for n in num2s])

        out = [str(self)]
        for i in range(len(self)-1):
            f = self.root_movements[i].function_char
            arrow = self.root_movements[i]._movement_marker
            d1, c1, d2, c2, mv, cad = self.root_degrees[i], c1s[i], self.root_degrees[i+1], c2s[i], mvs[i], cads[i]
            n1 = num1s[i].lower() if self.chords[i].quality.minor_ish else num1s[i]
            n2 = num2s[i].lower() if self.chords[i+1].quality.minor_ish else num2s[i]
            line = f'[{f}] {n1:{n1_len}}{arrow}{n2:{n2_len}}    {d1}:{c1:{c1_len}}{arrow}{d2}:{c2:{c2_len}}    {mv:{mv_len}}    {cad}'
            out.append(line)
        print ('\n'.join(out))

    def as_numerals(self, sep=' ', check_scale=False):
        numerals = [numerals_roman[d]  if c.quality.major_ish else numerals_roman[d].lower()  for d,c in self.degree_chords]
        # add suffixes: (we ignore the 'm' suffix because it is denoted by lowercase instead)
        suffix_list = [c.suffix if c.suffix != 'm' else '' for c in self.chords]
        roman_chords_list = [f'{numerals[i]}{suffix_list[i]}' for i in range(len(self))]

        if check_scale:
            # annotate chords that are chromatic to the scale with square brackets
            # or, if they are at least in the corresponding harmonic/melodic scale, mark that too:
            if self.scale.suffix in {'m', ''}:
                if self.scale.suffix == 'm':
                    # natural minor scale
                    harmonic_scale = HarmonicMinor
                    melodic_scale = MelodicMinor
                if self.scale.suffix == '':
                    # natural major scale
                    harmonic_scale = HarmonicMajor
                    melodic_scale = MelodicMajor

                belongs_natural = [self.scale.contains_degree_chord(d,c) for d,c in self.degree_chords]

                ## is this needed?
                # but don't allow chords that are built on harmonic/melodic roots:
                root_intervals = [self.scale.degree_intervals[d] for d,c in self.degree_chords]
                belongs_harmonic = [HarmonicMinor.contains_degree_chord(*self.degree_chords[i], degree_interval=root_intervals[i]) for i in range(len(self))]
                belongs_melodic = [MelodicMinor.contains_degree_chord(*self.degree_chords[i], degree_interval=root_intervals[i]) for i in range(len(self))]
                ### (will probably handle chord roots belonging to parallel/neighbouring keys separately)

                # belongs_harmonic = [HarmonicMinor.contains_degree_chord(d,c, for d,c in self.degree_chords]
                # belongs_melodic = [MelodicMinor.contains_degree_chord(d,c for d,c in self.degree_chords]
                new_roman_chords = []
                for i in range(len(roman_chords_list)):
                    orig = roman_chords_list[i]
                    if belongs_natural[i]:
                        new_roman_chords.append(orig)
                    elif belongs_harmonic[i]:
                        # mark first character with combining 'h':
                        new_roman_chords.append(f'{orig[0]}\u036A{orig[1:]}')
                    elif belongs_melodic[i]:
                        # mark first character with combining 'm':
                        new_roman_chords.append(f'{orig[0]}\u036B{orig[1:]}')
                    else:
                        # mark out-of-scale chord with brackets:
                        new_roman_chords.append(f'[{orig}]')
                roman_chords_list = new_roman_chords
            else:
                # non-natural scale: just check raw scale compatibility
                belongs = [self.scale.contains_degree_chord(d,c) for d,c in self.degree_chords]
                roman_chords_list = [f'{roman_chords_list[i]}' if belongs[i]  else f'[{roman_chords_list[i]}]'  for i in range(len(self))]

        # turn suffix qualifiers into superscript marks etc. where possible:
        roman_chords_list = [''.join(reduce_aliases(r, qualifier_marks)) for r in roman_chords_list]
        if sep is not None:
            roman_chords_str = sep.join(roman_chords_list)
            return roman_chords_str
        else:
            # just return the raw list, instead of a sep-connected string
            return roman_chords_list

    def in_key(self, key):
        """returns a ChordProgression with these chords over a specified Key object"""
        # cast to Key object:
        if isinstance(key, str):
            key = Key(key)
        assert isinstance(key, Key)
        key_chords = []
        for d,c in self.degree_chords:
            root = key.degree_notes[d]
            key_chords.append(c.on_root(root))
        return ChordProgression(key_chords, key=key)


    # outer brackets for this container class:
    @property
    def _brackets(self):
        # return '╟', '╢'
        return '𝄆', '𝄇'

    def __len__(self):
        return len(self.root_degrees)

    def __str__(self):
        scale_name = self.scale.name
        if 'natural' in scale_name:
            scale_name = scale_name.replace('natural ', '')
        lb, rb = self._brackets
        return f'Progression:  {lb} {self.as_numerals(check_scale=True)} {rb}  (in {scale_name})'


    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        """progressions are equal to each other if they have the same chords built on the same degrees"""
        return self.degree_chords == other.degree_chords



class ChordMovement:
    """Movement of root and every other chord degree from one to another"""
    def __init__(self, start_chord, end_chord, key):
        self.start_chord = start_chord
        self.end_chord = end_chord
        self.key = key

        order1, order2 = start_chord.order, end_chord.order

        ... # TBI


class ChordProgression(Progression, ChordList):
    """ChordList subclass defined additionally over a specific key"""
    def __init__(self, *chords, key=None):

        if len(chords) == 1:
            chords = chords[0]

        if isinstance(chords, str):
            # if chords is a plain string instead of iterable,
            # try auto splitting:
            chords = auto_split(chords, allow='°øΔ♯♭♮+𝄫𝄪#')

        # iterate through list and cast to chord objectss:
        valid_chords = []
        self.note_count = Counter()

        for item in chords:
            if isinstance(item, Chord): # already a Chord object
                c = item
            elif isinstance(item, str): # string that we try to cast to Chord
                c = Chord(item)
            elif isinstance(item, (list, tuple)): # pair of parameters that we try to cast to Chord
                c = Chord(*item)
            elif isinstance(item, dict):
                # unpack keyword args to cast to chord
                c = Chord(**dict)
            else:
                raise ValueError(f'Expected iterable to contain Chords, or items that can be cast as Chords, but got: {type(item)}')

            valid_chords.append(c)
            self.note_count.update(c.notes)

        self.chords = ChordList(chords)
        self.abstract_chords = [c.abstract() for c in self.chords]

        # detect most likely key:
        if key is None:

            matches = self.chords.matching_keys(return_matches=True, require_tonic=False, upweight_first=True, upweight_last=True)
            ideal_matches = [(c,s) for c,s in matches.items() if s['recall'] == 1.0]
            if len(ideal_matches) == 1:
                # only one good match, so use it
                self.key = ideal_matches[0][0]
            elif len(ideal_matches) >= 2:
                # multiple good matches, see if one has better precision than the other
                max_prec = max([s['precision'] for c,s in ideal_matches])
                best_matches = [(c,s) for c,s in ideal_matches if s['precision'] == max_prec]
                if len(best_matches) == 1:
                    # one of the perfect-recall matches is better than all the others, so use it (probably?)
                    self.key = best_matches[0][0]
                else:
                    # multiple matches that are equally as good,
                    # so look for a cadence-based match around V-I resolutions or something

                    # TBI: use implied resolution to I chord if the progression ends on a V,
                    # and use that ot determine minor/major between candidate matches

                    ### TBI: this is a workaround for now, take the one that matches the first chord
                    found_match = False
                    for match,stats in best_matches:
                        if match.tonic == self.chords[0].root:
                            self.key = match
                            found_match = True
                            break
                    if not found_match:
                        raise Exception('Not yet implemented')

            if len(ideal_matches) == 0:
                # open up and just take the best non-ideal match:
                self.key = list(matches.keys())[0] # TBI, look for cadence resolutions here too
        else:
            self.key = key if isinstance(key, Key) else Key(key)
        # and rip out its scale:
        self.scale = Scale(self.key.scale)

        self.roots = [c.root for c in self.chords]
        self.root_degrees = [self.key.note_degrees[n] for n in self.roots]
        self.degree_chords = [(self.root_degrees[i], self.chords[i]) for i in range(len(self))]

        self.numerals = self.as_numerals(sep=None)

        # note movements between each chord root:
        self.chord_root_intervals_from_tonic = [self.scale.degree_intervals[d] for d in self.root_degrees]
        self.root_movements = [DegreeMovement(self.root_degrees[i], self.root_degrees[i+1], scale=self.scale) for i in range(len(self)-1)]




    def __contains__(self, item):
        if isinstance(item, Chord):
            # efficient lookup by checking hash table keys:
            return item in self.chord_count.keys()
        elif isinstance(item, Note):
            return item in self.note_set

    def __eq__(self, other):
        if isinstance(other, Progression):
            return self.chords == other.chords
        else:
            raise TypeError(f'__eq__ only defined between Progressions, not between Progression and: {type(other)}')

    def __str__(self):
        # numerals = self.as_numerals()
        # chord_names = ' '.join([c.short_name for c in self.chords])
        lb, rb = self._brackets
        return f'{self.chords}  or  {lb} {self.as_numerals(check_scale=True)} {rb}  (in {self.key.name})'

    # def __str__(self):
    #     # chord_set_str = '-'.join(['♬ ' + c.name for c in self.chords])
    #     chords_str = '-'.join([c.name for c in self.chords])
    #     return f'ChordProgression: {chords_str} \n or Progression:  𝄆 {self.as_numerals()} 𝄇  (in {self.key.name})'
    #
    # def __repr__(self):
    #     return str(self)

# TODO: key recognition routine that respects progression logic,
# i.e. looking for cadences or half cadences in the final root movement

def propose_root_movements(start, direction):
    """Given a root degree 'from', and a direction which should be one of 'D' (dominant)
    or 'SD' (subdominant), propose DegreeMovement continuations in that direction"""
    ...
