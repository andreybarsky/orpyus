### this progressions module is incomplete, very WIP at the moment

from .intervals import Interval
from .notes import Note, NoteList, chromatic_notes
from .chords import Chord, AbstractChord, ChordList
from .qualities import Major, Minor, Perfect, Diminished, parse_chord_modifiers, ChordModifier, modifier_aliases, minor_mod, dim_mod
from .scales import infer_chord_scale, infer_scale, parse_roman_numeral, Scale, ScaleChord, NaturalMajor, NaturalMinor
from .keys import Key, KeyChord, matching_keys# , most_likely_key
from .util import reduce_aliases, rotate_list, check_all, reverse_dict, log
from .parsing import roman_numerals, numerals_roman, modifier_marks, auto_split, superscript, fl, sh, nat
from . import parsing, _settings

from collections import Counter

# import numpy as np  # not needed yet

# global defaults:
default_diacs = _settings.DEFAULT_PROGRESSION_DIACRITICS
default_marks = _settings.DEFAULT_PROGRESSION_MARKERS

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

            base_degree_chord_params = [parse_roman_numeral(n, return_params=True) for n in numerals] # degree, AbstractChord tuples
            self.root_degrees = [d[0] for d in base_degree_chord_params]
            base_degree_chords = [(deg, AbstractChord.from_cache(modifiers=mods, inversion=inv)) for deg, (mods, inv) in base_degree_chord_params]

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
                    deg, ch = parse_roman_numeral(numerals[i], ignore_alteration=True)
                    base_degree_chords[i] = deg, ch
                    log(f'So quietly replaced with {numerals[i][1:]} (in scale: {self.scale.name}')
                    self.root_degrees = [d[0] for d in base_degree_chords]


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

        elif check_all(numerals, 'isinstance', ScaleChord):
            ### allow init by scalechords alone
            scalechord_scales = [ch.scale for ch in numerals]
            assert check_all(scalechord_scales, 'eq', scalechord_scales[0]), f"Non-matching scale attributes in ScaleChord list given to Progression: {scalechord_scales}"
            self.scale = scalechord_scales[0]
            self.chords = ChordList(numerals)
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
                             'Distance', '', 'Cadence'])
        else:
            df = DataFrame(['Function', '', 'Deg1', '', 'Deg2', '',
                             'Chd1', '', 'Chd2', '',
                             'Distance', '', 'Cadence'])
        # sloppy for now: should be rolled into a dataframe from the Display module
        num1s, num2s, c1s, c2s, mvs, cads = [], [], [], [], [], []
        clean_numerals = self.as_numerals(marks=False, diacritics=False, sep='@').split('@')
        for i in range(len(self)-1):
            f = f'[{self.root_movements[i].function_char}]'
            arrow = self.root_movements[i]._movement_marker
            n1, n2 = clean_numerals[i], clean_numerals[i+1]
            ch1, ch2 = self.chords[i].short_name, self.chords[i+1].short_name,
            dist = str(self.root_movements[i].direction_str)
            cadence = self.root_movements[i].cadence
            cadence = cadence if (cadence != False) else ''
            if roots is None:
                df.append([f, '  ', n1, arrow, n2, '  ',
                            # ch1, arrow, ch2, ' ',
                            dist, '  ', cadence])
            else:
                df.append([f, '  ', n1, arrow, n2, '  ',
                            ch1, arrow, ch2, ' ',
                            dist, '  ', cadence])

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

    def as_numerals(self, sep=' ', modifiers=True, marks=default_marks, diacritics=default_diacs):
        """returns this Progression's representation in roman numeral form
        with respect to its Scale"""

        numerals = [ch.get_numeral(modifiers=modifiers, marks=marks, diacritics=diacritics) for ch in self.chords]

        if sep is not None:
            roman_chords_str = sep.join(numerals)
            return roman_chords_str
        else:
            # just return the raw list, instead of a sep-connected string
            return numerals
    get_numerals = as_numerals # convenience alias
    @property
    def numerals(self):
        return self.as_numerals()

    @property
    def simple_numerals(self):
        """just raw upper/lowercase numerals, no modifiers or diacritics etc."""
        return self.as_numerals(sep=None, marks=False, diacritics=False, modifiers=False)

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
        return self.on_tonic('C').transpose_for_guitar(*args, **kwargs)

    def __getitem__(self, i):
        return self.chords[i]

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

    def slice(self, start, stop):
        """return a new Progression as a sliced subset of this Progression,
        that starts on integer index 'start' and ends just before integer index 'stop'"""
        new_chords = self.chords[start:stop]
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


class ChordProgression(Progression): # , ChordList):
    """ChordList subclass defined additionally over a specific key"""
    def __init__(self, *chords, key=None, search_natural_keys_only=True):
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
                self.key = self.find_key(chords=base_chords, natural_only = search_natural_keys_only)
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
            self.chords = ChordList([KeyChord(factors=ch.factors, inversion=ch.inversion, root=ch.root, key=self.key, degree=d, assigned_name=ch.assigned_name) for ch,d in zip(base_chords, self.root_degrees)])

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
            return self.in_key(new_key)
        elif isinstance(other, str):
            # check if a roman numeral:
            if other.upper() in roman_numerals:
                new_numerals = self.numerals + [other]
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

        else:
            raise TypeError(f'ChordProgression.__add__ not implemented for type: {type(other)}')

    def __sub__(self, other):
        """subtraction with Interval"""
        if isinstance(other, (int, Interval)):
            return self + (-other)
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

    _brackets = _settings.BRACKETS['ChordProgression']

    def long_str(self):
        # numerals = self.as_numerals()
        # chord_names = ' '.join([c.short_name for c in self.chords])
        lb, rb = self._brackets
        return f'{self.chords}  or  {lb}{self.as_numerals()}{rb}  (in {self.key.name})'

    def __str__(self, marks=default_marks, diacritics=default_diacs, chords_only=False, degrees_only=False):
        lb, rb = self._brackets
        numerals = self.as_numerals(marks=marks, diacritics=diacritics, sep='@')
        split_numerals = numerals.split('@')
        chordlist = [ch.name for ch in self.chords]
        num_chords = zip(split_numerals, chordlist)
        if chords_only:
            prog_str = ' '.join([f'{ch}' for num, ch in num_chords])
        elif degrees_only:
            prog_str = ' '.join([f'{num}' for num, ch in num_chords])
        else: # i.e. both chords AND degrees
            prog_str = ' - '.join([f'{ch} ({num})' for num, ch in num_chords])
        # return f'{self.chords}  (in {self.key.name})'
        return f'ChordProgression:  {lb}{prog_str}{rb}  (in {self.key.name})'

    def __repr__(self, marks=default_marks, diacritics=default_diacs):
        """ChordProgression repr comes out as a table
        with chords above and scale degrees below"""
        numerals = self.as_numerals(marks=marks, diacritics=diacritics, sep='@')
        split_numerals = numerals.split('@')
        chord_names = [ch.name for ch in self.chords]
        from src.display import DataFrame
        df = DataFrame(['' for c in range(len(self))])
        df.append(chord_names) # chord row
        df.append(split_numerals) # degrees row
        return df.show(header=False, header_border=False, margin=' - ', fix_widths=True,
                       return_string=True, title=str(self.key), align='centre')

    def chord_motions(self):
        for i in range(1, len(self)):
            ch1, ch2 = self.chords[i-1], self.chords[i]
            motion = ChordMotion(ch1, ch2, key=self.key)
            print(motion.interval_df, '\n')

    def voice_table(self):
        ### experimental: needs a better name (and Progression main class implementation)
        import numpy as np
        import pandas as pd
        arr = np.zeros((len(self.chords), 12), dtype=int)
        for i, ch in enumerate(self.chords):
            note_array = [1  if n in ch.notes else 0 for n in chromatic_notes]
            arr[i] = note_array
        df = pd.DataFrame(arr, index=[ch.name for ch in self.chords], columns=[f'{n.chroma:<2}' for n in chromatic_notes])
        return df

    def find_chromatic_lines(self, min_length=3, max_length=None):
        print(f'Searching for chromatic lines in {self.__str__(chords_only=True)} ....')
        if max_length is None:
            max_length = len(self)+1
        voice_table = self.voice_table()
        lines = {}
        # try starting on each row, provided there's enough space to find a min-length line:

        print('\n', voice_table)
        for start_row in range(len(self)-(min_length-1)):
            # start locs are the places in this row where each note occurs:
            line_start_locs = [i for i,val in enumerate(voice_table.iloc[start_row]) if val]
            left_dir, right_dir = (-1, +1)
            left_name, right_name = 'falling', 'rising'

            for start_loc in line_start_locs: # i.e. columns
                for dir, dir_name in zip([left_dir, right_dir], [left_name, right_name]):
                    # don't search if this would overlap with an existing line in the same direction:
                    if (start_row-1, start_loc - dir, dir) not in lines:
                        line = [chromatic_notes[start_loc]] # list of notes that form this line
                        log(f'Starting a {dir_name} line at: {start_row, start_loc}, on chord: {self.chords[start_row].name} beginning: {line[0]}')
                        line_broken = False
                        next_row = start_row + 1
                        next_loc = (start_loc + dir) % 12 # mod so as to wrap arond from C to B
                        while (not line_broken) and not (next_row >= len(self)):
                            if voice_table.iloc[next_row, next_loc]:
                                # if a note exists on that diagonal:
                                this_note = chromatic_notes[next_loc]
                                log(f'Line continues on chord: {self.chords[next_row].name} with: {this_note}')
                                line.append(this_note)
                                next_row = next_row + 1
                                next_loc = (next_loc + dir) % 12
                            else:
                                line_broken = True

                        if (len(line) >= min_length) and (len(line) <= max_length):
                            line = NoteList(line)
                            idx = start_row+1
                            suf = parsing.num_suffixes[idx]
                            print(f'Found a {dir_name} chromatic line starting on {idx}{suf} chord ({self.chords[idx-1]}): {line}')
                            lines[(start_row, start_loc, dir)] = line
                    else:
                        log(f'Existing line already begins at {(start_row-1, start_loc)}')


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
                if chord not in easy_chords:
                    is_easy = False
                    break
            if is_easy:
                if not return_all:
                    # just return the first match found:
                    return transp_prog
                playable_progressions.append(transp_prog)
        if return_all:
            return playable_progressions
        else:
            return None

    def find_key(self, chords, natural_only=True, verbose=False):
        """wraps around matching_keys but additionally uses cadence information to distinguish between competing candidates"""

        prev_verbosity = log.verbose
        log.verbose=verbose

        if natural_only:
            min_lik = 0.9
            modes = False
        else: # currently not very good (fix cadential detection)
            min_lik = 0.8
            modes = True

        log(f'Searching for keys of {chords} with default parameters')
        matches = matching_keys(chords=chords, min_likelihood=min_lik, min_recall=0.8, modes=modes,
                                chord_factor_weights = {}, key_factor_weights = {}, # kludge for now until we fix these
                                max_results=12, display=False)

        if len(matches) == 0:
            # if no matches at all first, open up the min recall property:
            log(f'No key found matching notes using default parameters, widening search')
            matches = matching_keys(chords=chords, max_likelihood=min_lik-0.01, min_likelihood=0, min_recall=0.8, modes=modes,
                                    max_results=12, display=False)
            if len(matches) == 0:
                raise Exception(f'No key matches at all found for chords: {self} \n(this should never happen!)')
        # try ideal matches (with perfect recall) first:
        log(f'Matches: {matches}')

        ideal_matches = [(k,scores) for k,scores in matches.items() if scores['recall'] == 1.0]
        log(f'{len(matches)} possible key matches found')

        if len(ideal_matches) == 0:
            # no good matches, so open up to all matches that share the max recall:
            max_rec = max([scores['recall'] for k,scores in matches.items()])
            max_rec_matches = [(k,scores) for k,scores in matches.items() if scores['recall'] == max_rec]
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
            max_prec = max([scores['precision'] for k,scores in match_tuples])
            precise_matches = [(k,scores) for k,scores in match_tuples if scores['precision'] == max_prec]
            log(f'Multiple candidates for key: {[m[0].name for m in match_tuples]}')
            log(f' So focusing on the {len(precise_matches)} tied for highest precision')
            if len(precise_matches) == 1:
                # one of the perfect-recall matches is better than all the others, so use it (probably?)
                key = precise_matches[0][0]
                print(f'Found key: {key}')

            else:
                # multiple matches that are equally as good,
                # so look for a cadence-based match around V-I resolutions or something

                candidate_keys = [k for k, scores in precise_matches]

                log(f'Testing {len(candidate_keys)} candidate keys for grammaticity of this progression in those keys')
                candidate_progressions = [Progression(chords.as_numerals_in(k), scale=k.scale).in_key(k) for k in candidate_keys]
                log(f'Candidate keys: {", ".join([str(p.key) for p in candidate_progressions])}')
                grammatical_progressions = most_grammatical_progression(candidate_progressions, verbose=log.verbose)
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
                        key = likely_keys[0]
                        log(f'One key is more likely than the others: {key}')
                    else:
                        # nothing else left, just tie-break by key consonance
                        keys_by_consonance = sorted(likely_keys, key=lambda x: x.consonance, reverse=True)
                        log(f'Found multiple equally likely keys: {[str(k) for k in keys_by_consonance]}')
                        log(f'So doing a final tie-break by consonance')
                        key = keys_by_consonance[0]

                print(f'Found key: {key}')

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

        self.start_chord, self.end_chord = ch1, ch2

        self._build_tables()

    def __repr__(self):
        return f'{self.start_chord.compact_name}{self._arrow}{self.end_chord.compact_name}\nDegree distance:\n{self.degree_df}\nInterval distance:\n{self.interval_df}'



    _arrow = _settings.MARKERS['right']

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

        self._build_tables()
        # print(f'Degree distance:\n{self.degree_df}')
        # print(f'Degree distance:\n{self.interval_df}')


    def _build_tables(self):
        # experimental, WIP

        ### TBI: adjust degree_df to work for scales/intervals instead of keys/notes
        import numpy as np
        degree_distance_matrix = np.zeros((len(self.start_chord), len(self.end_chord)), dtype=float)
        interval_distance_matrix = np.zeros((len(self.start_chord), len(self.end_chord)), dtype=int)
        for r, n1 in enumerate(self.start_chord.notes):
            for c, n2 in enumerate(self.end_chord.notes):
                deg1 = self.key._get_arbitrary_note_degree(n1) # note_degrees[n1] if n1 in self.key.note_degrees else key.fractional_note_degrees[n1]
                deg2 = self.key._get_arbitrary_note_degree(n2) # note_degrees[n2] if n2 in self.key.note_degrees else key.fractional_note_degrees[n2]
                motion = DegreeMotion(deg1, deg2, scale=self.key.scale)
                degree_distance_matrix[r,c] = round(motion.distance,1)

                iv_distance = (n2 - n1).signed_class # i.e. the interval or its inversion, whichever is narrower
                interval_distance_matrix[r,c] = iv_distance.value

        import pandas as pd
        self.degree_df = pd.DataFrame(degree_distance_matrix,
                                      columns=[f'{n.chroma}' for n in self.end_chord.notes],
                                      index=[f'{n.chroma:<2}  ' for n in self.start_chord.notes])
        self.interval_df = pd.DataFrame(interval_distance_matrix,
                                        columns=[f'{n.chroma}' for n in self.end_chord.notes],
                                        index=[f'{n.chroma:<2}  ' for n in self.start_chord.notes])


# generic constructor method for motion either between ScaleChords or KeyChords:
def chord_motion(start_chord, end_chord, scale=None):
    if type(start_chord) in (AbstractChord, ScaleChord) and (type(end_chord) == type(start_chord)):
        # this will be a ScaleChordMotion
        return ScaleChordMotion(start_chord, end_chord, scale=scale)
    elif type(start_chord) in (Chord, KeyChord) and (type(end_chord) == type(start_chord)):
        return KeyChordMotion(start_chord, end_chord, key=scale)
    else:
        raise TypeError(f'Cannot make a ChordMotion object from incompatible types: {type(start_chord)} and {type(end_chord)}')




# TODO: key recognition routine that respects progression logic,
# i.e. looking for cadences or half cadences in the final root movement

def propose_root_motions(start, direction):
    """Given a root degree 'from', and a direction which should be one of 'D' (dominant)
    or 'SD' (subdominant), propose RootMotion continuations in that direction"""
    ... # TBI



common_progressions = {
    Progression('I IV V'  ) : '145',
    Progression('ii V I'  ) : '251',
    Progression('ii V i'  ) : 'minor 251',
    Progression('V IV I'  ) : '541',
    Progression('I vi V'  ) : '165',
    Progression('I V IV V') : '1545',

    Progression('I IV  ii V ') : '1425',
    Progression('I III IV iv') : '134m4',
    Progression('I ii iii IV V') : '12345',

    Progression('I  V    vi   IV' ) : 'axis',
    Progression('I  V   ♭VII  IV' ) : 'axis (variant)',
    Progression('vi IV   I    V'  ) : 'axis minor', # rotation of axis progression
    Progression('I  vi   IV   V'  ) : '50s', # aka doo-wop
    Progression('I  vi   ii   V  ') : 'blue moon',
    Progression('vi V    IV   III') : 'andalusian',
    Progression('i ♭VII ♭VI   V'  ) : 'andalusian minor',
    Progression('vi IV   V    I'  ) : 'komuro',

    Progression('ii⁷ V⁷  Iᐞ⁷ V⁷') : 'jazz turnaround',
    Progression('Iᐞ⁷ vi⁷ ii⁷ V⁷') : 'rhythm changes',
    Progression('Iᐞ⁷ ii⁷ V⁷ IVᐞ⁷') : '1 to 4',
    Progression('Iᐞ⁷ II⁷ ii⁷ V⁷ Iᐞ⁷') : 'a-train',
    Progression('I⁷  IV⁷ ii⁷ V⁷') : 'montgomery-ward bridge',
    Progression('v⁷ I⁷ IV IV vi⁷ II⁷ ii⁷ V⁷'): 'full montgomery-ward bridge',

    Progression('I⁷ IV⁷ I⁷  V⁷    ') : 'blues',
    Progression('I⁷ IV⁷ I⁷  V⁷ IV⁷') : 'shuffle blues',
    Progression('i⁷ iv⁷ i⁷ ♭VI⁷ V⁷') : 'minor blues',
    Progression('III⁷ VI⁷ II⁷ V⁷ I') : 'ragtime',

    Progression('I ♭VII IV I' ) : 'mixolydian vamp',
    Progression('vi ii  V I'  ) : 'circle',
    Progression('VI ii° V i'  ) : 'circle minor',
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

common_progressions_by_name = reverse_dict(common_progressions)

# just some songs I'm practicing:
house_of_the_rising_sun = ChordProgression('Am C D F Am E Am E', key='Am') # animals
cant_find_my_way_home = ChordProgression('G, D/F#, Dm/F, A, C, D, A', key='A') # clapton
hollow = ChordProgression('A6 - Cmaj7#11 - Emadd9', key='Em') # yosh
would_you_go_with_me = ChordProgression('E C#m B E B A', key='E') # josh turner
your_man = ChordProgression('C G D G', key='G') - 1 # josh turner again

# guitar-playable variants of the common progressions:
def guitar_progressions():
    for prog, name in common_progressions.items():
        cprogs = prog.transpose_for_guitar(return_all=True)
        desc = '\n'
        if len(cprogs) == 0:
            cprogs = prog.simplify().transpose_for_guitar(return_all=True)
            desc += '(simplified)\n'
        cprogs_str = desc + '\n'.join([str(p) for p in cprogs]) + '\n===='
        print(f'{name}: {cprogs_str}')
