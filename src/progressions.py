### this progressions module is incomplete, very WIP at the moment

from .intervals import Interval
from .notes import Note, NoteList
from .chords import Chord, AbstractChord, ChordList
from .qualities import Major, Minor, Perfect, Diminished, parse_chord_modifiers, ChordModifier
from .scales import Scale, ScaleChord, NaturalMajor, NaturalMinor, MelodicMinor, HarmonicMinor, MelodicMajor, HarmonicMajor
from .keys import Key, KeyChord # matching_keys, most_likely_key
from .util import reduce_aliases, rotate_list, check_all, reverse_dict, log
from .parsing import roman_numerals, numerals_roman, auto_split, superscript, fl, sh, nat
from . import parsing, _settings

from collections import Counter

# import numpy as np  # not needed yet

# global defaults:
default_diacs = _settings.DEFAULT_PROGRESSION_DIACRITICS
default_marks = _settings.DEFAULT_PROGRESSION_MARKERS

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


### harmonic flowchart in major:

major_harmonic_model_functions = {'T': ['TP', 'PD', 'D'],  # tonic to tonic prolongation, predominant, or dominant
                        'TP': ['TP', 'PD'],
                        'PD': ['PD', 'D'],
                        'D': ['D', 'T']}
major_harmonic_model_degrees = {1: [3,6,4,2,7,5],
                                3: [6,4,2],
                                6: [4,2],
                                4: [2,7,5],
                                2: [7,5],
                                7: [5,1],
                                5: [1]}
major_harmonic_model_degrees_exceptions = {4: [1], 5: [6]}


major_function_chords = {'T': [1], 'TP': [3,6], 'PD': [4,2], 'D': [7,5]}

# functions of (major?) scale chords, indexed by interval (not degree)
scale_functions = { 0: "T", # 1st, tonic
                    1: "ST", # m2, supertonic
                    2: "ST", # M2, supertonic
                    3: "M", # m3, mediant
                    4: "M", # M3, mediant
                    5: "S", # 4th, subdominant
                    6: "TT", # tritone
                    7: "D", # 5th, dominant
                    8: "SM", # m6, submediant
                    9: "SM", # M6, submediant
                    10: "ST", # m7, subtonic
                    11: "L", # M7, leading tone
                    }

scale_function_names = {0: "tonic", # 1st
                        1: "supertonic", # 2nd (phrygian/locrian)
                        2: "supertonic", # 2nd
                        3: "mediant", # 3rd (minor)
                        4: "mediant", # 3rd (major)
                        5: "subdominant", # 4th
                        6: "tritone",
                        7: "dominant", # 5th
                        8: "submediant", # 6th (minor)
                        9: "submediant", # 6th (major)
                        10: "subtonic", # 7th (minor)
                        11: "leading tone", # 7th (major)
                        }

# modifier_marks = { 'dim':  '°',
#                    'hdim': 'ø', # ᶲ ?
#                    'aug':  '⁺',
#                    'maj':  'ᐞ',
#                    # '5':    '⁵',
#                    # '6':    '⁶',
#                    # '7':    '⁷',
#                    # 'm7':   '⁷',  # a kludge; here we replace out the 'm' because it is already implied by the lower case roman numeral
#                    # '9':    '⁹',
#                    # 'm9':   '⁹', # ditto for m9, m11, m13
#                    # '11':   '¹¹',
#                    # 'm11':  '¹¹',
#                    # '13':   '¹³',
#                    # 'm13':  '¹³',
#                    'sus':  'ˢ',
#                    'add':  'ᵃ',
# _settings.CHARACTERS['unknown_chord']: _settings.CHARACTERS['unknown_superscript'],
# } # '⁽ᵃ⁾'}
#
# # all numerals also get turned into modifier marks:
# modifier_marks.update({str(i): parsing.superscript_integers[i] for i in range(10)})
# # as well as some select superscriptable symbols:
# modifier_marks.update({c: parsing.superscript_symbols[c] for c in '/+-!?'})
# # but not chord alterations: (because we can't superscript sharps/flats)
# modifier_marks.update({f'{acc}{i}' : f'{acc}{i}' for i in range(3,14) for acc in [sh, fl, nat]})


roman_degree_chords = {}
# render as an alias dict linking numerals to major/minor qualities:
for arabic,roman in numerals_roman.items():
    roman_degree_chords[roman] = (arabic, Major)
    roman_degree_chords[roman.lower()] = (arabic, Minor)
# and the reverse mapping, for SDC.__repr__:
degree_chords_roman = reverse_dict(roman_degree_chords)

progression_aliases = dict(roman_degree_chords)
# fractional degrees for bIII chords etc:
accidental_progression_aliases = {}
for num, (deg, qual) in progression_aliases.items():
    if deg > 1:
        for flat_sign in parsing.offset_accidentals[-1]:
            accidental_progression_aliases[flat_sign + num] = (round(deg-0.5, 1), qual)
    if deg < 8:
        for sharp_sign in parsing.offset_accidentals[1]:
            accidental_progression_aliases[sharp_sign + num] = (round(deg+0.5, 1), qual)
progression_aliases.update(accidental_progression_aliases)
# kludge: we have to specifically ignore 'dim' when reading roman numerals,
# because it is the only modifier that contains a roman numeral ('i')
progression_aliases['dim'] = 'dim'

minor_mod = ChordModifier('minor')

def parse_roman_numeral(numeral, ignore_alteration=False):
    """given a (string) roman numeral, in upper or lower case,
    with a potential chord modifier at the end,
    parse into a (degree, AbstractChord) tuple, where degree is an int between 1-7"""

    if ignore_alteration and parsing.is_accidental(numeral[0]):
        # if required, disregard accidentals in the start of this degree, like bIII -> III
        numeral = numeral[1:]

    out = reduce_aliases(numeral, progression_aliases)
    assert isinstance(out[0], tuple) # an integer, quality tuple
    deg, quality = out[0]

    modifiers = []
    inversion = 0

    if quality.minor:
        modifiers.append(minor_mod)

    if len(out) > 1: # got one or more additional modifiers as well
        rest = ''.join(out[1:])

        rest_inv = rest.split('/')
        if len(rest_inv) > 1:
            assert len(rest_inv) == 2 # chord part and inversion part
            rest, inversion = rest_inv[0], int(rest_inv[1])

        rest_mods = parse_chord_modifiers(rest)
        modifiers.extend(rest_mods)

    chord = AbstractChord(modifiers=modifiers, inversion=inversion)

    return deg, chord


class DegreeMotion:
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
            assert isinstance(scale, Scale), f"DegreeMotion expected a Scale object, or string that casts to Scale, but got: {type(scale)}"
        self.scale = scale

        # if end is not None:
        if isinstance(start, int) and isinstance(end, int):
            # regular integer degree movement
            assert (start in range(1,scale.factors.max_degree+1)) and (end in range(1,scale.factors.max_degree+1))
            self.fractional = False
        else:
            # movement involving one or more fractional degrees
            # which might get strange?
            log(f'Parsed a fractional degree movement from {start} to {end}')
            self.fractional = True

        self.start, self.end = start, end

        self._set_degree_distances()
        if scale is not None:
            self._set_interval_distances(scale)

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
        if not self.fractional:
            self.start_iv, self.end_iv = (scale_obj.degree_intervals[d] for d in [self.start, self.end])
        else:
            self.start_iv = scale_obj.degree_intervals[self.start] if self.start in scale_obj.degree_intervals else scale_obj.fractional_degree_intervals[self.start]
            self.end_iv = scale_obj.degree_intervals[self.end] if self.end in scale_obj.degree_intervals else scale_obj.fractional_degree_intervals[self.end]

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

    @property
    def direction_str(self):
        if self.up == 0: # no direction
            return ' 0'

        if self.descending_fifth:
            direction_char = self._down_arrow
            distance_char = 5
        elif self.ascending_fifth:
            direction_char = self._up_arrow
            distance_char = 5
        else:
            distance, upward = self.magnitude, (self.distance > 0)
            direction_char = self._up_arrow if upward else self._down_arrow
            distance_char = self.magnitude + 1

        return f'{direction_char}{distance_char}'

    @property
    def degrees(self):
        return f'{self.start}{self._movement_marker}{self.end}'

    def __str__(self):
        return(f'{self.degrees}:{self.direction_str}')

    def __repr__(self):
        return str(self)

    _movement_marker = _settings.MARKERS['right']
    _up_arrow = _settings.MARKERS['up']
    _down_arrow = _settings.MARKERS['down']


class RootMotion(DegreeMotion):
    """degree motion specifically between chord roots,
    defined with extra properties like harmonic function"""

    def __init__(self, *args, **kwargs):

        DegreeMotion.__init__(self, *args, **kwargs)
        self._set_harmonic_functions()

    def _set_harmonic_functions(self):
        self.descending_fifth = self.down == 4
        self.ascending_fifth = self.down == 3
        # self.function = ('primary ' if self.primary else 'substitute ') + ('dominant' if self.dominant else 'subdominant')

        # the 'size' of the movement: 2 to 1 has less magnitude than 5 to 1, but the same as 7 to 1
        self.magnitude = min([self.up, self.down])
        # signed/directional shortest distance up or down:
        self.distance = self.up if self.up == self.magnitude else -self.down

        # experimental chord function flags: (based on major scale harmony theory, but should apply to minor as well?)
        self.dominant = self.down in {4,2} or self.up in {3,1} # descending by fifth or third
        self.subdominant = self.down in {3,1} or self.up in {4,2}
        self.primary = 4 in {self.down, self.up}
        self.substitute = not self.primary

        if self.scale is not None:
            self.start_function = scale_functions[int(self.start_iv)]
            self.end_function = scale_functions[int(self.end_iv)]

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
    def cadence_score(self):
        # extremely fuzzy score used for checking the grammaticity of progressions
        if self.authentic_cadence:
            return 1
        elif self.authentic_half_cadence:
            return 0.5
        elif self.plagal_cadence:
            return 0.75
        elif self.plagal_half_cadence:
            return 0.25
        elif self.deceptive_cadence:
            return 0.1
        else:
            return 0

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
        """returns a string that describes the function of this DegreeMotion as a root movement,
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
        elif self.fractional:
            return '?'
        else:
            return '='

    def __str__(self):
        return(f'[{self.function_char}]{self.degrees}:{self.direction_str}')



class Progression:
    """A theoretical progression between AbstractChords in a particular scale,
    initialised as list: e.g. Progression(['I', 'IV', 'iii', 'V'])
    or as string separated by dashes, e.g.: Progression('I-IV-iii-V')"""
    def __init__(self, *numerals, scale=None, chords=None, order=3, ignore_conflicting_case=False):
        """accepts one of three input schemes:
        1. 'numerals' input is a list (or demarcated string) of upper/lower-case roman numerals denoting scale chords,
            with optional 'scale' parameter.
                a. if scale is None, we automatically determine the scale from the case/quality of the chord numerals.
                b. if scale is provided, and 'ignore_conflicting_case' is False, we parse chords according to their case/quality,
                    even if they conflict with the scale given.
                c. if scale is provided, and ignore_conflicting_case is True, we ignore the case/quality of the chord numerals
                    and instantiate chords solely according to their root degree and modifiers, in the scale given.
                        in either case (?), if 'auto_qualify' is True, we also qualify chords automatically as required by the scale,
                        for example making the 7-chord diminished in major.
        2. 'numerals' input is a list of integers denoting root degrees of chords, and 'scale' is a Scale object (or string that casts to Scale),
            in which case we allocate major/minor quality to the chords based on the scale provided.
        3. 'numerals' input is a list of integers denoting root degrees of chords, and 'chords' is an iterable of AbstractChord objects
            (or strings that cast to AbstractChords), in which case we automatically determine the scale from the qualities of the chords.
        4. 'numerals' input is a list of ScaleChords, in which case no other args are needed.
        other args:
        'order': only used if 'chords' is not provided. determines the order of chords generated for this progression,
            where order=3 produces triads, order=4 produces tetrads, etc.
            instead of an integer, 'order' can be a list of integers with the same length as 'numerals',
            which gets unpacked into a separate order for each chord in the progression."""

        original_input = numerals # for debugging

        # unpack tuple arg:
        if len(numerals) == 1:
            numerals = numerals[0]

        # reparse args to catch if 'chords' has been given, but no numerals:
        if (len(numerals) == 0) and chords is not None:
            if check_all(chords, 'isinstance', ScaleChord):
                numerals = chords
                chords = None

        if isinstance(numerals, str):
            original_numerals = numerals
            # remove all diacritics:
            numerals = ''.join([c for c in numerals if c not in _settings.DIACRITICS.values()])
            # and all scale marks:

            split_numerals = auto_split(numerals, allow='°øΔ♯♭♮+𝄫𝄪#/' + ''.join(parsing.modifier_marks.values()))
            assert len(split_numerals) > 1, f"Expected a string of roman numerals separated by dashes (or other obvious separator), but got: {numerals[0]}"
            numerals = split_numerals
        # is now an iterable of roman numeral strings OR of integers OR scalechords

        if check_all(numerals, 'isinstance', str):
            # roman numeral strings
            # which we parse into AbstractChords based on their case and suffixes
            base_degree_chords = [parse_roman_numeral(n) for n in numerals] # degree, AbstractChord tuples


            self.root_degrees = [d[0] for d in base_degree_chords]

            # log(f'Base (unscaled) degree chords:')
            # for r,c in base_degree_chords:
                # log(f'{r}: {c}')

            if scale is None:
                # detect scale from base AbstractChords and then instantiate ScaleChords
                # abs_chords = ChordList([ch for d,ch in base_degree_chords])
                self.scale = self._detect_scale(base_degree_chords)

                # catch a special case: have we been given flat degrees (like bVI) in a minor key,
                # which cannot be found because e.g. the minor VI is already flat?
                for i in range(len(base_degree_chords)):
                    deg, ch = base_degree_chords[i]
                    if isinstance(deg, float) and deg not in self.scale.fractional_degree_intervals:
                        # quietly re-parse but ignore accidental:
                        log(f'Progression given chord: {numerals[i]} but that altered root is already in scale')
                        deg, ch = parse_roman_numeral(numerals[i], ignore_alteration=True)
                        base_degree_chords[i] = deg, ch
                        log(f'So quietly replaced with {numerals[i][1:]} (in scale: {self.scale.name}')
                        self.root_degrees = [d[0] for d in base_degree_chords]

                self.chords = ChordList([ch.in_scale(self.scale, degree=d) for d,ch in base_degree_chords])

            else:
                # scale is provided, so we simply instantiate it
                # and, if needed, check degree chords against it
                if isinstance(scale, str):
                    scale = Scale(scale)
                # assert isinstance(scale, Scale)
                self.scale = scale

                # catch a special case: have we been given flat degrees (like bVI) in a minor key,
                # which cannot be found because e.g. the minor VI is already flat?
                for i in range(len(base_degree_chords)):
                    deg, ch = base_degree_chords[i]
                    if isinstance(deg, float) and deg not in self.scale.fractional_degree_intervals:
                        # quietly re-parse but ignore accidental:
                        log(f'Progression given chord: {numerals[i]} but that altered root is already in scale')
                        deg, ch = parse_roman_numeral(numerals[i], ignore_alteration=True)
                        base_degree_chords[i] = deg, ch
                        log(f'So quietly replaced with {numerals[i][1:]} (in scale: {self.scale.name}')
                        self.root_degrees = [d[0] for d in base_degree_chords]


                if ignore_conflicting_case:
                    # ignore case (but not modifiers) of roman numeral chords provided
                    # and instantiate them from scale instead:
                    scale_chords = ChordList([self.scale.chord(d, linked=True) for d in self.root_degrees])
                    self.chords = scale_chords
                    log(f'Ignoring conflicting case in chord numerals:')
                    for (d, bc), sc in zip(base_degree_chords, self.chords):
                        if bc == sc:
                            log(f'{d}: Provided {bc.short_name:{5}}, computed {sc.short_name:{5}}')
                        else:
                            log(f'{d}: Provided {bc.short_name:{5}}, computed {sc.short_name:{5}} [CONFLICT, using computed scale chord]')

                else:
                    # do not ignore case; instantiate chords in provided case
                    self.chords = ChordList([ch.in_scale(self.scale, degree=d) for d,ch in base_degree_chords])
                    # log(f'Ignoring conflicting case in chord numerals:')
                    # for (d, bc), sc in zip(base_degree_chords, scale_chords):
                        # if bc == sc:
                            # log(f'{d}: Provided {bc.short_name:{5}}, computed {sc.short_name:{5}}')
                        # else:
                            # log(f'{d}: Provided {bc.short_name:{5}}, computed {sc.short_name:{5}} [CONFLICT, using provided chord]')
                # print()

        elif check_all(numerals, 'isinstance', int):
            assert scale is not None, f'Progression chords given as integers but scale arg not provided'
            if isinstance(scale, str):
                scale = Scale(scale)
            assert type(scale) is Scale
            self.scale = scale
            self.root_degrees = numerals
            if chords is None:
                # construct scale chords: (and here we check the order arg to make 7ths etc. if needed)
                if isinstance(order, int): # same order for each chord
                    order = [order] * len(numerals)
                else: # individual order for each chord
                    assert isinstance(order, (list,tuple)), f"'order' arg to Progression must be an int or list of ints, but got: {type(order)}"
                self.chords = ChordList([self.scale.chord(d, order=order[i], linked=True) for i,d in enumerate(self.root_degrees)])
            else:
                # use the abstractchords we have been given (and cast them to abstract)
                import ipdb; ipdb.set_trace() # why are these being abstracted?
                self.chords = ChordList(chords).abstract()

        elif check_all(numerals, 'isinstance', ScaleChord):
            ### allow init by scalechords alone
            scalechord_scales = [ch.scale for ch in numerals]
            assert check_all(scalechord_scales, 'eq', scalechord_scales[0]), f"Non-matching scale attributes in ScaleChord list given to Progression: {scalechord_scales}"
            self.scale = scalechord_scales[0]
            self.chords = numerals
            self.root_degrees = [ch.scale_degree for ch in self.chords]

        else:
            raise ValueError(f'Progression init ended up with an iterable of mixed types, expected all ints or all strings but got: {numerals}')

        # self.abstract_chords = self.chords # true for Progression class, not for ChordProgression

        # scaledegree, chord pairs:
        # self.degree_chords = [(self.root_degrees[i], self.chords[i]) for i in range(len(self))]

        # self.numerals = self.as_numerals(sep=None)

        # note movements between each chord root:
        self.chord_root_intervals_from_tonic = [self.scale.degree_intervals[d] if d in self.scale.degree_intervals else self.scale.fractional_degree_intervals[d]  for d in self.root_degrees]
        self.root_movements = [RootMotion(self.root_degrees[i], self.root_degrees[i+1], scale=self.scale) for i in range(len(self)-1)]

        assert check_all(self.chords, 'isinstance', ScaleChord) # sanity check: progression chords are always ScaleChords


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

    def analyse(self, display=False, ret=True):
        """shows the harmonic functions of the chords in this progression"""
        out = []
        from src.display import DataFrame
        df = DataFrame(['Function', '', 'Deg1', '', 'Deg2', '',
                         # 'Chd1', '', 'Chd2', '',
                         'Distance', '', 'Cadence'])
        # sloppy for now: should be rolled into a dataframe from the Display module
        num1s, num2s, c1s, c2s, mvs, cads = [], [], [], [], [], []
        for i in range(len(self)-1):
            f = f'[{self.root_movements[i].function_char}]'
            arrow = self.root_movements[i]._movement_marker
            n1, n2 = self.numerals[i], self.numerals[i+1]
            ch1, ch2 = self.chords[i].short_name, self.chords[i+1].short_name,
            dist = str(self.root_movements[i].direction_str)
            cadence = self.root_movements[i].cadence
            cadence = cadence if (cadence != False) else ''
            df.append([f, '  ', n1, arrow, n2, '  ',
                        # ch1, arrow, ch2, ' ',
                        dist, '  ', cadence])

            # num1s.append(self.numerals[i])
            # num2s.append(self.numerals[i+1])
            # c1s.append(self.chords[i].short_name)
            # c2s.append(self.chords[i+1].short_name)
            # mvs.append(str(self.root_movements[i].direction_str))
            # cad = self.root_movements[i].cadence
            # cads.append(cad if cad != False else '')

        if display:
            print('\n' + str(self))
            # border between title and df:
            title_width = len(str(self))
            df_width = df.total_width(up_to_row=None, header=False, margin_size=0)
            print('=' * max([title_width, df_width]))
            df.show(header=False, header_border=False, margin='')
        if ret:
            return df
        # # determine max string len of each element:
        # c1_len = max([len(c) for c in c1s])
        # c2_len = max([len(c) for c in c2s])
        # mv_len = max([len(mv) for mv in mvs])
        # n1_len = max([len(n) for n in num1s])
        # n2_len = max([len(n) for n in num2s])

        # out = [str(self)]
        # for i in range(len(self)-1):
        #     f = self.root_movements[i].function_char
        #     arrow = self.root_movements[i]._movement_marker
        #     d1, c1, d2, c2, mv, cad = self.root_degrees[i], c1s[i], self.root_degrees[i+1], c2s[i], mvs[i], cads[i]
        #     n1 = num1s[i].lower() if self.chords[i].quality.minor_ish else num1s[i]
        #     n2 = num2s[i].lower() if self.chords[i+1].quality.minor_ish else num2s[i]
        #     line = f'[{f}] {n1:{n1_len}}{arrow}{n2:{n2_len}}    {d1}:{c1:{c1_len}}{arrow}{d2}:{c2:{c2_len}}    {mv:{mv_len}}    {cad}'
        #     out.append(line)
        # if display:
        #     print('\n'.join(out))
        # if ret:
        #     return '\n'.join(out)

    # def analyze(self, *args, **kwargs):
    #     """see Progression.analyse (this is just a quality-of-life alias for American spelling)"""
    #     return self.analyse(*args, **kwargs)

    analyze = analyse # QoL alias

    @property
    def analysis(self):
        return self.analyse(display=True, ret=False)

    def as_numerals(self, sep=' ', modifiers=True, marks=default_marks, diacritics=default_diacs):
        """returns this Progression's representation in roman numeral form
        with respect to its Scale"""

        # scale_chords = [ch.in_scale(self.scale, degree=self.root_degrees[i]) for i,ch in enumerate(self)]

        numerals = [ch.get_numeral(modifiers=modifiers, marks=marks, diacritics=diacritics) for ch in self.chords]

        if sep is not None:
            roman_chords_str = sep.join(numerals)
            return roman_chords_str
        else:
            # just return the raw list, instead of a sep-connected string
            return numerals

    @property
    def numerals(self):
        return self.as_numerals()

    # def _as_numerals(self, sep='  ', check_scale=False):
    #     numerals = []
    #     for d,c in self.degree_chords:
    #         # use the quality of the chord if it is not indeterminate, otherwise use the quality of the key:
    #         chord_mod = c.quality if not c.quality.perfect else self.scale.quality
    #         if chord_mod.major_ish:
    #             numerals.append(numerals_roman[d])
    #         elif chord_mod.minor_ish:
    #             numerals.append(numerals_roman[d].lower())
    #         else:
    #             raise Exception(f'Could not figure out whether to make numeral upper or lowercase: {d}:{c} in {key} (should never happen)')
    #
    #     # add suffixes: (we ignore the 'm' suffix because it is denoted by lowercase instead)
    #     suffix_list = [c.suffix if c.suffix != 'm' else '' for c in self.chords]
    #     # pull inversions out of suffixes:
    #     for i in range(len(suffix_list)):
    #         chord, suf = self.chords[i], suffix_list[i]
    #         if '/' in suf:
    #             # slash chord detected
    #             new_slash = parsing.superscript['/']
    #             new_inv = ''.join([parsing.superscript[s] for s in str(chord.inversion)])
    #             new_suf = f'{new_slash}{new_inv}'
    #             suffix_list[i] = new_suf
    #
    #     roman_chords_list = [f'{numerals[i]}{suffix_list[i]}' for i in range(len(self))]
    #
    #     if check_scale:
    #         # annotate chords that are chromatic to the scale with square brackets
    #         # or, if they are at least in the corresponding harmonic/melodic scale, mark that too:
    #         if self.scale.is_natural():
    #             if self.scale == NaturalMinor:
    #                 # natural minor scale
    #                 harmonic_scale = HarmonicMinor
    #                 melodic_scale = MelodicMinor
    #             elif self.scale == NaturalMajor:
    #                 # natural major scale
    #                 harmonic_scale = HarmonicMajor
    #                 melodic_scale = MelodicMajor
    #
    #             belongs_natural = [self.scale.contains_degree_chord(d,c) for d,c in self.degree_chords]
    #
    #             ## is this needed?
    #             # but don't allow chords that are built on harmonic/melodic roots:
    #             root_intervals = [self.scale.degree_intervals[d] for d,c in self.degree_chords]
    #             belongs_harmonic = [HarmonicMinor.contains_degree_chord(*self.degree_chords[i], degree_interval=root_intervals[i]) for i in range(len(self))]
    #             belongs_melodic = [MelodicMinor.contains_degree_chord(*self.degree_chords[i], degree_interval=root_intervals[i]) for i in range(len(self))]
    #             ### (will probably handle chord roots belonging to parallel/neighbouring keys separately)
    #
    #             # belongs_harmonic = [HarmonicMinor.contains_degree_chord(d,c, for d,c in self.degree_chords]
    #             # belongs_melodic = [MelodicMinor.contains_degree_chord(d,c for d,c in self.degree_chords]
    #             new_roman_chords = []
    #             for i in range(len(roman_chords_list)):
    #                 orig = roman_chords_list[i]
    #                 if belongs_natural[i]:
    #                     new_roman_chords.append(orig)
    #                 elif belongs_harmonic[i]:
    #                     # mark first character with combining 'h':
    #                     new_roman_chords.append(f'{orig[0]}{orig[1:]}\u036A')
    #                 elif belongs_melodic[i]:
    #                     # mark first character with combining 'm':
    #                     new_roman_chords.append(f'{orig[0]}{orig[1:]}\u036B')
    #                 else:
    #                     # mark out-of-scale chord with brackets:
    #                     new_roman_chords.append(f'[{orig}]')
    #             roman_chords_list = new_roman_chords
    #         else:
    #             # non-natural scale: just check raw scale compatibility
    #             belongs = [self.scale.contains_degree_chord(d,c) for d,c in self.degree_chords]
    #             roman_chords_list = [f'{roman_chords_list[i]}' if belongs[i]  else f'[{roman_chords_list[i]}]'  for i in range(len(self))]
    #
    #     # turn suffix modifiers into superscript marks etc. where possible:
    #     roman_chords_list = [''.join(reduce_aliases(r, parsing.modifier_marks)) for r in roman_chords_list]
    #     if sep is not None:
    #         roman_chords_str = sep.join(roman_chords_list)
    #         return roman_chords_str
    #     else:
    #         # just return the raw list, instead of a sep-connected string
    #         return roman_chords_list

    def in_key(self, key, **kwargs):
        """returns a ChordProgression with these chords over a specified Key object"""
        # cast to Key object:
        if isinstance(key, str):
            key = Key(key)
        assert isinstance(key, Key)
        key_chords = []
        for ch in self.chords:
            d = ch.scale_degree
            root = key.degree_notes[d] if d in key.degree_notes else key.fractional_degree_notes[d]
            key_chords.append(ch.on_root(root))
        return ChordProgression(key_chords, key=key, **kwargs)

    def on_tonic(self, tonic, **kwargs):
        """uses the existing set or detected .scale attribute and returns a ChordProgression
        in the Key of that scale which starts on the desired tonic"""
        key = self.scale.on_tonic(tonic)
        return self.in_key(key, **kwargs)

    def rotate(self, N):
        """returns a rotation of this progression by N places"""
        # (inheritable by ChordProgression)
        new_chords = self.chords.rotate(N)
        return self.__class__(new_chords)

    def get_rotations(self):
        """returns all the rotations of this progression"""
        return [self.rotate(i) for i in range(2,len(self)+1)]
    @property
    def rotations(self):
        return self.get_rotations()

    @property
    def diagram(self):
        from .guitar import standard # lazy import
        standard.show(self)

    def __len__(self):
        return len(self.root_degrees)

    def __str__(self, marks=default_marks, diacritics=default_diacs):
        scale_name = self.scale.name
        if 'natural' in scale_name:
            scale_name = scale_name.replace('natural ', '')
        lb, rb = self._brackets
        return f'Progression:  {lb}{self.as_numerals(marks=marks, diacritics=diacritics)}{rb}  (in {scale_name})'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        """progressions are emod to each other if they have the same chords built on the same degrees"""
        # built on the same degrees:
        return (self.chords == other.chords) and (self.root_degrees == other.root_degrees)

    def __add__(self, other):
        """Addition defined over Progressions:
            1. Progression + integer tranposes this progression's roots upward by that many degrees
            2. Progression + roman numeral returns a new Progression with that numeral appended to it"""
        if isinstance(other, int): # transpose upward/downward by integer degrees
            new_root_degrees = [r + other for r in self.root_degrees]
            # mod to range 1-7:
            new_root_degrees = [((r-1) % 7) + 1 for r in new_root_degrees]
            return Progression(numerals=new_root_degrees, chords=self.chords, scale=self.scale)
        elif isinstance(other, str): # add a new chord (as roman numeral)
            new_numerals = self.numerals + [other]
            return Progression(new_numerals, scale=self.scale)
        elif isinstance(other, (list, tuple)): # add new chords as list of roman numeral strings
            assert check_all(other, 'isinstance', 'str'), f"Progression got added with list/tuple, expected to loop over roman numeral strings but got: {type(other[0])}"
            new_numerals = self.numerals + list(other)
            return Progression(new_numerals, scale=self.scale)
        elif isinstance(other, Progression): # concatenate two progressions
            new_numerals = self.numerals + other.numerals
            new_chords = self.chords + other.chords
            return Progression(new_numerals, chords=new_chords, scale=self.scale)

    def pad_with_tonic(self):
        """returns a new Progression that is this one but with an added tonic of the appropriate quality,
        if this one does not already end on a tonic"""
        if self.root_degrees[-1] != 1:
            tonic_char = 'I' if self.scale.quality.major else 'i'
            return self + tonic_char
        else:
            return self

    def simplify(self):
        """returns a new Progression based on this one with simplified chords only"""
        new_chords = [ch.simplify() for ch in self.chords]
        return self.__class__(new_chords)

    _brackets = _settings.BRACKETS['Progression']

def most_grammatical_progression(progressions, add_resolution=True, verbose=False):
    """given an iterable of Progression objects, compare their cadences and return the one that seems most likely/grammatical"""
    p1_len = len(progressions[0])
    # sanity check that all progressions are the same length:
    lengths = [len(p) for p in progressions]
    for l in lengths:
        assert l == p1_len

    # count the number of cadences in each progression:
    cadence_counts = [0] * len(progressions)
    cadence_scores = [0] * len(progressions)
    for i,p in enumerate(progressions):
        if add_resolution:
            # add a tonic on the end to see how it resolves
            p = p.pad_with_tonic()
        for movement in p.root_movements:
            if movement.cadence:
                cadence_counts[i] += 1
                cadence_scores[i] += movement.cadence_score
        # normalise by progression length: (to compensate for added implied resolutions)
        cadence_scores[i] = cadence_scores[i] / len(p)
    # take argmax of cadence count/score:
    max_cadences = max(cadence_scores)
    top_matches = []
    for i,c in enumerate(cadence_scores):
        if c == max_cadences:
            top_matches.append(i)


    for p,c in zip(progressions, cadence_scores):
        log(f'\nTesting key: {p.key}')
        if verbose:
            p.pad_with_tonic().analysis
        log(f'cadence score:{c})\n')

    matching_progressions = [progressions[i] for i in top_matches]

    return matching_progressions

    # if len(top_matches) == 1:
        # # one progression has the most cadences

        # return matching_progressions
        # # match_idx = top_matches[0]
        # # return progressions[match_idx]
    # else:
        # # multiple matching progressions
        # return top_matches




class ChordMotion:
    """Movement of root and every other chord degree from one to another"""
    def __init__(self, start_chord, end_chord, key=None):
        self.start_chord = start_chord
        self.end_chord = end_chord
        if key is None:
            # interpret it from given KeyChords:
            assert isinstance(start_chord, KeyChord)
            assert isinstance(end_chord, KeyChord)
            assert start_chord.key == end_chord.key
            key = start_chord.key
        self.key = key
        self.scale = key.scale

        # experimental, WIP
        import numpy as np
        distance_matrix = np.zeros((len(start_chord), len(end_chord)))
        for r, n1 in enumerate(start_chord.notes):
            for c, n2 in enumerate(end_chord.notes):
                deg1, deg2 = key.note_degrees[n1], key.note_degrees[n2]
                motion = DegreeMotion(deg1, deg2, scale=key.scale)
                distance_matrix[r,c] = motion.distance

        print(distance_matrix)


class ChordProgression(Progression, ChordList):
    """ChordList subclass defined additionally over a specific key"""
    def __init__(self, *chords, key=None, search_natural_keys_only=False):
        """Initialised by a list or series of Chord objects, or strings that cast to Chord objects,
        or by a list of integers combined with the (otherwise-optional) key argument.

        If key is not given, we try to detect the most likely key using a
        combination of the chord notes, and the likeliness of the progression
        in specific keys with respect to cadence resolution etc.
        By default, this key detection routine searches all keys that fit the
        chords, but if search_natural_keys_only is True, we search natural major
        and minor keys only  (useful for performance purposes)"""

        if len(chords) == 1:
            chords = chords[0]

        if isinstance(chords, str):
            # if chords is a plain string instead of iterable,
            # try auto splitting:
            chords = auto_split(chords, allow='°øΔ♯♭♮+𝄫𝄪#/' + ''.join(parsing.modifier_marks.values()))

        # iterate through list and cast to chord objectss:
        valid_chords = []

        keychord_keys = [] # for determining progression key later on
        for item in chords:
            if isinstance(item, KeyChord): # already a KeyChord object
                ch = item
                keychord_keys.append(ch.key)
            elif isinstance(item, Chord): # already a Chord object
                ch = item
            elif isinstance(item, str): # string that we try to cast to Chord
                ch = Chord(item)
            elif isinstance(item, (list, tuple)): # unpackable parameters that we try to cast to Chord
                ch = Chord(*item)
            elif isinstance(item, dict):
                # unpack keyword args to cast to chord
                ch = Chord(**dict)
            else:
                raise ValueError(f'Expected iterable to contain Chords, or items that can be cast as Chords, but got: {type(item)}')

            valid_chords.append(ch)

        base_chords = ChordList(chords)
        # self.abstract_chords = [c.abstract() for c in base_chords]

        if key is None:
            # detect most likely key:
            if len(keychord_keys) > 0:
                # accept key from KeyChord attributes
                assert check_all(keychord_keys, 'eq', keychord_keys[0]), f"Non-matching key attributes in KeyChord list given to ChordProgression: {keychord_keys}"
                self.key = keychord_keys[0]
            else:
                self.key = base_chords.find_key(natural_only = search_natural_keys_only)
        else:
            self.key = key if isinstance(key, Key) else Key(key)

        self.scale = Scale(self.key.scale)
        self.roots = NoteList([ch.root for ch in base_chords])
        self.basses = NoteList([ch.bass for ch in base_chords])

        self.root_degrees = [self.key.note_degrees[n] if n in self.key.note_degrees else self.key.fractional_note_degrees[n] for n in self.roots]

        # form KeyChords:
        self.chords = ChordList([KeyChord(factors=ch.factors, inversion=ch.inversion, root=ch.root, key=self.key, degree=d) for ch,d in zip(base_chords, self.root_degrees)])

        # self.degree_chords = [(self.root_degrees[i], self.chords[i]) for i in range(len(self))]

        # self.numerals = self.as_numerals(sep=None)

        # note movements between each chord root:
        self.chord_root_intervals_from_tonic = [self.key.degree_intervals[d]  if d in self.key.degree_intervals  else self.key.fractional_degree_intervals[d]  for d in self.root_degrees]
        self.root_movements = [RootMotion(self.root_degrees[i], self.root_degrees[i+1], scale=self.scale) for i in range(len(self)-1)]

        # assert check_all(self.chords, 'isinstance', KeyChord) # sanity check: progression chords are always ScaleChords



    def __contains__(self, item):
        if isinstance(item, Chord):
            # efficient lookup by checking hash table keys:
            return item in self.chords
        elif isinstance(item, Note):
            return item in self.chords.note_counts()

    def __eq__(self, other):
        if isinstance(other, Progression):
            return self.chords == other.chords
        else:
            raise TypeError(f'__eq__ only defined between Progressions, not between Progression and: {type(other)}')

    @property
    def scale_chords(self):
        """return the chords that comprise this progression
        as ScaleChords (rather than KeyChords)"""
        return ChordList([ScaleChord(factors=ch.factors, inversion=ch.inversion, scale=ch.key.scale, degree=ch.scale_degree) for ch in self.chords])

    def abstract(self):
        """returns the abstract Progression object corresponding to this ChordProgression"""
        return Progression(self.scale_chords, scale=self.key.scale)

    @property
    def progression(self):
        return self.abstract()

    def __add__(self, other):
        """Addition defined over ChordProgressions:
            1. Progression + integer tranposes this progression's roots upward by that many degrees
            2. ChordProgression + roman numeral returns a new ChordProgression with that numeral appended to it
            3. ChordProgression + Chord returns a new ChordProgression with that chord appended to it"""
        if isinstance(other, int):
            new_root_degrees = [r + other for r in self.root_degrees]
            # mod to range 1-7:
            new_root_degrees = [((r-1) % 7) + 1 for r in new_root_degrees]
            return Progression(numerals=new_root_degrees, chords=self.scale_chords, scale=self.scale)
        elif isinstance(other, str):
            # check if a roman numeral:
            if other.upper() in roman_numerals:
                new_numerals = self.numerals + [other]
                return Progression(new_numerals, scale=self.scale).in_key(self.key)
            else:
                # assume this is a string that casts to Chord
                other = Chord(other)

        if isinstance(other, Chord):
            new_chords = self.chords + other
            return ChordProgression(new_chords, key=self.key)
        else:
            raise TypeError('ChordProgression.__add__ not implemented for type: {type(other)}')

        if isinstance(other, (list, tuple)):
            # if the first item is a numeral, assume the rest are numerals:
            if other[0].upper() in roman_numerals:
                new_numerals = self.numerals + list(other)
                return Progression(new_numerals, scale=self.scale).in_key(self.key)
            else:
                # assume these are Chords, or strings that cast to Chords
                new_chords = ChordList(self.chords + other)
                return ChordProgression(new_chords, key=self.key)

        elif isinstance(other, Progression):
            new_numerals = self.numerals + other.numerals
            return Progression(new_numerals, scale=self.key.scale).in_key(self.key)

    def pad_with_tonic(self):
        """returns a new ChordProgression that is this one but with an added tonic of the appropriate quality,
        if this one does not already end on a tonic"""
        if self.root_degrees[-1] != 1:
            tonic_chord = self.key.chord(1)
            return self + tonic_chord
        else:
            return self

    def play(self, *args, **kwargs):
        # just a wrapper around this progression's ChordList's method:
        self.chords.play(*args, **kwargs)

    _brackets = _settings.BRACKETS['ChordProgression']

    # def __str__(self):
    #     # chord_set_str = '-'.join(['♬ ' + c.name for c in self.chords])
    #     chords_str = '-'.join([c.name for c in self.chords])
    #     return f'ChordProgression: {chords_str} \n or Progression:  𝄆 {self.as_numerals()} 𝄇  (in {self.key.name})'

    def long_str(self):
        # numerals = self.as_numerals()
        # chord_names = ' '.join([c.short_name for c in self.chords])
        lb, rb = self._brackets
        return f'{self.chords}  or  {lb}{self.as_numerals()}{rb}  (in {self.key.name})'

    def __str__(self, marks=default_marks, diacritics=default_diacs):
        lb, rb = self._brackets
        numerals = self.as_numerals(marks=marks, diacritics=diacritics, sep='@')
        split_numerals = numerals.split('@')
        chordlist = [ch.name for ch in self.chords]
        num_chords = zip(split_numerals, chordlist)
        num_chords_str = ' - '.join([f'{ch} ({num})' for num, ch in num_chords])
        # return f'{self.chords}  (in {self.key.name})'
        return f'ChordProgression:  {lb}{num_chords_str}{rb}  (in {self.key.name})'

    # def __repr__(self):
    #     return str(self)

# def chordlist_numerals_in_key(chordlist, key, sep=' ', modifiers=True, auto_superscript=True):
#     """given a chordlist and a key, produces the roman numerals
#     that describe those chords in that key"""
#     # recast args if needed:
#     if not isinstance(chordlist, (ChordList)):
#         chordlist = ChordList(chordlist)
#     if not isinstance(key, Key):
#         key = Key(key)
#
#     root_degrees = chordlist.root_degrees_in(key)
#     scale_chords = [ch.in_scale(key.scale, degree=root_degrees[i]) for i,ch in enumerate(chordlist)]
#
#     numerals = [ch.numeral for ch in scale_chords]
#
#     if sep is not None:
#         roman_chords_str = sep.join(numerals)
#         return roman_chords_str
#     else:
#         # just return the raw list, instead of a sep-connected string
#         return numerals

    # if None in root_degrees:
    #     # if any of the chords start on a root that is NOT in the key,
    #     # figure out alternative notations:
    #     nonmatching_chord_idxs = [i for i,d in enumerate(root_degrees) if d is None]
    #     root_degrees = []
    #     root_degree_offsets = []
    #     for i, ch in enumerate(chordlist):
    #         if ch.root in key:
    #             root_degree = key.note_degrees[ch.root]
    #             root_degrees.append(root_degree)
    #             root_degree_offsets.append(0)
    #         else:
    #             root_interval = ch.root - key.tonic
    #             # is this a bIII or something?
    #             sharpened_root_note = ch.root + 1
    #             if sharpened_root_note in key:
    #                 sharpened_degree = key.note_degrees[sharpened_root_note]
    #                 root_degrees.append(sharpened_degree)
    #                 root_degree_offsets.append(-1)
    #                 continue
    #
    #             # this is more rare, but might come up in irregular keys:
    #             flattened_root_note = ch.root - 1
    #             if flattened_root_note in key:
    #                 flattened_degree = key.note_degrees[flattened_root_note]
    #                 root_degrees.append(flattened_degree)
    #                 root_degree_offsets.append(1)
    #                 continue
    #
    #             # otherwise, this will just be treated as a chromatic or out-of-key root
    #             assumed_degree = root_interval.degree
    #             root_degrees.append(assumed_degree)
    #             root_degree_offsets.append(None)
    # else:
    #     # all chord roots are in this key,
    #     # so all offsets are 0 by definition:
    #     root_degree_offsets = [0] * len(root_degrees)
    #
    # chords_degrees_offsets = zip(chordlist, root_degrees, root_degree_offsets)
    # numerals = [] # build a list of numerals, allocating case as we go
    # for ch, deg, offset in chords_degrees_offsets:
    #     # use the quality of the chord if it is not indeterminate, otherwise use the quality of the key:
    #     chord_qual = ch.quality if not ch.quality.perfect else key.quality
    #     if chord_qual.major_ish:
    #         numeral = parsing.numerals_roman[deg]
    #     elif chord_qual.minor_ish:
    #         numeral = parsing.numerals_roman[deg].lower()
    #     else:
    #         raise Exception(f'Could not figure out whether to make numeral upper or lowercase: {d}:{c} in {key} (should never happen)')
    #
    #     # get the chord suffix, but ignore any suffix that means 'minor'
    #     # because minor-ness is already communicated by the numeral's case
    #     suffix = ch.suffix
    #     if (len(suffix)) > 0 and (suffix[0] == 'm') and (not ch.quality.major_ish):
    #         suffix = suffix[1:]
    #
    #     # turn suffix modifiers into superscript marks etc. where possible:
    #     suffix = ''.join(reduce_aliases(suffix, parsing.modifier_marks))
    #
    #     # # place leading numbers in superscript:
    #     # leading_numbers = [] # will be list of integer strings
    #     # is_leading = False
    #     # rest_index = len(suffix)
    #     # for i,s in enumerate(suffix):
    #     #     if s.isnumeric():
    #     #         is_leading = True
    #     #         leading_numbers.append(s)
    #     #     else:
    #     #         if is_leading:
    #     #             rest_index = i # start of non-leading part of string
    #     #             break
    #     # # leading_numbers = ''.join(leading_numbers) # cast to str
    #     # rest = suffix[rest_index:] # everything after leading numbers
    #     # leading_numbers_super = ''.join([parsing.superscript[s] for s in leading_numbers])
    #     # suffix = leading_numbers_super + rest
    #
    #     # if auto_superscript:
    #     #     # replace all superscriptable characters
    #
    #     # get inversion as integer degree rather than bass note:
    #     inv_string = '' if ch.inversion == 0 else f'/{ch.inversion}'
    #
    #     full_numeral = f'{numeral}{suffix}{inv_string}'
    #     # finally, prefix the numeral with flat or sharp if it's not in key:
    #     if offset is not None:
    #         prefix = '' if offset==0 else parsing.preferred_accidentals[offset]
    #         full_numeral = prefix + full_numeral
    #     else:
    #         # or wrap it in out-of-key brackets:
    #         lb, rb = _settings.BRACKETS['non_key_chord_root']
    #         full_numeral = lb + full_numeral + rb
    #
    #     numerals.append(full_numeral)

    # numerals = [numerals_roman[d]  if c.quality.major_ish else numerals_roman[d].lower()  for d,c in degree_chords]
    # add suffixes: (we ignore the 'm' suffix because it is denoted by lowercase instead)
    # if modifiers:
    #     suffix_list = [c.get_suffix(inversion=False) if c.get_suffix() != 'm' else '' for c in self]
    #     inversion_list = ['' if c.inversion==0 else f'/{c.inversion}' for c in self]
    #     roman_chords_list = [f'{numerals[i]}{suffix_list[i]}{inversion_list[i]}' for i in range(len(self))]
    #     # turn suffix modifiers into superscript marks etc. where possible:
    #     roman_chords_list = [''.join(reduce_aliases(r, modifier_marks)) for r in roman_chords_list]
    # else:
    #     roman_chords_list = [f'{numerals[i]}' for i in range(len(self))]




# TODO: key recognition routine that respects progression logic,
# i.e. looking for cadences or half cadences in the final root movement

def propose_root_motions(start, direction):
    """Given a root degree 'from', and a direction which should be one of 'D' (dominant)
    or 'SD' (subdominant), propose RootMotion continuations in that direction"""
    ...




common_progressions = {
    Progression('I IV V'  ) : '145',
    Progression('ii V I'  ) : '251',
    Progression('ii V i'  ) : 'minor 251',
    Progression('V IV I'  ) : '541',
    Progression('I vi V'  ) : '165',
    Progression('I V IV V') : '1545',

    Progression('I V vi IV'   ) : 'common',
    Progression('I V ♭VII IV' ) : 'common (variant)',
    Progression('I vi IV V'   ) : '50s',
    Progression('i VII VI V'  ) : 'andalusian',
    Progression('vi IV V I'   ) : 'komuro', # better as rotation/transposition of 50s progression?

    Progression('ii V I V' ) : 'jazz turnaround',

    Progression('I⁷ IV⁷ ii⁷ V⁷') : 'montgomery-ward bridge',
    Progression('v⁷ I⁷ IV IV vi⁷ II⁷ ii⁷ V⁷'): 'full montgomery-ward bridge',

    Progression('I⁷ IV⁷ I⁷ V⁷      I⁷') : 'blues',
    Progression('I⁷ IV⁷ I⁷ V⁷  IV⁷ I⁷') : 'shuffle blues',
    Progression('i⁷ iv⁷ i⁷ ♭VI⁷ V⁷ I⁷') : 'minor blues',
    Progression('III⁷ VI⁷ II⁷ V⁷ I'   ) : 'ragtime',

    Progression('vi ii V I'  ) : 'circle',
    Progression('VI ii° V i' ) : 'circle minor',
    Progression('I IV vii° iii vi ii V'     ): 'full circle',
    Progression('i iv VII  III VI ii° V i'  ): 'full circle minor',

    Progression('IVᐞ⁷ V⁷   iii⁷ vi' ): 'royal road',
    Progression('VIᐞ⁷ VII⁷ v⁷   i ' ): 'royal road minor',
    Progression('iv⁷  v⁷   IIIᐞ⁷ VI'): 'royal road minor (variant)',
    Progression('IVᐞ⁷ V⁷   iii⁷  vi⁷ ii⁷ V⁷ I'): 'full royal road',
    Progression('iv⁷  v⁷   IIIᐞ⁷ VI iiø⁷ V⁷ i'): 'full royal road minor',

    Progression('I   V⁷  i VII III VII i V⁷ i'): 'folia',
    Progression('III VII i V   III VII i V  i'): 'romanesca',
    Progression('i   VII i V   III VII i V  i'): 'passamezzo antico',
    Progression('i   VII i V'                 ): 'passamezzo antico (first phrase)',
    Progression('               III VII i V i'): 'passamezzo antico (second phrase)',
    }

common_simple_progressions = {p.simplify(): name for p,name in common_progressions.items()}

common_progressions_by_name = reverse_dict(common_progressions)
