### this progressions module is incomplete, very WIP at the moment

from .intervals import Interval
from .chords import Chord, AbstractChord, ChordList
from .qualities import Major, Minor, Perfect, Diminished, parse_chord_modifiers, ChordModifier
from .scales import Scale, ScaleChord, NaturalMajor, NaturalMinor, MelodicMinor, HarmonicMinor, MelodicMajor, HarmonicMajor
from .keys import Key, KeyChord # matching_keys, most_likely_key
from .util import reduce_aliases, check_all, reverse_dict, log
from .parsing import roman_numerals, numerals_roman, auto_split, superscript, fl, sh, nat
from . import parsing, _settings

from collections import Counter

# import numpy as np  # not needed yet



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
# kludge: we have to specifically ignore 'dim' when reading roman numerals,
# because it is the only modifier that contains a roman numeral ('i')
progression_aliases['dim'] = 'dim'

minor_mod = ChordModifier('minor')

def parse_roman_numeral(numeral):
    """given a (string) roman numeral, in upper or lower case,
    with a potential chord modifier at the end,
    parse into a (degree, AbstractChord) tuple, where degree is an int between 1-7"""
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
        return(f'[{self.function_char}]{self.degrees}:{self.direction_str}')

    def __repr__(self):
        return str(self)

    _movement_marker = _settings.MARKERS['right']
    _up_arrow = _settings.MARKERS['up']
    _down_arrow = _settings.MARKERS['down']



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
            """

        # unpack tuple arg:
        if len(numerals) == 1:
            numerals = numerals[0]

        if isinstance(numerals, str):
            original_numerals = numerals
            split_numerals = auto_split(numerals, allow='°øΔ♯♭♮+𝄫𝄪#/' + ''.join(parsing.modifier_marks.values()))
            assert len(split_numerals) > 1, f"Expected a string of roman numerals separated by dashes (or other obvious separator), but got: {numerals[0]}"
            numerals = split_numerals
        # is now an iterable of roman numeral strings OR of integers

        if check_all(numerals, 'isinstance', str):
            # roman numeral strings
            # which we parse into AbstractChords based on their case and suffixes
            base_degree_chords = [parse_roman_numeral(n) for n in numerals] # degree, AbstractChord tuples
            self.root_degrees = [d[0] for d in base_degree_chords]

            # log(f'Base (unscaled) degree chords:')
            # for r,c in base_degree_chords:
                # log(f'{r}: {c}')

            if scale is None:
                # build chords as specified from numerals and detect scale afterward
                self.chords = ChordList([d[1] for d in base_degree_chords])
                self.scale = self._detect_scale(base_degree_chords)

            else:
                # scale is provided, so we simply instantiate it
                # and, if needed, check degree chords against it
                if isinstance(scale, str):
                    scale = Scale(scale)
                # assert isinstance(scale, Scale)
                self.scale = scale

                if ignore_conflicting_case:
                    # ignore case (but not modifiers) of roman numeral chords provided
                    # and instantiate them from scale instead:
                    scale_chords = ChordList([self.scale.chord(d) for d in self.root_degrees])
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
                self.chords = ChordList([self.scale.chord(d, order=order) for d in self.root_degrees])
            else:
                # use the abstractchords we have been given (and cast them to abstract)
                self.chords = ChordList(chords).abstract()

        else:
            raise ValueError(f'Progression init ended up with an iterable of mixed types, expected all ints or all strings but got: {numerals}')

        self.abstract_chords = chords # true for Progression class, not for ChordProgression

        # scaledegree, chord pairs:
        self.degree_chords = [(self.root_degrees[i], self.chords[i]) for i in range(len(self))]

        self.numerals = self._as_numerals(sep=None)

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

    def analyse(self, display=False, ret=True):
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
        if display:
            print('\n'.join(out))
        if ret:
            return '\n'.join(out)

    def analyze(self, *args, **kwargs):
        """see Progression.analyse (this is just a quality-of-life alias for American spelling)"""
        return self.analyse(*args, **kwargs)

    @property
    def analysis(self):
        return self.analyse(display=True, ret=False)

    def _as_numerals(self, sep='  ', check_scale=False):
        numerals = []
        for d,c in self.degree_chords:
            # use the quality of the chord if it is not indeterminate, otherwise use the quality of the key:
            chord_mod = c.quality if not c.quality.perfect else self.scale.quality
            if chord_mod.major_ish:
                numerals.append(numerals_roman[d])
            elif chord_mod.minor_ish:
                numerals.append(numerals_roman[d].lower())
            else:
                raise Exception(f'Could not figure out whether to make numeral upper or lowercase: {d}:{c} in {key} (should never happen)')

        # add suffixes: (we ignore the 'm' suffix because it is denoted by lowercase instead)
        suffix_list = [c.suffix if c.suffix != 'm' else '' for c in self.chords]
        # pull inversions out of suffixes:
        for i in range(len(suffix_list)):
            chord, suf = self.chords[i], suffix_list[i]
            if '/' in suf:
                # slash chord detected
                new_slash = parsing.superscript['/']
                new_inv = ''.join([parsing.superscript[s] for s in str(chord.inversion)])
                new_suf = f'{new_slash}{new_inv}'
                suffix_list[i] = new_suf

        roman_chords_list = [f'{numerals[i]}{suffix_list[i]}' for i in range(len(self))]

        if check_scale:
            # annotate chords that are chromatic to the scale with square brackets
            # or, if they are at least in the corresponding harmonic/melodic scale, mark that too:
            if self.scale.is_natural():
                if self.scale == NaturalMinor:
                    # natural minor scale
                    harmonic_scale = HarmonicMinor
                    melodic_scale = MelodicMinor
                elif self.scale == NaturalMajor:
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
                        new_roman_chords.append(f'{orig[0]}{orig[1:]}\u036A')
                    elif belongs_melodic[i]:
                        # mark first character with combining 'm':
                        new_roman_chords.append(f'{orig[0]}{orig[1:]}\u036B')
                    else:
                        # mark out-of-scale chord with brackets:
                        new_roman_chords.append(f'[{orig}]')
                roman_chords_list = new_roman_chords
            else:
                # non-natural scale: just check raw scale compatibility
                belongs = [self.scale.contains_degree_chord(d,c) for d,c in self.degree_chords]
                roman_chords_list = [f'{roman_chords_list[i]}' if belongs[i]  else f'[{roman_chords_list[i]}]'  for i in range(len(self))]

        # turn suffix modifiers into superscript marks etc. where possible:
        roman_chords_list = [''.join(reduce_aliases(r, parsing.modifier_marks)) for r in roman_chords_list]
        if sep is not None:
            roman_chords_str = sep.join(roman_chords_list)
            return roman_chords_str
        else:
            # just return the raw list, instead of a sep-connected string
            return roman_chords_list

    def in_key(self, key, **kwargs):
        """returns a ChordProgression with these chords over a specified Key object"""
        # cast to Key object:
        if isinstance(key, str):
            key = Key(key)
        assert isinstance(key, Key)
        key_chords = []
        for d,c in self.degree_chords:
            root = key.degree_notes[d]
            key_chords.append(c.on_root(root))
        return ChordProgression(key_chords, key=key, **kwargs)

    def on_tonic(self, tonic, **kwargs):
        """uses the existing set or detected .scale attribute and returns a ChordProgression
        in the Key of that scale which starts on the desired tonic"""
        key = self.scale.on_tonic(tonic)
        return self.in_key(key, **kwargs)

    @property
    def diagram(self):
        from .guitar import standard # lazy import
        standard.show(self)

    def __len__(self):
        return len(self.root_degrees)

    def __str__(self):
        scale_name = self.scale.name
        if 'natural' in scale_name:
            scale_name = scale_name.replace('natural ', '')
        lb, rb = self._brackets
        return f'Progression:  {lb}{self._as_numerals(check_scale=True)}{rb}  (in {scale_name})'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        """progressions are emod to each other if they have the same chords built on the same degrees"""
        return self.degree_chords == other.degree_chords

    def __add__(self, other):
        """Addition defined over Progressions:
            1. Progression + integer tranposes this progression's roots upward by that many degrees
            2. Progression + roman numeral returns a new Progression with that numeral appended to it"""
        if isinstance(other, int):
            new_root_degrees = [r + other for r in self.root_degrees]
            # mod to range 1-7:
            new_root_degrees = [((r-1) % 7) + 1 for r in new_root_degrees]
            return Progression(numerals=new_root_degrees, chords=self.chords, scale=self.scale)
        elif isinstance(other, str):
            new_numerals = self.numerals + [other]
            return Progression(new_numerals, scale=self.scale)
        elif isinstance(other, (list, tuple)):
            # assume this is a list or tuple of roman numerals:
            new_numerals = self.numerals + list(other)
            return Progression(new_numerals, scale=self.scale)
        elif isinstance(other, Progression):
            new_numerals = self.numerals + other.numerals
            return Progression(new_numerals, scale=self.scale)

    def pad_with_tonic(self):
        """returns a new Progression that is this one but with an added tonic of the appropriate quality,
        if this one does not already end on a tonic"""
        if self.root_degrees[-1] != 1:
            tonic_char = 'I' if self.scale.quality.major else 'i'
            return self + tonic_char
        else:
            return self

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




class ChordMovement:
    """Movement of root and every other chord degree from one to another"""
    def __init__(self, start_chord, end_chord, key):
        self.start_chord = start_chord
        self.end_chord = end_chord
        self.key = key
        self.scale = key.scale

        # experimental, WIP
        import numpy as np
        distance_matrix = np.zeros((len(start_chord), len(end_chord)))
        for r, n1 in enumerate(start_chord.notes):
            for c, n2 in enumerate(end_chord.notes):
                deg1, deg2 = key.note_degrees[n1], key.note_degrees[n2]
                movement = DegreeMovement(deg1, deg2, scale=key.scale)
                distance_matrix[r,c] = movement.distance

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

        if key is None:
            # detect most likely key:
            self.key = self.chords.find_key(natural_only = search_natural_keys_only)
        else:
            self.key = key if isinstance(key, Key) else Key(key)
        # and rip out its scale:
        self.scale = Scale(self.key.scale)

        self.roots = [c.root for c in self.chords]
        self.root_degrees = [self.key.note_degrees[n] for n in self.roots]
        self.degree_chords = [(self.root_degrees[i], self.chords[i]) for i in range(len(self))]

        self.numerals = self._as_numerals(sep=None)

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


    def abstract(self):
        """returns the abstract Progression object corresponding to this ChordProgression"""
        return Progression(self.numerals, scale=self.key.scale)

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
            return Progression(numerals=new_root_degrees, chords=self.chords, scale=self.scale)
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

    def __str__(self):
        # numerals = self.as_numerals()
        # chord_names = ' '.join([c.short_name for c in self.chords])
        lb, rb = self._brackets
        return f'{self.chords}  or  {lb}{self._as_numerals(check_scale=True)}{rb}  (in {self.key.name})'

    # def __repr__(self):
    #     return str(self)

def chordlist_numerals_in_key(chordlist, key, sep=' ', modifiers=True, auto_superscript=True):
    """given a chordlist and a key, produces the roman numerals
    that describe those chords in that key"""
    # recast args if needed:
    if not isinstance(chordlist, (ChordList)):
        chordlist = ChordList(chordlist)
    if not isinstance(key, Key):
        key = Key(key)

    root_degrees = chordlist.root_degrees_in(key)
    scale_chords = [ch.in_scale(key.scale, degree=root_degrees[i]) for i,ch in enumerate(chordlist)]

    numerals = [ch.numeral for ch in scale_chords]

    if sep is not None:
        roman_chords_str = sep.join(numerals)
        return roman_chords_str
    else:
        # just return the raw list, instead of a sep-connected string
        return numerals

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

def propose_root_movements(start, direction):
    """Given a root degree 'from', and a direction which should be one of 'D' (dominant)
    or 'SD' (subdominant), propose DegreeMovement continuations in that direction"""
    ...




common_progressions = {
    Progression('I-iv-IV-V',        scale='major') : '4 chord song',
    Progression('ii-V-I',           scale='minor') : 'jazz',
    Progression('ii-V-I-V',         scale='minor') : 'jazz turnaround',
    Progression('I7-IV7-I7-V7',     scale='major') : 'blues',
    Progression('I7-IV7-I7-V7-IV7', scale='major') : 'blues turnaround',
    }
