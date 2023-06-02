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
                    1: "ST", # m2, supertonic
                    2: "ST", # M2, supertonic
                    3: "M", # m3, mediant
                    4: "M", # M3, mediant
                    5: "S", # 4th, subdominant
                    6: "?",
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

minor_qual = ChordQualifier('minor')

def parse_roman_numeral(numeral):
    """given a (string) roman numeral, in upper or lower case,
    with a potential chord qualifier at the end,
    parse into a (degree, AbstractChord) tuple, where degree is an int between 1-7"""
    out = reduce_aliases(numeral, progression_aliases)
    assert isinstance(out[0], tuple) # an integer, quality tuple
    deg, quality = out[0]

    qualifiers = []

    if quality.minor:
        qualifiers.append(minor_qual)

    if len(out) > 1: # got one or more additional qualifiers as well
        rest = ''.join(out[1:])
        rest_quals = parse_chord_qualifiers(rest)
        qualifiers.extend(rest_quals)

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
                items = auto_split(arg, allow='°øΔ♯♭♮+𝄫𝄪#/' + ''.join(qualifier_marks.values()))
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
        return '𝄃 ', ' 𝄂'
        # return '╟', '╢'
        # return '𝄆', '𝄇'

    def __str__(self):
        # return f'𝄃{super().__repr__()}𝄂'
        lb, rb = self._brackets
        sep_char = ' - '
        # if any of the chords in this progression are AbstractChords, use a different sep char
        # (because AbstractChords have spaces in their names)
        for c in self:
            if type(c) == AbstractChord:
                sep_char = ' - '
                break
        return f'{lb}{sep_char.join([n.name for n in self])}{rb}'

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

    # def matching_keys(self, *args, **kwargs):
    #     """just wraps around keys.matching_keys module function"""
    #     return matching_keys(self, *args, **kwargs)

    def root_degrees_in(self, key):
        if isinstance(key, str):
            key = Key(key)
        assert isinstance(key, Key), f"key input to ChordList.root_degrees_in must be a Key or string that casts to Key, but got: {type(key)})"
        root_intervals_from_tonic = [c.root - key.tonic for c in self]
        root_degrees = [key.interval_degrees[iv]  if iv in key  else iv.degree  for iv in root_intervals_from_tonic]
        return root_degrees

    def as_numerals_in(self, key, sep=' ', qualifiers=True):
        if isinstance(key, str):
            key = Key(key)
        root_degrees = self.root_degrees_in(key)
        degree_chords = zip(root_degrees, self)
        numerals = [] # build a list of numerals, allocating case as we go
        for d,c in degree_chords:
            # use the quality of the chord if it is not indeterminate, otherwise use the quality of the key:
            chord_qual = c.quality if not c.quality.perfect else key.quality
            if chord_qual.major_ish:
                numerals.append(numerals_roman[d])
            elif chord_qual.minor_ish:
                numerals.append(numerals_roman[d].lower())
            else:
                raise Exception(f'Could not figure out whether to make numeral upper or lowercase: {d}:{c} in {key} (should never happen)')

        # numerals = [numerals_roman[d]  if c.quality.major_ish else numerals_roman[d].lower()  for d,c in degree_chords]
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

    def find_key(self, verbose=True):
        """wraps around matching_keys but additionally uses cadence information to distinguish between competing candidates"""
        matches = matching_keys(chords=self, return_matches=True, min_likelihood=0, max_results=12, require_tonic=True, require_roots=True,
                                upweight_first=False, upweight_last=False, upweight_chord_roots=False, upweight_key_tonics=False)

        if len(matches) == 0:
            # if no matches at all first, open up the min recall property:
            matches = matching_keys(chords=self, return_matches=True, min_recall=0, min_likelihood=0, max_results=12, 
                                    require_tonic=True, require_roots=True,
                                    upweight_first=False, upweight_last=False, upweight_chord_roots=False, upweight_key_tonics=False)
            if len(matches) == 0:
                # open up everything:
                matches = matching_keys(chords=self, return_matches=True, min_recall=0, min_precision=0, min_likelihood=0, max_results=12,
                                        require_tonic=True, require_roots=True,
                                        upweight_first=False, upweight_last=False, upweight_chord_roots=False, upweight_key_tonics=False)
                if len(matches) == 0:
                    raise Exception(f'No key matches at all found for chords: {self} \n(this should never happen!)')
        # try ideal matches (with perfect recall) first:
        ideal_matches = [(c,s) for c,s in matches.items() if s['recall'] == 1.0]

        if len(ideal_matches) == 0:
            # no good matches, so open up to all matches that share the max recall:
            max_rec = max([s['recall'] for c,s in matches.items()])
            max_rec_matches = [(c,s) for c,s in matches.items() if s['recall'] == max_rec]
            match_tuples = max_rec_matches
            log('No ideal matches with perfect recall')
            log(f'So opened up to all {len(match_tuples)} matches tied for the highest recall')
        else:
            log(f'Found {len(ideal_matches)} candidate/s with perfect recall')
            # at least one ideal match, so we'll focus on those
            match_tuples = ideal_matches

        if len(match_tuples) == 1:
            log(f'Only one candidate for key: {match_tuples}')
            # only one good match, so use it
            key = match_tuples[0][0]
            print(f'Found key: {key}')

        elif len(match_tuples) >= 2:
            # multiple good matches, see if one has better precision than the other
            max_prec = max([s['precision'] for c,s in match_tuples])
            precise_matches = [(c,s) for c,s in match_tuples if s['precision'] == max_prec]
            log(f'Multiple candidates for key: {[m[0].name for m in match_tuples]}')
            log(f' So focusing on the {len(precise_matches)} tied for highest precision')
            if len(precise_matches) == 1:
                # one of the perfect-recall matches is better than all the others, so use it (probably?)
                key = precise_matches[0][0]
                print(f'Found key: {key}')

            # elif len(best_matches) == 2:
            #     # is one major and the other minor?
            #     m1, m2 = best_matches[0][0], best_matches[1][0]
            #     if (m1.quality.major and m2.quality.minor) or (m1.quality.minor and m2.quality.major):
            #         # decide between major and minor candidate keys:
            #         candidate_progressions = [Progression(self.as_numerals_in(k)) for k in [m1, m2]]

            else:
                # multiple matches that are equally as good,
                # so look for a cadence-based match around V-I resolutions or something
                # log(f'Reducing the shortlist to those tied for highest likelihood')
                # max_likely = max([s['likelihood'] for c,s in match_tuples])
                # likely_matches = [(c,s) for c,s in match_tuples if s['likelihood'] == max_likely]
                candidate_keys = [m[0] for m in precise_matches]
                log(f'Testing {len(candidate_keys)} candidate keys for grammaticity of this progression in those keys')
                candidate_progressions = [Progression(self.as_numerals_in(k), scale=k.scale).in_key(k) for k in candidate_keys]
                log(f'Candidate keys: {", ".join([str(p.key) for p in candidate_progressions])}')
                grammatical_progressions = most_grammatical_progression(candidate_progressions, verbose=verbose)
                grammatical_keys = [p.key for p in grammatical_progressions]
                if len(grammatical_keys) == 1:
                    key = grammatical_keys[0]
                    log(f'Found one key more grammatical than the others: {str(key)}')
                else:
                    # multiple keys equally tied for how grammatical they are
                    # so tiebreak by likelihood:
                    log(f'Found multiple equally grammatical keys: {[str(k) for k in grammatical_keys]}')
                    log('So tie-breaking by key likelihood')
                    max_likely = max([k.likelihood for k in grammatical_keys])
                    likely_keys = [k for k in grammatical_keys if k.likelihood == max_likely]
                    
                    if len(likely_keys) == 1:
                        # one key is more common than the other
                        key = likely_keys[0]
                        log('One key is more likely than the others: {key}')
                    else:
                        # nothing else left, just tie-break by key consonance
                        keys_by_consonance = sorted(likely_keys, key=lambda x: x.consonance, reverse=True)
                        log(f'Found multiple equally likely keys: {[str(k) for k in keys_by_consonance]}')
                        log(f'So doing a final tie-break by consonance')
                        key = keys_by_consonance[0]
                    
                print(f'Found key: {key}')

        assert isinstance(key, Key)
        return key

    def play(self, delay=1, duration=2.5, octave=None, falloff=True, block=False, type='fast', **kwargs):
        """play this chordlist as audio"""
        chord_waves = [c._melody_wave(duration=duration, delay=0, octave=octave, type=type, **kwargs) for c in self]
        from .audio import arrange_melody, play_wave, play_melody
        play_melody(chord_waves, delay=delay, falloff=falloff, block=block)
        # prog_wave = arrange_melody(chord_waves, delay=delay, **kwargs)
        # play_wave(prog_wave, block=block)

# alias for easy access:
Chords = ChordList

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
            original_numerals = numerals
            split_numerals = auto_split(numerals, allow='°øΔ♯♭♮+𝄫𝄪#/' + ''.join(qualifier_marks.values()))
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
                assert type(scale) in [Scale, Subscale]
                self.scale = scale

                if ignore_conflicting_case:
                    # ignore case (but not qualifiers) of roman numeral chords provided
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
            assert type(scale) in [Scale, Subscale]
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

    def _as_numerals(self, sep=' ', check_scale=False):
        numerals = []
        for d,c in self.degree_chords:
            # use the quality of the chord if it is not indeterminate, otherwise use the quality of the key:
            chord_qual = c.quality if not c.quality.perfect else self.scale.quality
            if chord_qual.major_ish:
                numerals.append(numerals_roman[d])
            elif chord_qual.minor_ish:
                numerals.append(numerals_roman[d].lower())
            else:
                raise Exception(f'Could not figure out whether to make numeral upper or lowercase: {d}:{c} in {key} (should never happen)')

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
                        new_roman_chords.append(f'\u036A{orig[0]}{orig[1:]}')
                    elif belongs_melodic[i]:
                        # mark first character with combining 'm':
                        new_roman_chords.append(f'\u036A{orig[0]}{orig[1:]}')
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
        return f'Progression:  {lb} {self._as_numerals(check_scale=True)} {rb}  (in {scale_name})'

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        """progressions are equal to each other if they have the same chords built on the same degrees"""
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
    # take argmax of cadence count/score:
    max_cadences = max(cadence_scores)
    top_matches = []
    for i,c in enumerate(cadence_scores):
        if c == max_cadences:
            top_matches.append(i)

    
    for p,c in zip(progressions, cadence_scores):
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
    def __init__(self, *chords, key=None):

        if len(chords) == 1:
            chords = chords[0]

        if isinstance(chords, str):
            # if chords is a plain string instead of iterable,
            # try auto splitting:
            chords = auto_split(chords, allow='°øΔ♯♭♮+𝄫𝄪#/' + ''.join(qualifier_marks.values()))

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
            self.key = self.chords.find_key()

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

    def __str__(self):
        # numerals = self.as_numerals()
        # chord_names = ' '.join([c.short_name for c in self.chords])
        lb, rb = self._brackets
        return f'{self.chords}  or  {lb} {self._as_numerals(check_scale=True)} {rb}  (in {self.key.name})'

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
