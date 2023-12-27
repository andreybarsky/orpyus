### this progressions module is incomplete, very WIP at the moment

from .intervals import Interval
from .notes import Note, NoteList
from .chords import Chord, AbstractChord, ChordList
from .qualities import Major, Minor, Perfect, Diminished, parse_chord_modifiers, ChordModifier, modifier_aliases, minor_mod, dim_mod
from .scales import infer_chord_scale, infer_scale, Scale, ScaleChord, NaturalMajor, NaturalMinor
from .keys import Key, KeyChord, matching_keys# , most_likely_key
from .util import reduce_aliases, rotate_list, check_all, reverse_dict, log
from .parsing import auto_split, superscript, fl, sh, nat # roman_numerals, numerals_roman, modifier_marks,
from .numerals import RomanNumeral
from . import parsing, notes, scales
from .config import settings, def_progressions
from .config.def_progressions import common_progression_defines

from collections import Counter

# import numpy as np  # not needed yet

# global defaults:
default_diacs = settings.DEFAULT_PROGRESSION_DIACRITICS
default_marks = settings.DEFAULT_PROGRESSION_MARKERS

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





class Progression:
    """A theoretical progression between AbstractChords in a particular scale,
    initialised as list: e.g. Progression(['I', 'IV', 'iii', 'V'])
    or as string separated by dashes, e.g.: Progression('I-IV-iii-V')"""
    def __init__(self, *numerals, scale=None, chords=None, order=None, ignore_conflicting_case=False):
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

            # catch the special case of: we've been given a progression by name
            if numerals in common_progression_strs_by_name:
                # translate name to string of numerals:
                numerals = common_progression_strs_by_name[numerals]

            original_numerals = numerals
            # remove all diacritics:
            numerals = ''.join([c for c in numerals if c not in settings.DIACRITICS.values()])
            # and all scale marks:

            split_numerals = auto_split(numerals, allow='°øΔ♯♭♮+𝄫𝄪#/' + ''.join(parsing.modifier_marks.values()))
            assert len(split_numerals) > 1, f"Expected a string of roman numerals separated by dashes (or other obvious separator), but got: {numerals[0]}"
            numerals = split_numerals
        # is now an iterable of roman numeral strings OR of integers OR scalechords

        if check_all(numerals, 'isinstance', str):
            # roman numeral strings
            # which we parse into RomanNumeral objects:
            numerals = [RomanNumeral(rn) for rn in numerals]

        # now we can deal with RomanNumeral objects:
        if check_all(numerals, 'isinstance', RomanNumeral):

            self.numerals = numerals
            self.root_degrees = [rn.degree for rn in self.numerals]

            # base_degree_chord_params = [parse_roman_numeral(n, return_params=True) for n in numerals] # degree, AbstractChord tuples
            # self.root_degrees = [d[0] for d in base_degree_chord_params]
            base_degree_chords = [(rn.degree, AbstractChord.from_cache(modifiers=rn.modifiers, inversion=rn.inversion)) for rn in self.numerals]

            chord_degree_qualities = [(deg, ch.quality) for deg,ch in base_degree_chords]

            # determine scale from numerals provided, if scale not given:
            if scale is None:
                self.scale = infer_scale(chord_degree_qualities)
            elif isinstance(scale, str):
                self.scale = Scale(scale)
            else:
                self.scale = scale

            # catch a special case: have we been given flat degrees (like bVI) in a minor key,
            # which cannot be found because e.g. the minor VI is already flat?
            for i, (deg, ch) in enumerate(base_degree_chords):
                if isinstance(deg, float) and deg not in self.scale.fractional_degree_intervals:
                    # quietly re-parse but ignore accidental:
                    log(f'Progression given chord: {numerals[i]} but that altered root is already in scale')
                    # deg, ch = parse_roman_numeral(numerals[i], ignore_alteration=True)
                    rn = RomanNumeral(numerals[i])
                    base_degree_chords[i] = rn.natural_degree, ch
                    log(f'So quietly replaced with {rn} (in scale: {self.scale.name}')
                    self.root_degrees = [deg for (deg,ch) in base_degree_chords]


            # decide how to instantiate chords:
            if order is None:
                # take numerals as given, assume that they might contain suffixes like maj7 etc.
                degree_chords = base_degree_chords
                self.chords = ChordList([ch.in_scale(self.scale, degree=d) for d,ch in degree_chords])
            else:
                # override any detected roman numeral suffixes and construct tertian chords instead:
                # int_numerals = [num for num,chord in base_degree_chords]
                scale_chords = scale.chords(self.root_degrees, order=order)
                degree_chords = [(d,c) for d,c in zip(self.root_degrees, scale_chords)]
                self.chords = degree_chords

        elif check_all(numerals, 'isinstance', int):
            assert scale is not None, f'Progression chords given as integers but scale arg not provided'
            if isinstance(scale, str):
                scale = Scale(scale)
            assert type(scale) is Scale
            self.scale = scale
            self.root_degrees = numerals
            if order is None:
                order = 3 # triads by default
            if chords is None:
                # construct scale chords: (and here we check the order arg to make 7ths etc. if needed)
                if isinstance(order, int): # same order for each chord
                    order = [order] * len(numerals)
                else: # individual order for each chord
                    assert isinstance(order, (list,tuple)), f"'order' arg to Progression must be an int or list of ints, but got: {type(order)}"
                self.chords = ChordList([self.scale.chord(d, order=order[i], linked=True) for i,d in enumerate(self.root_degrees)])
            else:
                # use the abstractchords we have been given (and cast them to ScaleChords)
                self.chords = ChordList([ScaleChord(factors=chords[i].factors, inversion=chords[i].inversion, scale=self.scale, degree=d) for i,d in enumerate(self.root_degrees)])
            self.numerals = [ch.numeral for ch in self.chords]

        elif check_all(numerals, 'isinstance', ScaleChord):
            ### allow init by scalechords alone
            scalechord_scales = [ch.scale for ch in numerals]
            assert check_all(scalechord_scales, 'eq', scalechord_scales[0]), f"Non-matching scale attributes in ScaleChord list given to Progression: {scalechord_scales}"
            self.scale = scalechord_scales[0]
            self.chords = ChordList(numerals)
            self.numerals = [ch.numeral for ch in self.chords]
            self.root_degrees = [ch.scale_degree for ch in self.chords]

        else:
            raise ValueError(f'Progression init ended up with an iterable of mixed types, expected all ints or all strings but got: {numerals}')

        # note movements between each chord root:
        self.chord_root_intervals_from_tonic = [self.scale.degree_intervals[d] if d in self.scale.degree_intervals else self.scale.fractional_degree_intervals[d]  for d in self.root_degrees]
        self.root_movements = [RootMotion(self.root_degrees[i], self.root_degrees[i+1], scale=self.scale) for i in range(len(self)-1)]

        assert check_all(self.chords, 'isinstance', ScaleChord) # sanity check: progression chords are always ScaleChords




    def analyse(self, display=False, ret=True, roots=None):
        """shows the harmonic functions of the chords in this progression"""
        out = []
        from src.display import DataFrame
        if roots is None:
            df = DataFrame(['Function', '', 'Deg1', '', 'Deg2', '',
                             # 'Chd1', '', 'Chd2', '',
                             'Distance', '', 'Cadence', '', 'CadScore'])
        else:
            df = DataFrame(['Function', '', 'Deg1', '', 'Deg2', '',
                             'Chd1', '', 'Chd2', '',
                             'Distance', '', 'Cadence', '', 'CadScore'])
        num1s, num2s, c1s, c2s, mvs, cads = [], [], [], [], [], []
        #clean_numerals = self.as_numerals(marks=False, diacritics=False, sep='@').split('@')
        clean_numerals = self.numerals
        for i in range(len(self)-1):
            f = f'[{self.root_movements[i].function_char}]'
            arrow = self.root_movements[i]._movement_marker
            n1, n2 = clean_numerals[i], clean_numerals[i+1]
            ch1, ch2 = self.chords[i].short_name, self.chords[i+1].short_name,
            dist = str(self.root_movements[i].direction_str)
            cadence = self.root_movements[i].cadence
            cadence = cadence if (cadence != False) else ''
            score = self.root_movements[i].cadence_score
            # blank if 0:
            score = score if score > 0 else ''
            if roots is None:
                df.append([f, '  ', n1, arrow, n2, '  ',
                            # ch1, arrow, ch2, ' ',
                            dist, '  ', cadence, ' ', score])
            else:
                df.append([f, '  ', n1, arrow, n2, '  ',
                            ch1, arrow, ch2, ' ',
                            dist, '  ', cadence, ' ', score])

        if display:
            # construct dataframe object for human viewing
            title = str(self)
            print('\n' + title)
            # border between title and df:
            title_width = len(title)
            df_width = df.total_width(up_to_row=None, header=False, margin_size=0)
            print('=' * max([title_width, df_width]))
            df.show(header=False, header_border=False, margin='')
        if ret:
            return df

    analyze = analyse # QoL alias

    @property
    def analysis(self):
        return self.analyse(display=True, ret=False)

    # def to_numerals(self, sep=' ', modifiers=True, marks=default_marks, diacritics=default_diacs):
    #     """returns this Progression's representation in roman numeral form
    #     with respect to its Scale"""
    #
    #     numerals = [ch.get_numeral(modifiers=modifiers, marks=marks, diacritics=diacritics) for ch in self.chords]
    #
    #     if sep is not None:
    #         roman_chords_str = sep.join(numerals)
    #         return roman_chords_str
    #     else:
    #         # just return the raw list, instead of a sep-connected string
    #         return numerals
    # get_numerals = as_numerals = to_numerals # convenience aliases
    # @property
    # def numerals(self):
    #     return self.to_numerals()
    #
    # @property
    # def mod_numerals(self):
    #     """upper/lowercase numerals with chord type modifiers like 7, sus4, etc."""
    #     return self.to_numerals(sep=None, modifiers=True, marks=False, diacritics=False)
    #
    # @property
    # def simple_numerals(self):
    #     """just raw upper/lowercase numerals, no modifiers or diacritics etc."""
    #     return self.to_numerals(sep=None, marks=False, diacritics=False, modifiers=False)

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
        return [self.rotate(i) for i in range(1,len(self))]
    @property
    def rotations(self):
        return self.get_rotations()

    @property
    def diagram(self):
        from .guitar import standard # lazy import
        standard.show(self)

    def transpose_for_guitar(self, *args, **kwargs):
        """finds a nice key for playing these chords easily on guitar,
        with respect to guitar.standard_open_chord_names,
        by reverse-inheriting the ChordProgression method of the same name"""
        return self.on_tonic('Bb').transpose_for_guitar(*args, **kwargs)

    def __getitem__(self, i):
        return self.chords[i]

    def __len__(self):
        return len(self.root_degrees)

    def __str__(self, marks=default_marks, diacritics=default_diacs):
        scale_name = self.scale.name
        if 'natural' in scale_name:
            scale_name = scale_name.replace('natural ', '')
        lb, rb = self._brackets
        return f'Progression:  {lb}{" - ".join([str(rn) for rn in self.numerals])}{rb}  (in {scale_name})'
        # return f'Progression:  {lb}{self.to_numerals(marks=marks, diacritics=diacritics)}{rb}  (in {scale_name})'

    def __repr__(self):
        return str(self)

    def __hash__(self):
        chord_factors = tuple([ch.factors for ch in self.chords])
        chord_degrees = tuple([ch.scale_degree for ch in self.chords])
        return hash((chord_factors, chord_degrees, self.scale.factors))

    def __eq__(self, other):
        """progressions are emod to each other if they have the same chords built on the same degrees"""
        # built on the same degrees:
        return (self.chords == other.chords) and (self.root_degrees == other.root_degrees)

    def __add__(self, other):
        """Addition defined over Progressions:
            1. Progression + roman numeral returns a new Progression with that numeral appended to it"""
        if isinstance(other, (int, Interval)):
            raise TypeError('Progression cannot be transposed by interval (try on ChordProgression instead)')
        ### old transposition-by-degrees-within-key implementation: less useful than key transposition
        # if isinstance(other, int): # transpose upward/downward by integer degrees
            # new_root_degrees = [r + other for r in self.root_degrees]
            # # mod to range 1-7:
            # new_root_degrees = [((r-1) % 7) + 1
            #                     if isinstance(r, float) # i.e. catch fractional (float) degrees
            #                     else r                  # use ScaleDegree as normal
            #                     for r in new_root_degrees]
            # return Progression(new_root_degrees, chords=self.chords, scale=self.scale)
        if isinstance(other, str): # add a new chord (as roman numeral)
            new_numerals = self.numerals + [RomanNumeral(other)]
            return Progression(new_numerals, scale=self.scale)
        elif isinstance(other, RomanNumeral):
            new_numerals = self.numerals + [other]
            return Progression(new_numerals, scale=self.scale)
        elif isinstance(other, (list, tuple)): # add new chords as list of roman numeral strings
            assert check_all(other, 'isinstance', 'str'), f"Progression got added with list/tuple, expected to loop over roman numeral strings but got: {type(other[0])}"
            new_numerals = self.mod_numerals + list(other)
            return Progression(new_numerals, scale=self.scale)
        elif isinstance(other, Progression): # concatenate two progressions
            new_numerals = self.mod_numerals + other.mod_numerals
            new_chords = self.chords + other.chords
            return Progression(new_numerals, chords=new_chords, scale=self.scale)

    def shift(self, value, relative=False):
        """shifts the root degrees of this progression up or down by an integer.
        not included in addition operation as addition is reserved for key transposition,
        but this 'shift' operation is used for computing relative major/minor progressions."""
        # new_root_degrees = [r + value for r in self.root_degrees]
        # # mod to range 1-7:
        # new_root_degrees = [((r-1) % 7) + 1
        #                     if isinstance(r, float) # i.e. catch fractional (float) degrees
        #                     else r                  # use ScaleDegree as normal
        #                     for r in new_root_degrees]
        new_numerals = [rn + value for rn in self.numerals]
        new_scale = self.scale if not relative else self.scale.parallel
        return Progression(new_numerals, chords=self.chords, scale=new_scale)

    @property
    def relative(self):
        """returns the relative major or minor variant of this progression"""
        if self.scale.quality.major:
            return self.shift(2, relative=True)
        elif self.scale.quality.minor:
            return self.shift(-2, relative=True)
        else:
            raise MusicError(f'{self} is neither major or minor, so has no relative')
    @property
    def relative_minor(self):
        if self.scale.quality.major:
            return self.relative
        else:
            raise MusicError(f'{self} is not major, so has no relative minor')
    @property
    def relative_major(self):
        if self.scale.quality.minor:
            return self.relative
        else:
            raise MusicError(f'{self} is not minor, so has no relative major')


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

    def slice(self, start, stop):
        """return a new Progression as a sliced subset of this Progression,
        that starts on integer index 'start' and ends just before integer index 'stop'"""
        new_chords = self.chords[start:stop]
        return self.__class__(new_chords)

    # progression completion logic:
    def complete(self, model=None, display=True):
        if model is None:
            from src.harmony import default_harmonic_models
            # get the default model for this progression's scale:
            model = default_harmonic_models[self.scale]
        if display:
            model.complete(self, display=True)
        else:
            return model.complete(self, display=False)

    _brackets = settings.BRACKETS['Progression']

def most_grammatical_progression(progressions, add_resolution=True, return_scores=True, verbose=False):
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
        for j, movement in enumerate(p.root_movements):
            development = .5 + (j / len(p.root_movements))*.5 # upweight cadences toward the end
            if movement.cadence:
                cadence_counts[i] += 1
                cadence_scores[i] += movement.cadence_score * development
        # normalise by progression length: (to compensate for added implied resolutions)
        cadence_scores[i] = round( cadence_scores[i] / len(p),  3)

    # take argmax of cadence count/score:



    for p,c in zip(progressions, cadence_scores):
        log(f'\nTesting key: {p.key}')
        if verbose:
            if add_resolution:
                p.pad_with_tonic().analysis
            else:
                p.analysis
        log(f'cadence score:{c})\n', force=verbose)



    if return_scores:
        score_dct = {progressions[i].key: cadence_scores[i] for i in range(len(progressions))}
        ranked_keys = sorted([p.key for p in progressions], key=lambda k: -score_dct[k])
        ranked_dct = {k: score_dct[k] for k in ranked_keys}
        return ranked_dct
    else:
        # just return a list of those with the best cadence scores
        max_cadences = max(cadence_scores)
        top_matches = []
        for i,c in enumerate(cadence_scores):
            if c == max_cadences:
                top_matches.append(i)
        matching_progressions = [progressions[i] for i in top_matches]
        return matching_progressions


class ChordProgression(Progression): # , ChordList):
    """ChordList subclass defined additionally over a specific key"""
    def __init__(self, *chords, key=None, search_natural_keys_only=True, verbose=False):
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
                ch = Chord.from_cache(item)

            elif isinstance(item, (list, tuple)): # unpackable parameters that we try to cast to Chord
                ch = Chord(*item)
            elif isinstance(item, dict):
                # unpack keyword args to cast to chord
                ch = Chord(**dict)
            else:
                raise ValueError(f'Expected iterable to contain Chords, or items that can be cast as Chords, but got: {type(item)}')

            valid_chords.append(ch)

        base_chords = ChordList(valid_chords)

        if key is None:
            # detect most likely key:
            if len(keychord_keys) > 0:
                # accept key from KeyChord attributes
                assert check_all(keychord_keys, 'eq', keychord_keys[0]), f"Non-matching key attributes in KeyChord list given to ChordProgression: {keychord_keys}"
                self.key = keychord_keys[0]
            else:
                self.key = self.find_key(chords=base_chords, verbose=verbose)
        else:
            self.key = key if isinstance(key, Key) else Key(key)

        self.scale = Scale(self.key.scale)
        self.roots = NoteList([ch.root for ch in base_chords])
        self.basses = NoteList([ch.bass for ch in base_chords])

        self.root_degrees = [self.key.note_degrees[n] if n in self.key.note_degrees else self.key.fractional_note_degrees[n] for n in self.roots]

        # form KeyChords (if they are not all already keychords)
        if len(keychord_keys) == len(base_chords):
            log(f'Not recasting ChordProgression input chords to KeyChords, as they are already KeyChords: {base_chords}')
            self.chords = base_chords
        else:
            self.chords = ChordList([KeyChord(factors=ch.factors, inversion=ch.inversion, root=ch.root,
                                        key=self.key, degree=d,
                                        assigned_name=ch.assigned_name, prefer_sharps=self.key.prefer_sharps)
                                     for ch,d in zip(base_chords, self.root_degrees)])

        self.numerals = [ch.numeral for ch in self.chords]

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
        """Addition defined over ChordProgressions.
            Addition with interval (or int) is transposition, otherwise concatenation.
        1. ChordProgression + Interval (or integer) returns the same progression in a new Key,
            transposed up that many semitones (with the same root degrees, i.e. transposed chord roots)
        2. ChordProgression + roman numeral returns a new ChordProgression with that numeral appended to it
        3. ChordProgression + Chord returns a new ChordProgression with that chord appended to it"""
        #### transposition
        if isinstance(other, (int, Interval)):
            new_key = self.key + other
            log(f'- Transposing {self} to {new_key}')
            return self.in_key(new_key)
        elif isinstance(other, str):
            # check if a roman numeral:
            if other.upper() in roman_numerals:
                new_numerals = self.mod_numerals + [other]
                return Progression(new_numerals, scale=self.scale).in_key(self.key)
            else:
                # assume this is a string that casts to Chord
                other = Chord(other)

        #### concatenation:
        if isinstance(other, Chord):
            new_chords = self.chords + other
            return ChordProgression(new_chords, key=self.key)

        elif isinstance(other, (list, tuple)):
            # if the first item is a numeral, assume the rest are numerals:
            if parsing.begins_with_roman_numeral(other[0]): # .upper() in roman_numerals:
                new_numerals = self.mod_numerals + list(other)
                return Progression(new_numerals, scale=self.scale).in_key(self.key)
            else:
                # assume these are Chords, or strings that cast to Chords
                new_chords = ChordList(self.chords + other)
                return ChordProgression(new_chords, key=self.key)

        elif isinstance(other, Progression):
            new_numerals = self.mod_numerals + other.mod_numerals
            return Progression(new_numerals, scale=self.key.scale).in_key(self.key)

        else:
            raise TypeError(f'ChordProgression.__add__ not implemented for type: {type(other)}')

    def __sub__(self, other):
        """subtraction with Interval"""
        if isinstance(other, (int, Interval)):
            new_prog = (self + -other)
            return new_prog
        else:
            raise TypeError(f'ChordProgression.__sub__ not implemented for type: {type(other)}')

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

    _brackets = settings.BRACKETS['ChordProgression']

    def long_str(self):
        # numerals = self.as_numerals()
        # chord_names = ' '.join([c.short_name for c in self.chords])
        lb, rb = self._brackets
        return f'{self.chords}  or  {lb}{self.to_numerals()}{rb}  (in {self.key.name})'

    def get_numeral_str(self, sep =' - ', modifiers=True):
        """returns a single string corresponding to this Progression's defining numerals"""
        if modifiers:
            numeral_strs = [str(rn) for rn in self.numerals]
        else:
            numeral_strs = [str(rn) for rn in self.numerals]

    def __str__(self, marks=default_marks, diacritics=default_diacs, chords_only=False, degrees_only=False):
        lb, rb = self._brackets
        # numerals = self.to_numerals(marks=marks, diacritics=diacritics, sep='@')
        numerals_placeholder = '@'.join([str(rn) for rn in self.numerals])
        split_numerals = numerals_placeholder.split('@')
        # chord_name_list = [ch.compact_name for ch in self.chords]
        num_chords = zip(split_numerals, self.chords)
        if chords_only:
            prog_str = ' '.join([f'{Chord.get_short_name(ch)}' for num, ch in num_chords])
        elif degrees_only:
            prog_str = ' '.join([f'{num}' for num, ch in num_chords])
        else: # i.e. both chords AND degrees
            prog_str = ' - '.join([f'{ch.compact_name}' for num, ch in num_chords])
        # return f'{self.chords}  (in {self.key.name})'
        return f'ChordProgression (in {self.key.name}):  {lb}{prog_str}{rb}'

    def __repr__(self, marks=default_marks, diacritics=default_diacs):
        """ChordProgression repr comes out as a table
        with chords above and scale degrees below"""
        numerals_placeholder = '@'.join([str(rn) for rn in self.numerals])
        split_numerals = numerals_placeholder.split('@')
        chord_names = [ch.chord_name for ch in self.chords]
        from src.display import DataFrame
        df = DataFrame(['' for c in range(len(self))])
        df.append(chord_names) # chord row
        df.append(split_numerals) # degrees row
        return df.show(header=False, header_border=False, margin=' - ', fix_widths=True,
                       return_string=True, title=str(self.key), align='centre')

    def chord_motions(self):
        for i in range(1, len(self)):
            ch1, ch2 = self.chords[i-1], self.chords[i]
            motion = KeyChordMotion(ch1, ch2, key=self.key)
            print(motion.interval_distances, '\n')

    def voice_table(self, disp=True, as_pretty_df=True):
        ### experimental: needs a better name (and Progression main class implementation)
        from src.display import Grid
        # import pandas as pd

        arr = Grid((len(self.chords), 12))
        # arr = np.zeros((len(self.chords), 12), dtype=int)
        for i, ch in enumerate(self.chords):
            if disp:
                pos_char = '+'
                neg_char = ' '
            else:
                pos_char = 1
                neg_char = 0
            note_array = [pos_char  if n in ch.notes else neg_char for n in notes.chromatic_notes]
            arr[i] = note_array

        arr.row_labels = [ch.chord_name for ch in self.chords]

        # note labels depend on the sharp preference of this progression's key:
        note_list = notes.chromatic_sharp_notes if self.key.prefer_sharps else notes.chromatic_flat_notes
        arr.col_labels = note_list

        if disp:
            print(arr)
        else:
            return arr

        # df = pd.DataFrame(arr, index=[str(ch.unkey()) for ch in self.chords], columns=[f'{n.chroma:<2}' for n in chromatic_notes])
        # return df

    def find_chromatic_lines(self, min_length=3, max_length=None, allowed_breaks=0, disp=True, _return_table=False):
        print(f'Searching for chromatic lines in\n  {self.__str__(chords_only=True)} ...\n')
        if max_length is None:
            max_length = len(self)+1
        voice_table = self.voice_table(disp=False)
        # if disp:
        #     print(str(voice_table).replace('1', '+').replace('0', ' '))
        chromatic_notes = voice_table.col_labels
        lines = {}
        proposed_lines = {}

        ruled_out = set()
        # try starting on each row, provided there's enough space to find a min-length line:
        for start_row in range(len(self)-(min_length-1)):
            # start locs are the places in this row where each note occurs:
            line_start_locs = [i for i,val in enumerate(voice_table[start_row]) if val]
            left_dir, right_dir = (-1, +1)
            left_name, right_name = 'falling', 'rising'

            for start_loc in line_start_locs: # i.e. columns
                for dir, dir_name in zip([left_dir, right_dir], [left_name, right_name]):
                    # don't search if this would overlap with an existing line in the same direction:
                    if (start_row-1, start_loc - dir, dir) not in lines:
                        # the list 'line' is a list of (row, col, note) tuples, which we start here:
                        start_note = chromatic_notes[start_loc]
                        line = [(start_row, start_loc, start_note)]
                        proposed_line = [(start_row, start_loc, start_note, True)] # same but for theoretical lines that might exist
                        log(f'Starting a {dir_name} line at: {start_row, start_loc}, on chord: {self.chords[start_row].name} beginning: {line[0]}')
                        true_line_broken, line_broken = False, False
                        line_breaks = 0
                        next_row = start_row + 1
                        next_loc = (start_loc + dir) % 12 # mod so as to wrap arond from C to B
                        while (not line_broken) and not (next_row >= len(self)):
                            this_note = chromatic_notes[next_loc]
                            if voice_table[next_row, next_loc]:
                                # if a note exists on that diagonal:
                                log(f' Line continues on chord: {self.chords[next_row].name} with: {this_note}')
                                if not true_line_broken:
                                    line.append((next_row, next_loc, this_note))
                                proposed_line.append((next_row, next_loc, this_note, True))
                                next_row = next_row + 1
                                next_loc = (next_loc + dir) % 12
                            else:
                                true_line_broken = True # the 'true line' is no longer valid,
                                                        # but a proposed line may still exist
                                line_breaks += 1
                                if line_breaks > allowed_breaks: # keep track of hypothetical lines
                                    log(f'   But does not continue, this breaks the line')
                                    line_broken = True
                                else:
                                    log(f'  Line does not continues on chord: {self.chords[next_row].name}... but it might, with: {this_note}')
                                    proposed_line.append((next_row, next_loc, this_note, False))
                                    next_row = next_row + 1
                                    next_loc = (next_loc + dir) % 12

                        idx = start_row+1
                        suf = parsing.num_suffixes[idx]
                        if (len(line) >= min_length) and (len(line) <= max_length):
                            line_coords = [(r,c) for r,c,n in line]
                            line_notes = NoteList([n for r,c,n in line])

                            if disp:
                                print(f'Found a {dir_name} chromatic line (size {len(line)}) starting on {idx}{suf} chord ({self.chords[idx-1].chord_name}) : {line_notes}')
                            lines[(start_row, start_loc, dir)] = line
                        if (len(proposed_line) >= min_length) and (len(proposed_line) <= max_length):
                            if (start_row-1, start_loc - dir, dir) not in proposed_lines:
                                proposed_line_coords = [(r,c) for r,c,n,b in proposed_line]
                                proposed_line_notes = NoteList([n for r,c,n,b in proposed_line])
                                if (start_row, start_loc, dir) in lines: # if this proposed line shares a start with a real line
                                    associated_true_line = lines[(start_row, start_loc, dir)]
                                    if len(proposed_line) - len(associated_true_line) >= (1+allowed_breaks): # only for non-trivial extensions
                                        extension_notes = proposed_line_notes[len(associated_true_line):]
                                        if disp:
                                            print(f'  Which could be extended as: {extension_notes}')
                                else:
                                    if disp:
                                        print(f'Found a POTENTIAL {dir_name} chromatic line (size {len(proposed_line)}) starting on {idx}{suf} chord ({self.chords[idx-1].chord_name}) : {proposed_line_notes}')
                                    proposed_lines[(start_row, start_loc, dir)] = proposed_line
                    else:
                        log(f'Existing line already begins at {(start_row-1, start_loc)}, in dir: {dir}')

        if not disp:
            if allowed_breaks == 0:
                return lines # true lines only
            else:
                if _return_table:
                    return lines, proposed_lines, voice_table
                else:
                    return lines, proposed_lines
        else:
            # output a nice table
            self.disp_voice_table(voice_table, lines)



    def disp_voice_table(self, voice_table, lines=None, proposed_lines=None):
        # first, replace 1s and 0s in voice table with prettier characters:
        for r in range(voice_table.num_rows):
            for c in range(voice_table.num_cols):
                cur_val = voice_table[(r,c)]
                rep_val = '+' if cur_val == 1 else ' ' # '·'
                voice_table[(r,c)] = rep_val

        # display lines as voice table, by changing voice table values
        # to directional slashes:
        if lines is not None:
            for line_key, line_contents in lines.items():
                start_row, start_loc, dir = line_key
                if dir == -1:
                    dir_char = '╱' # descending
                else:
                    dir_char = '╲' # ascending (note: not a backslash, different unicode char)
                # cur_row = start_row
                # cur_col = start_loc
                for row, col, note in line_contents:
                    voice_table[(row, col)] = dir_char
                    # voice_table[(cur_row, cur_col)] = dir_char
                    # cur_col = (cur_col + dir) % 12
                    # cur_row += 1
        if proposed_lines is not None:
            for line_key, line_contents in proposed_lines.items():
                start_row, start_col, dir = line_key
                # start_chord = self.chords[start_row]
                # dir_name = 'falling' if dir == -1 else 'rising'
                # line_coords = [(r,c) for r,c,n,b in line_contents]
                # line_notes = NoteList([n for r,c,n,b in line_contents])
                if dir == -1:
                    dir_char = '/' # descending
                    prop_char = '╳'
                else:
                    dir_char = '\\' # ascending
                    prop_char = '╳'
                for row, col, note, present in line_contents:
                    if present:
                        voice_table[(row, col)] = dir_char
                    else:
                        voice_table[(row, col)] = prop_char

        # prettify voice table for output:
        from src.display import DataFrame
        chromatic_notes = notes.chromatic_sharp_notes if self.key.prefer_sharps else notes.chromatic_flat_notes
        disp_df = DataFrame(['Chord', '', ''] + [f'{n.chroma:<2}' for n in chromatic_notes])
        for r in range(voice_table.num_rows):
            # margin = [self.chords[r].chord_name, self.chords[r].mod_numeral, ' | ']
            margin = [voice_table.row_labels[r], self.chords[r].mod_numeral, ' | ']
            # pretty_row = ['+' if cell==1 else ' ' for cell in voice_table.rows[r]]
            df_row = margin + voice_table.rows[r]
            disp_df.append(df_row)
        disp_df.show()

    def suggest_chromatic_lines(self, allowed_breaks=1,
                                # line parameters:
                                min_length=4,
                                # chord parameters:
                                diatonic=True, min_likelihood=0.35, min_consonance=0.3):

        lines, proposed_lines, voice_table = self.find_chromatic_lines(allowed_breaks=allowed_breaks, min_length=3, _return_table=True, disp=False)
        finalised_proposed_lines = {}
        chromatic_notes = notes.chromatic_sharp_notes if self.key.prefer_sharps else notes.chromatic_flat_notes
        for line_start, line_contents in proposed_lines.items():
            if len(line_contents) >= min_length:
                start_row, start_col, dir = line_start
                start_chord = self.chords[start_row]
                dir_name = 'falling' if dir == -1 else 'rising'
                line_coords = [(r,c) for r,c,n,b in line_contents]
                line_notes = NoteList([n for r,c,n,b in line_contents])
                which_present = [b for r,c,n,b in line_contents]
                # figure out the note and chord that needs to be added:
                if allowed_breaks == 1:
                    absent_idx = [i for i,b in enumerate(which_present) if b is False][0]
                    absent_coord = line_coords[absent_idx]
                    absent_row, absent_col = absent_coord
                    absent_note = chromatic_notes[absent_col]
                    chord_to_modify = self.chords[absent_row]
                    new_chord = chord_to_modify + absent_note

                    # little string parsing details:
                    modified_chord_num = str(absent_row+1) + parsing.num_suffixes[absent_row+1]
                    start_chord_num = str(start_row+1) + parsing.num_suffixes[start_row+1]
                    a_an = 'an' if absent_note.chroma[0] in 'AEF' else 'a' # english grammar rules
                    if new_chord.likelihood >= min_likelihood and new_chord.consonance >= min_consonance:
                        if (new_chord in self.key) or (not diatonic): # keep diatonic unless asked not to
                            print(f'Try changing {modified_chord_num} chord ({Chord._marker}{chord_to_modify.chord_name}) by adding {a_an} {absent_note} to make it: {Chord._marker}{new_chord.chord_name}')
                            print(f'    which would add a {dir_name} chromatic line (of size {len(line_contents)}) starting on {start_chord_num} chord ({Chord._marker}{start_chord.chord_name})')
                            print(f'        that goes: {line_notes}')
                            finalised_proposed_lines[line_start] = line_contents
                            voice_table.row_labels[absent_row] = f'{chord_to_modify.chord_name} ({new_chord.chord_name})'
                        else:
                            print(f'{Chord._marker}{new_chord} would work to replace {modified_chord_num} chord {Chord._marker}{chord_to_modify}, but is not diatonic to key')
                    else:
                        log(f'Chord change to {new_chord} discarded as it is too obscure: likelihood {new_chord.likelihood}, consonance {new_chord.consonance}')
                else:
                    raise Exception('suggest_chromatic_lines not yet implemented for allowed_breaks > 1')
        self.disp_voice_table(voice_table, lines, finalised_proposed_lines)

    def transpose_for_guitar(self, return_all=False):
        """tries to transpose this ChordProgression into a form where its chords
            are easily playable on guitar in open form
            (depending on the 'easy' chords defined in guitar.standard_open_chords).
        if return_all, returns a list of all matches.
            otherwise, return the first match (or None)"""
        from src import guitar
        easy_chords = guitar.standard_open_chords
        playable_progressions = []
        for i in range(1,12):
            transp_prog = self + i
            is_easy = True
            for chord in transp_prog.chords:
                if (chord not in easy_chords) and (len(chord) > 2): # dyad chords are always easy
                    is_easy = False
                    break
            if is_easy:
                if not return_all:
                    # just return the first match found:
                    return transp_prog
                playable_progressions.append(transp_prog)
        if return_all:
            print(f'{len(playable_progressions)} possible guitar transpositions for chords: {self.chords}')
            return playable_progressions
        else:
            print(f'No guitar transposition found for chords: {self.chords}')
            return None

    def find_key(self, chords=None,
                #candidate_scales = scales.natural_scales + scales.extended_scales,
                candidate_scales = scales.major_scales + scales.minor_scales,
                contract_extended_scales = True,
                pad_with_tonic=False, verbose=False):
        """wraps around matching_keys but additionally uses cadence information to distinguish between competing candidates"""

        prev_verbosity = log.verbose
        # log.verbose=verbose
        if chords is None:
            chords = self.chords

        log(f'Searching for keys of {chords} with default parameters')
        matches = matching_keys(chords=chords, min_likelihood=0.7, min_recall=0.95, candidate_scales=candidate_scales,
                                max_results=12, display=False)
        if verbose:
            # display the table
            matching_keys(chords=chords, min_likelihood=0.7, min_recall=0.95, candidate_scales=candidate_scales,
                          max_results=12, display=True)

        if len(matches) == 0:
            # if no matches at all first, open up the min recall property:
            log(f'No key found matching notes using default parameters, widening search')
            matches = matching_keys(chords=chords, max_likelihood=0.6, min_likelihood=0.5, min_recall=0.8, candidate_scales=candidate_scales,
                                    max_results=12, display=False)
            if verbose:
                # display the table again:
                matching_keys(chords=chords, max_likelihood=0.6, min_likelihood=0.5, min_recall=0.8, candidate_scales=candidate_scales,
                              max_results=12, display=True)
            if len(matches) == 0:
                raise Exception(f'No key matches at all found for chords: {self} \n(this should never happen!)')
        # try ideal matches (with perfect recall) first:
        log(f'Matches: {[k.name for k in matches]}')

        ideal_matches = [(k,scores) for k,scores in matches.items() if scores['recall'] == 1.0]
        log(f'{len(matches)} possible key matches found')

        match_tuples = [(k, scores) for k,scores in matches.items()]

        # if len(ideal_matches) == 0:
        #     # no good matches, so open up to all matches that share the max recall:
        #     # max_rec = max([scores['recall'] for k,scores in matches.items()])
        #     # max_rec_matches = [(k,scores) for k,scores in matches.items() if scores['recall'] == max_rec]
        #     match_tuples = max_rec_matches
        #     log('No ideal matches with perfect recall')
        #     # log(f'So opened up to all {len(match_tuples)} matches tied for the highest recall')
        #     log(f'So opened up to all matches above recall threshold')
        # else:
        #     log(f'Found {len(ideal_matches)} candidate/s with perfect recall')
        #     # at least one ideal match, so we'll focus on those
        #     match_tuples = ideal_matches

        if len(match_tuples) == 1:
            log(f'Only one candidate for key: {match_tuples}')
            # only one good match, so use it
            key = match_tuples[0][0]
            print(f'Found key: {key}')

        elif len(match_tuples) >= 2:
            # # multiple good matches, see if one has better precision than the other
            # max_prec = max([scores['precision'] for k,scores in match_tuples])

            # precise_matches = [(k,scores) for k,scores in match_tuples if scores['precision'] == max_prec]
            log(f'Multiple candidates for key: {[m[0].name for m in match_tuples]}')
            log(f' So testing them for cadence-based grammaticity')
            # if len(precise_matches) == 1:
            #     # one of the perfect-recall matches is better than all the others, so use it (probably?)
            #     key = precise_matches[0][0]
            #     print(f'Found key: {key}')

            # else:

            candidate_keys = [k for k, scores in match_tuples]

            log(f'Testing {len(candidate_keys)} candidate keys for grammaticity of this progression in those keys')
            candidate_progressions = [Progression(chords.as_numerals_in(k), scale=k.scale).in_key(k) for k in candidate_keys]
            log(f'Candidate keys: {", ".join([str(p.key) for p in candidate_progressions])}')
            # get a dict of key: cadence_score pairs for key candidates
            key_cadence_scores = most_grammatical_progression(candidate_progressions, add_resolution=pad_with_tonic, return_scores=True, verbose=verbose)
            # augment match tuples with cadence scores:
            new_scores = {}
            for key, score in match_tuples:
                new_score = {k:v for k,v in score.items()}
                new_score['cadence'] = key_cadence_scores[key]
                joint_cadence_recall = (new_score['cadence'] + new_score['recall']**2 + new_score['precision']/2) / 2.5
                new_score['joint_cadence_recall'] = round(joint_cadence_recall, 3)
                new_scores[key] = new_score

            re_ranked_keys = sorted(candidate_keys, key=lambda k: (-new_scores[k]['joint_cadence_recall'],
                                                               -new_scores[k]['cadence'],
                                                               -new_scores[k]['recall'],
                                                               -k.likelihood,
                                                               -new_scores[k]['precision'],
                                                               -k.consonance))

            # grammatical_progressions = most_grammatical_progression(candidate_progressions, add_resolution=pad_with_tonic, verbose=log.verbose)
            # grammatical_keys = [p.key for p in grammatical_progressions]

            ranked_keys, ranked_scores = re_ranked_keys, [new_scores[k] for k in re_ranked_keys]
            key = ranked_keys[0]

            if verbose:
                from src.display import DataFrame
                df = DataFrame(['Key', 'C-R score', 'Cad.',
                                'Rec.', 'Prec.',
                                'Likl.', 'Cons.'])
                for k,s in zip(ranked_keys, ranked_scores):
                    df.append([str(k), s['joint_cadence_recall'], s['cadence'],
                              round(s['recall'],2), round(s['precision'],2),
                              round(k.likelihood,2), round(k.consonance, 3)])
                df.show()

            # short_chord_names = ' - '.join([ch.name for ch in chords])
            print(f'Determining key for ChordProgression: {chords}')
            print(f'    Best guess: {key}')

            if key.is_extended() and (contract_extended_scales):
                print(f'     (contracted to {key.contraction})')
                key = key.contraction

        log.verbose = prev_verbosity

        assert isinstance(key, Key)
        return key

        # return lines
    # def __repr__(self):
    #     return str(self)



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
            # cast ScaleDegrees to ints:
            start, end = int(start), int(end)
            self.fractional = False
        else:
            # movement involving one or more fractional degrees
            # which might get strange?
            log(f'Parsed a fractional degree movement from {start} to {end}')
            # cast the non-float ones to int anyway, because you can't add ScaleDegrees
            start = int(start) if not isinstance(start, float) else start
            end = int(end) if not isinstance(end, float) else end
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

        # the 'size' of the movement: 2 to 1 has less magnitude than 5 to 1, but the same as 7 to 1
        self.magnitude = min([self.up, self.down])
        # signed/directional shortest distance up or down:
        self.distance = self.up if self.up == self.magnitude else -self.down


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

    _movement_marker = settings.MARKERS['right']
    _up_arrow = settings.MARKERS['up']
    _down_arrow = settings.MARKERS['down']


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

        self.authentic_cadence = (self.start == 5 and self.end == 1)
        self.leading_tone_cadence = (self.start == 7 and self.end == 1)
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
        elif self.leading_tone_cadence:
            return 'leading tone cadence'
        else:
            return False

    @property
    def cadence_score(self):
        # extremely fuzzy score used for checking the grammaticity of progressions
        if self.authentic_cadence:
            return 1
        elif self.leading_tone_cadence:
            return 0.6
        elif self.authentic_half_cadence:
            return 0.2
        elif self.plagal_cadence:
            return 0.7
        elif self.plagal_half_cadence:
            return 0.1
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


class ScaleChordMotion:
    """Movement of root and every other chord degree from one to another,
    understood within the context of a scale and the chords built on its degrees"""
    def __init__(self, start_chord, end_chord, scale=None):
        scale_chords = []
        for ch in (start_chord, end_chord):
            if not isinstance(ch, ScaleChord):
                # cast to ScaleChord from roman numeral
                assert isinstance(ch, str), f"Inputs to ScaleChordMotion must be either ScaleChords or strings denoting roman numerals, but got: {ch} ({type(ch)})"
                ch = ScaleChord.from_numeral(ch, scale=scale)
            scale_chords.append(ch)
        ch1, ch2 = scale_chords

        if scale is None:
            # auto-determine scale if not explicitly provided
            if ch1.scale == ch2.scale:
                # use the ScaleChords' scales if they match
                self.scale = ch1.scale
            else:
                # determine it from roots and qualities:
                chord_quality_tuples = [(ch1.scale_degree, ch1.quality), (ch2.scale_degree, ch2.quality)]
                self.scale = infer_scale(chord_quality_tuples)

            # interpret it from given ScaleChords:
            assert isinstance(ch1, ScaleChord)
            assert isinstance(ch2, ScaleChord)
            if ch2.scale != ch1.scale: # force second chord's scale into first one if mismatched
                ch2 = ScaleChord(intervals=ch2.intervals, inversion=ch2.inversion, scale=ch1.scale, degree=ch2.scale_degree)
        else:
            if not isinstance(scale, Scale):
                scale = Scale(scale)
            self.scale = scale

        self.start_chord, self.end_chord = ch1, ch2

        self.start_chord_relative_intervals = (self.start_chord.intervals + self.start_chord.root_interval_from_tonic).flatten()
        self.end_chord_relative_intervals = (self.end_chord.intervals + self.end_chord.root_interval_from_tonic).flatten()

        self.degree_distance_values, self.interval_distance_values = self.build_tables()

        import pandas as pd
        self.degree_distances = pd.DataFrame(self.degree_distance_values,
                                      columns=[f'{iv.short_name}' for iv in self.end_chord_relative_intervals],
                                      index=[f'{iv.short_name:<2}  ' for iv in self.start_chord_relative_intervals])
        self.interval_distances = pd.DataFrame(self.interval_distance_values,
                                        columns=[f'{iv.short_name}' for iv in self.end_chord_relative_intervals],
                                        index=[f'{iv.short_name:<2}  ' for iv in self.start_chord_relative_intervals])



    def build_tables(self):
        import numpy as np
        degree_distance_matrix = np.zeros((len(self.start_chord), len(self.end_chord)), dtype=float)
        interval_distance_matrix = np.zeros((len(self.start_chord), len(self.end_chord)), dtype=int)
        rt1 = self.start_chord.root_interval_from_tonic
        rt2 = self.end_chord.root_interval_from_tonic

        for r, iv1 in enumerate(self.start_chord_relative_intervals):
            for c, iv2 in enumerate(self.end_chord_relative_intervals):
                deg1 = self.scale._get_arbitrary_interval_degree(iv1) # note_degrees[n1] if n1 in self.key.note_degrees else key.fractional_note_degrees[n1]
                deg2 = self.scale._get_arbitrary_interval_degree(iv2) # note_degrees[n2] if n2 in self.key.note_degrees else key.fractional_note_degrees[n2]
                motion = DegreeMotion(deg1, deg2, scale=self.scale)
                degree_distance_matrix[r,c] = round(motion.distance,1)

                iv_distance = (iv2 - iv1).signed_class # i.e. the interval or its inversion, whichever is narrower
                interval_distance_matrix[r,c] = iv_distance.value
        return degree_distance_matrix, interval_distance_matrix




    @property
    def tension(self):
        """how much tension between the two chords, measured by the number of
        1s and 2s in their distances"""
        tension_score = len(self.end_chord) # normalising factor; so that tonic chord itself has 0 tension
        num_rows, num_cols = len(self.start_chord), len(self.end_chord)
        distances = self.interval_df
        for r in range(num_rows):
            row = distances.iloc[r]
            abs_semitones = [abs(v) for v in row]
            min_abs = min(abs_semitones)
            num_0s = len([v for v in abs_semitones if v==0])
            num_1s = len([v for v in abs_semitones if v==1])
            num_2s = len([v for v in abs_semitones if v==2])
            tension_score += num_1s
            tension_score += (num_2s /2)
            tension_score -= num_0s # every 0 _decreases_ tension
        return tension_score

    def play(self, key='C', *args, **kwargs):
        ch1, ch2 = self.start_chord.in_key(key), self.end_chord.in_key(key)
        ChordList([ch1, ch2]).play(*args, **kwargs)


    def __repr__(self):
        lines = [f'{self.start_chord.compact_name}{self._arrow}{self.end_chord.compact_name} (in {self.scale.name})',
                '\nDegree distance:',
                str(self.degree_distances),
                '\nInterval distance:',
                str(self.interval_distances)]
        return '\n'.join(lines)
        # return f'{self.start_chord.compact_name}{self._arrow}{self.end_chord.compact_name} (in {self.scale.name})\nDegree distance:\n{self.degree_distances}\nInterval distance:\n{self.interval_distances}'

    _arrow = settings.MARKERS['right']

class KeyChordMotion(ScaleChordMotion):
    def __init__(self, start_chord, end_chord, key=None):
        ch1, ch2 = start_chord, end_chord
        if key is None:
            # requires KeyChords as input
            assert isinstance(ch1, KeyChord) and isinstance(ch2, KeyChord), "KeyChordMotion must either be supplied KeyChords as input, or Chords plus a 'key' arg"
            assert ch1.key == ch2.key, "Keys of start and end KeyChords must be the same to initialise a KeyChordMotion"
            key = ch1.key
        else:
            if not isinstance(key, Key):
                key = Key(key)
            valid_chords = []
            for ch in [ch1, ch2]:
                if not isinstance(ch, KeyChord):
                    if isinstance(ch, str):
                        # assume roman numeral
                        deg, (modifiers, inversion) = parse_roman_numeral(ch, return_params=True)
                        root = key._get_arbitrary_degree_note(deg)
                        ch = KeyChord(modifiers=modifiers, inversion=inversion, root=root, key=key, degree=deg)
                    elif isinstance(ch, ScaleChord):
                        ch = ch.in_key(key)
                    elif type(ch) is Chord:
                        deg = key._get_arbitrary_note_degree(ch.root)
                        ch = ch.in_key(key=key, degree=deg)
                valid_chords.append(ch)
        # now both are KeyChords in the correct key:
        self.key = key
        ch1, ch2 = valid_chords
        assert isinstance(ch1, KeyChord) and isinstance(ch2, KeyChord)
        assert ch1.key == ch2.key == key
        self.start_chord, self.end_chord = ch1, ch2
        self.scale = self.key.scale

        self.start_chord_relative_intervals = (self.start_chord.intervals + self.start_chord.root_interval_from_tonic).flatten()
        self.end_chord_relative_intervals = (self.end_chord.intervals + self.end_chord.root_interval_from_tonic).flatten()

        self.degree_distance_values, self.interval_distance_values = self.build_tables()

        import pandas as pd
        self.degree_distances = pd.DataFrame(self.degree_distance_values,
                                      columns=[f'{nt.chroma}' for nt in self.end_chord.notes],
                                      index=[f'{nt.chroma:<2}  ' for nt in self.start_chord.notes])
        self.interval_distances = pd.DataFrame(self.interval_distance_values,
                                        columns=[f'{nt.chroma}' for nt in self.end_chord.notes],
                                        index=[f'{nt.chroma:<2}  ' for nt in self.start_chord.notes])


    def __repr__(self):
        lines = [f'{self.start_chord.compact_name}{self._arrow}{self.end_chord.compact_name} (in {self.key.name})',
                '\nDegree distance:',
                str(self.degree_distances),
                '\nInterval distance:',
                str(self.interval_distances)]
        return '\n'.join(lines)


    # def _build_tables(self):
    #     # experimental, WIP
    #
    #     ### TBI: adjust degree_df to work for scales/intervals instead of keys/notes
    #     import numpy as np
    #     degree_distance_matrix = np.zeros((len(self.start_chord), len(self.end_chord)), dtype=float)
    #     interval_distance_matrix = np.zeros((len(self.start_chord), len(self.end_chord)), dtype=int)
    #     for r, n1 in enumerate(self.start_chord.notes):
    #         for c, n2 in enumerate(self.end_chord.notes):
    #             deg1 = self.key._get_arbitrary_note_degree(n1) # note_degrees[n1] if n1 in self.key.note_degrees else key.fractional_note_degrees[n1]
    #             deg2 = self.key._get_arbitrary_note_degree(n2) # note_degrees[n2] if n2 in self.key.note_degrees else key.fractional_note_degrees[n2]
    #             motion = DegreeMotion(deg1, deg2, scale=self.key.scale)
    #             degree_distance_matrix[r,c] = round(motion.distance,1)
    #
    #             iv_distance = (n2 - n1).signed_class # i.e. the interval or its inversion, whichever is narrower
    #             interval_distance_matrix[r,c] = iv_distance.value
    #
    #     import pandas as pd
    #     self.degree_df = pd.DataFrame(degree_distance_matrix,
    #                                   columns=[f'{n.chroma}' for n in self.end_chord.notes],
    #                                   index=[f'{n.chroma:<2}  ' for n in self.start_chord.notes])
    #     self.interval_df = pd.DataFrame(interval_distance_matrix,
    #                                     columns=[f'{n.chroma}' for n in self.end_chord.notes],
    #                                     index=[f'{n.chroma:<2}  ' for n in self.start_chord.notes])
    #

# generic constructor method for motion either between ScaleChords or KeyChords:
def chord_motion(start_chord, end_chord, scale=None):
    if type(start_chord) in (AbstractChord, ScaleChord) and (type(end_chord) == type(start_chord)):
        # this will be a ScaleChordMotion
        return ScaleChordMotion(start_chord, end_chord, scale=scale)
    elif type(start_chord) in (Chord, KeyChord) and (type(end_chord) == type(start_chord)):
        return KeyChordMotion(start_chord, end_chord, key=scale)
    else:
        raise TypeError(f'Cannot make a ChordMotion object from incompatible types: {type(start_chord)} and {type(end_chord)}')

def tonic_tension(scale_chord, scale=None):
    """the tonic tension of a ScaleChord is how strongly it wants to resolve back
    the to tonic chord, measured by the number of steps back to a tonic chord within it"""
    if not isinstance(scale_chord, ScaleChord):
        scale_chord = ScaleChord(scale_chord, scale=scale)
    tonic_chord = scale_chord.scale.chord(1)
    motion = ScaleChordMotion(scale_chord, tonic_chord)
    return motion.tension


# TODO: key recognition routine that respects progression logic,
# i.e. looking for cadences or half cadences in the final root movement

def propose_root_motions(start, direction):
    """Given a root degree 'from', and a direction which should be one of 'D' (dominant)
    or 'SD' (subdominant), propose RootMotion continuations in that direction"""
    ... # TBI


common_progression_strs_by_name = {} # to avoid unassigned variable errors in upcoming Progression init

common_progressions = {Progression(numerals):name for numerals, name in common_progression_defines.items()}

# get the reverse mappings too:
common_progression_strs_by_name = reverse_dict(common_progression_defines)
common_progressions_by_name = reverse_dict(common_progressions)


simple_progressions = {p.simplify(): name for p,name in common_progressions.items()}

# augmented dicts that includes all their rotations as well:
rotated_common_progressions = dict(common_progressions)
rotated_simple_progressions = dict(simple_progressions)


for prog_dict, rot_dict in zip([common_progressions, simple_progressions], [rotated_common_progressions, rotated_simple_progressions]):
    for prog, name in prog_dict.items():
        rotations = {rot: f'{name} ({i+1}{parsing.num_suffixes[i+1]} rotation)' for i,rot in enumerate(prog.rotations)}
        # check if any rotations are already in this dict
        # for prog, name in rotations.items():
        #     if prog in common_rotated_progressions:
        #         print(f'{name} already exists as: {common_progressions[prog]} ({prog})')
        rot_dict.update(rotations)

# rotated_simple_progressions = {p.simplify(): name for p,name in rotated_common_progressions.items()}

# import named progressions as strings of roman numerals:
#from .config.def_progressions import common_progressions as common_progression_defines
## and cast them to Progression objects:
#common_progressions = {Progression(chords):name for chords, name in common_progression_defines.items()}


# guitar-playable variants of the common progressions:
def guitar_progressions():
    for prog, name in common_progressions.items():
        cprogs = prog.transpose_for_guitar(return_all=True)
        desc = '\n'
        if len(cprogs) == 0:
            cprogs = prog.simplify().transpose_for_guitar(return_all=True)
            desc += '(simplified)\n'
        cprogs_str = desc + '\n'.join([p.__str__(chords_only=True) for p in cprogs]) + '\n===='
        print(f'{name} - {prog}: {cprogs_str}')
