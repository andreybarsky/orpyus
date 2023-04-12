# new chord class with explicit factor recognition and compositional name generation/recognition

import notes
from notes import Note, NoteList
from intervals import Interval, IntervalList
from util import log, test, precision_recall, rotate_list, check_all, auto_split, reverse_dict, unpack_and_reverse_dict
import parsing
import qualities
from qualities import Quality, ChordQualifier, parse_chord_qualifiers

from collections import defaultdict

import pdb

# relative minors/majors of all chromatic notes:
relative_minors = {c.name : (c - 3).name for c in notes.chromatic_scale}
relative_minors.update({c.sharp_name: (c-3).sharp_name for c in notes.chromatic_scale})
relative_minors.update({c.flat_name: (c-3).flat_name for c in notes.chromatic_scale})

relative_majors = {value:key for key,value in relative_minors.items()}

# some chord/key tonics correspond to a preference for sharps or flats:
sharp_tonic_names = ['G', 'D', 'A', 'E', 'B']
flat_tonic_names = ['F', 'Bb', 'Eb', 'Ab', 'Db']
neutral_tonic_names = ['C', 'Gb'] # no sharp/flat preference, fall back on default

sharp_major_tonics = [Note(t) for t in sharp_tonic_names]
flat_major_tonics = [Note(t) for t in flat_tonic_names]
neutral_major_tonics = [Note(t) for t in neutral_tonic_names]

sharp_minor_tonics = [Note(relative_minors[t]) for t in sharp_tonic_names]
flat_minor_tonics = [Note(relative_minors[t]) for t in flat_tonic_names]
neutral_minor_tonics = [Note(relative_minors[t]) for t in neutral_tonic_names]


class ChordFactors(dict):
    """a class representing the factors of an AbstractChord, as a dict which has:
        keys: chord degrees (1 representing the root, 5 representing the fifth, etc.)
        values: semitone offsets from default degree intervals.
            e.g. the fifth degree is 7 semitones by default, so {5: -1} implies
            a fifth that is diminished (-1 from perfect), i.e. 6 semitones from root.
        qualifiers: a list of Qualifier objects that have been applied to this object.
            note these are not qualifiers that *should* be applied, but a history for this object.
            applying qualifiers must be done using the __add__ method, or the qualifier's .apply method"""

    def __init__(self, arg=None, qualifiers=None):
        """accepts any arg that would initialise a dict,
          and also allows a string of degree alterations (e.g. "1-♭3-♭♭5")
          or a list of such alterations (e.g. ["1", "♭3", "♭♭5"])
        also treats init by None (i.e. no args) as a major triad by default."""

        # accept re-casting by dict comp:
        if isinstance(arg, ChordFactors):
            arg = {k:v for k,v in arg.items()}

        ### allow initialisation by string or list of chord degrees:
        if isinstance(arg, str):
            ### parse string into list of accidentals by auto splitting non-accidentals
            arg = auto_split(arg, allow='#♯𝄪b♭𝄫')

        if isinstance(arg, list) and type(arg[0]) != tuple:
            # parse a list of non-tuples (i.e. invalid list for dict input) as list of chord degrees
            dict_arg = {}
            for item in arg:
                assert isinstance(item, str)
                # this is an
                qual_dict = parsing.parse_alteration(item)
                dict_arg.update(qual_dict)
            arg = dict_arg
            # then continue as normal

        if arg is None:
            # default init with no input args is a major triad:
            arg = {1:0, 3:0, 5:0}

        super().__init__(arg)
        # # sanity check:
        # for k, v in self.items():
        #     assert isinstance(k, int) and (k >= 1)
        #     assert isinstance(v, int) and (-2 <= v <= 2)
        if qualifiers is None:
            self.qualifiers = []
        else:
            self.qualifiers = list(qualifiers)

    @property
    def degrees(self):
        return list(self.keys())

    @property
    def offsets(self):
        return list(self.values())

    @property
    def order(self):
        """the number of notes in the chord that this object represents"""
        return len(self)

    def to_intervals(self, as_dict=False):
        """translates these ChordFactors into an IntervalList
        or, if as_dict, into a factor_intervals dict mapping degrees to intervals"""
        if not as_dict:
            return IntervalList([Interval.from_degree(d, offset=o) for d, o in self.items()]).sorted()
        elif as_dict:
            return {d:Interval.from_degree(d, offset=o) for d, o in self.items()}

    def copy(self):
        return ChordFactors({k:v for k,v in self.items()}, qualifiers=self.qualifiers)

    def __add__(self, other):
        """modifies these factors by the alterations in a ChordQualifier,
        return new factors object"""
        # output_factors = ChordFactors(self, qualifiers=self.qualifiers)

        if isinstance(other, ChordQualifier):
            output_factors = other.apply(self)
            # output_factors.qualifiers.append(other)
        elif isinstance(other, (list, tuple)):
            # apply a list of ChordQualifiers instead:
            output_factors = self.copy()
            for qual in other:
                assert isinstance(qual, ChordQualifier), f"ChordFactor tried to be modified by an item in a list that was not a ChordQualifier but was: {type(qual)}"
                output_factors = qual.apply(output_factors)
                # output_factors.qualifiers.append(qual)
        # ensure that we keep ourselves sorted:
        else:
            raise TypeError(f'Cannot add ChordFactors object to type: {type(other)}')
        sorted_keys = sorted(list(output_factors.keys()))
        # return output_factors
        return ChordFactors({k: output_factors[k] for k in sorted_keys}, qualifiers = output_factors.qualifiers)

    def distance(self, other):
        # distance from other ChordFactors objects, to detect altered chords from their factors
        # as qualifier: what must be done to RIGHT (other) to make it LEFT (self)
        assert isinstance(self, ChordFactors) and isinstance(other, ChordFactors)
        add, modify, remove  = {}, {}, []
        for degree, offset in self.items():
            if degree not in other:
                # other must add this degree at this value
                add[degree] = offset
            elif offset != other[degree]:
                other_offset = other[degree]
                offset_dist = offset - other_offset
                modify[degree] = offset_dist
        for degree in other.keys():
            if degree not in self:
                remove.append(degree)
        dist_qualifier = ChordQualifier(add=add, modify=modify, remove=remove)
        return dist_qualifier

    def __sub__(self, other):
        """the - operator calculates (symmetric) distance between ChordFactors"""
        return self.distance(other)

    def __hash__(self):
        return hash(tuple(self))

    def __str__(self):
        factor_strs = [f'{parsing.offset_accidentals[v][0]}{d}' for d,v in self.items()]
        return f'¦ {", ".join(factor_strs)} ¦'

    def __repr__(self):
        return f'ChordFactors: {str(self)}'

# a chord's factors look like this:
_major_triad = ChordFactors({1:0, 3:0, 5:0})
# meaning: default intervals of 1st, 3rd, and 5th degrees
# this _major_triad object is used for comparisons, but should never be modified

################################################################################

class AbstractChord:
    """a hypothetical chord not built on any specific note but having all the qualifiers that a chord would,
    whose principal members are Intervals. see AbstractChord._parse_input for valid input schemas.
    an AbstractChord is fully identified by its Factors and its Inversion."""
    def __init__(self, name=None, factors=None, intervals=None, inversion=None, inversion_degree=None, qualifiers=None):
        """primary input arg must be one of the following mutually exclusive keywords, in order of resolution:
        1. 'name' arg as string denoting the name of an AbstractChord (like 'mmaj7'),
                which we look up and parse as a list of ChordQualifiers.
                  --this name can also contain an inversion (like 'mmaj7/2'), which
                    we interpret as an 'inversion' arg (and therefore ignore an
                    inversion kwarg if one has been supplied)
        2. (re-casting): 'name' arg of type AbstractChord, or a subclass of AbstractChord, from which
                we read the factors/intervals/inversion directly.
        3. 'factors' arg of type ChordFactors, keying degree to semitone offsets,
                which we accept directly.
        4. 'intervals' arg as list of Intervals, or ints that cast to Intervals, which we
            interpret as distances from the desired chord's root (using Interval.degree
                attribute to build ChordFactors from)

        and special case:
        5. 'qualifiers' arg as string or list of ChordQualifier objects, (or objects that cast
                to ChordQualifiers), which we successively apply to the major triad.
        this can be given as sole init argument, but is also valid to provide in combination
            with any of the other keyword args, in which case we apply the qualifiers
            not to the major triad, but whatever other chord got parsed out by the keyword arg.

        lastly, an optional arg: one of 'inversion' or 'inversion_degree':
            'inversion' as int, denoting that this chord is an "Xth inversion", meaning that
                the bass note is the X+1th note in the chord, with notes ordered ascending.
        or
            'inversion_degree' as int, denoting the degree that the chord's bass note is on.

        note that both are ignored if the 'name' arg contains a slash."""

        self.factors, self.root_intervals, self.inversion = self._parse_input(name, factors, intervals, inversion, inversion_degree, qualifiers)

        # dict mapping chord factors to intervals from tonic:
        self.factor_intervals = {i.extended_degree: i for i in self.root_intervals}

        if self.inversion is not None: # list of self.intervals is with respect to this chord's inversion
            self.intervals = self.root_intervals.invert(self.inversion)
        else:
            self.intervals = self.root_intervals

        # quality of a chord is the quality of its third:
        self.quality = qualities.Perfect if 3 not in self.factors else self.factor_intervals[3].quality

    @staticmethod
    def _parse_input(name, factors, intervals, inversion, inversion_degree, qualifiers, allow_note_name=False):
        """takes valid inputs to AbstractChord and parses them into factors, intervals and inversion.
        (see docstring for AbstractChord.__init__)"""

        if name is None and factors is None and intervals is None:
            # we have been given nothing to init by, so initialise a basic major triad:
            factors = ChordFactors()

        if name is not None:
            assert factors is None and intervals is None
            # check for inversion by slashes: (or sometimes backslashes)
            if '/' in name or '\\' in name:
                assert inversion is None and inversion_degree is None, 'Parsed slash chord as denoting inversion, but received mutually exclusive inversion arg'
                # parse inversion from name
                name = name.replace('\\', '/')
                name, inversion_str = name.split('/')

                if inversion_str.isnumeric():
                    inversion = int(inversion_str)
                else:
                    assert allow_note_name, f'String inversions only allowed for non-AbstractChords'
                    inversion = inversion_str

            # detect major chord:
            if name == '' or name in ((qualities.qualifier_aliases['maj']) + ['maj']):
                factors = ChordFactors() # major triad by default
            else:
                qualifiers_from_name = parse_chord_qualifiers(name)
                factors = ChordFactors() + qualifiers_from_name
        elif factors is not None:
            assert name is None and intervals is None
            # do nothing! factors are already defined, just pass to next block
        elif intervals is not None:
            assert name is None and factors is None
            # sanitise interval list input, expect root to be provided:
            intervals = IntervalList(intervals).pad(left=True, right=False)
            assert len(intervals) == len(set(intervals)), f'Interval list supplied to AbstractChord init contains repeated intervals: {intervals}'

            # build factors by looping through intervals:
            factors = ChordFactors({1:0}) # note: NOT a major triad
            for i in intervals: # parse interval degree and quality
                # catch special case: do not record perfect octaves
                if i.mod != 0:
                    factors[i.extended_degree] = i.offset_from_default

        if qualifiers is not None:
            if factors is None:
                # start qualifying a major triad by default
                factors = ChordFactors()

            if isinstance(qualifiers, str):
                # parse string of qualifiers as an iterable of them
                qualifiers = parse_chord_qualifiers(qualifiers)
            # make sure we're dealing with an iterable of them:
            check_all(qualifiers, 'isinstance', ChordQualifier)
            # apply them to our factors:
            factors = factors + qualifiers

        if intervals is None: # i.e. if we have defined factors from name or factor kwarg
            intervals = []
            for deg, offset in factors.items():
                # note that interval list always includes Unison as root
                intervals.append(Interval.from_degree(deg, offset=offset))
            intervals = IntervalList(intervals)

        if inversion_degree is not None:
            # which Xth inversion is this, from the inversion degree:
            for x, deg in enumerate(sorted(factors.keys())):
                if inversion_degree == deg:
                    inversion = x
                    break

        if inversion is not None:
            if isinstance(inversion, int):
                assert 0 < inversion <= (len(factors)-1), f'{inversion} is an invalid inversion number for chord with {len(factors)} factors'
            elif isinstance(inversion, str):
                if not allow_note_name:
                    raise TypeError(f'inversion arg for AbstractChord must be an int, but got: {type(inversion)}')
                else:
                    if not parsing.is_valid_note_name(inversion):
                        raise ValueError(f'got string argument to inversion, but does not seem to be a valid note name: {inversion}')
            else:
                raise TypeError(f'inversion must be an int or str, but got: {type(inversion)}')

        return factors, intervals.sorted(), inversion

    def __len__(self):
        return len(self.factors)

    @property
    def _inv_string(self):
        """inversion string, used internally by suffix method (and inherited by subclasses)"""
        return f'/{self.inversion}' if (self.inversion is not None) else ''

    @property
    def suffix(self, inversion=True):
        """dynamically determine chord suffix from factors and inversion"""
        inv_string = self._inv_string if inversion else ''
        if self.factors in factors_to_chord_names:
            return factors_to_chord_names[self.factors] + inv_string
        elif self.root_intervals in intervals_to_chord_names:
            print(f' ++ Could not find chord by factors ({self.factors}), but found it by root intervals: {self.root_intervals}')
            return intervals_to_chord_names[self.root_intervals] + inv_string
        elif self.intervals in intervals_to_chord_names:
            print(f' ++++ Could not find chord by factors ({self.factors}), but found it by inverted intervals: {self.intervals}')
            return intervals_to_chord_names[self.intervals] + f' (inverted from {self.root})'
        elif self.factors == _major_triad:
            return ''
        else:
            return f'(?){inv_string}'

    @property
    def name(self):
        return f'{self.suffix} chord'

    def root(self, root_note):
        """constructs a Chord object from this AbstractChord with respect to a desired root"""
        return Chord(root=root_note, factors=self.factors, inversion=self.inversion)

    def __str__(self):
        # note that intervals are presented with respect to inversion
        interval_short_names = [i.short_name for i in self.intervals]
        intervals_str = ', '.join(interval_short_names)
        return f'♫ {self.name}  | {intervals_str} |'

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        """AbstractChords are equal to others on the basis of their factors and inversion"""
        if type(other) == AbstractChord:
            return (self.factors == other.factors) and (self.inversion == other.inversion)
        else:
            raise TypeError(f'AbstractChords can only be compared to other AbstractChords')

################################################################################

class Chord(AbstractChord):
    """a Chord built on a note of the chromatic scale, but in no particular octave,
    whose members are Notes.
    a Chord is fully identified by its Root, its Factors, and its Inversion"""
    def __init__(self, name=None,
                       root=None, factors=None, intervals=None,
                       notes=None,
                       inversion=None, inversion_degree=None, bass=None,
                       qualifiers=None,
                       in_key=None,
                       move_above=True):
        """initialised in the same way as an AbstractChord, with two differences:
        if 'notes' arg is supplied, we try to construct a Chord object from those notes
            and ignore name/root/factors/intervals keywords. (but still allow inversion? and qualifiers)

        elif 'name' arg is supplied, we treat it as in AbstractChord but require it to lead with the name of the chord root.
            i.e. 'Bbmmaj7' is parsed as having root 'Bb', and passes 'mmaj7' to AbstractChord init.

        otherwise, if neither is supplied, we parse keyword args in the same way as AbstractChord,
            with the additional requirement that 'root' keyword arg is also supplied, as a Note
            or object that casts to Note.

        we also accept the optional 'in_key' argument, instead of AbstractChord's 'in_scale',
        which specifies that this Chord is to be regarded as in a specific Key,
        affecting its sharp preference and arithmetic behaviours."""

        if notes is not None: # initialise from ascending note list by casting notes as intervals from root
            # ignore intervals/factors/root inputs
            assert root is None and factors is None and intervals is None
            assert name is None # but allow inversions
            note_list = NoteList(notes)
            # recover intervals and root, and continue to init as normal:
            intervals = NoteList(notes).ascending_intervals()
            root = note_list[0]

        self.root, chord_name = self._parse_root(name, root)

        # recover factor offsets, intervals from root, and inversion position from input args:
        self.factors, self.root_intervals, inversion = self._parse_input(chord_name, factors, intervals, inversion, inversion_degree, qualifiers, allow_note_name=True)
        # note that while self.inversion in AbstratChord comes out as strictly int or None
        # here we allow it to be a string denoting the bass note, which we'll correct in a minute

        # mapping of chord factors to intervals from tonic:
        self.factor_intervals = {i.extended_degree: i for i in self.root_intervals}
        # mapping of chord factors to notes:
        self.factor_notes = {degree: (self.root + i) for degree, i in self.factor_intervals.items()}

        # list of notes inside this chord, in root position:
        # self.root_notes = NoteList([self.root + i for i in self.root_intervals])
        self.root_notes = NoteList(self.factor_notes.values())

        # discover the correct inversion parameters, as well as inverted notes / intervals if they differ from root position:
        inv_params, self.notes, self.intervals = self._parse_inversion(inversion, move_above=move_above)

        self.inversion, self.inversion_degree, self.bass = inv_params

        # quality of a chord is the quality of its third:
        self.quality = qualities.Perfect if 3 not in self.factors else self.factor_intervals[3].quality

        # set sharp preference based on root note:
        self._set_sharp_preference()


    @staticmethod
    def _parse_root(name, root):
        """takes the class's name and root input args
        returns Note object as root,
        and string or None as chord_name"""
        if name is not None:
            root_name, chord_name = parsing.note_split(name)
            root = Note(root_name)
        elif root is not None:
            root = Note(root)
            chord_name = name
        else:
            raise Exception('neither name nor root provided to Chord init, we need one or the other!')
        return root, chord_name


    def _parse_inversion(self, inversion, move_above=True):
        """given an inversion as int (Xth inversion) or string (bass note),
        return canonical forms: (inversion, inversion_degree, bass)
        with respect to already-defined self.root_notes"""
        if inversion is None:
            inversion = inversion_degree = None
            # no inversion, so the bass is just the root, and the notes/intervals are in root position:
            bass = self.root
            inverted_notes, inverted_intervals = self.root_notes, self.root_intervals

            inv_params = (inversion, inversion_degree, bass)
            return (inv_params), inverted_notes, inverted_intervals

        elif isinstance(inversion, int):
            assert 0 < inversion <= (len(self.factors)-1), f'{inversion} is an invalid inversion number for chord with {len(self.factors)} factors'
            inversion_degree = self.root_intervals[inversion].degree
            bass = self.root_notes[inversion]
        elif isinstance(inversion, (Note, str)):
            bass = Note(inversion)

            ####################################################################

            ### here we catch a special case: inversion over a bass note that is not in the specified chord.
            # e.g. something like Chord('D/C#') - it is not really a D major chord,
            # but a voicing of Dmaj7 or something

            if bass not in self.factor_notes.values():
                print(f"    Chord initialised with inversion over {bass}, \n    but {bass} is not in this chord's notes: {list(self.factor_notes.values())}")
                print(f"    Decomposing and reidentifying using recursive init")
                print(f'     Existing root intervals: {self.root_intervals}')
                bass_distance_from_root = bass - self.root

                if bass_distance_from_root < self.root_intervals[-1]:
                    ### e.g. for Am/C case
                    if move_above:
                        print('     Bass note above root would not be above the highest interval in this chord, ')
                        print('      so we shift it up an octave and call it an inversion')
                        bass_distance_from_root += 12  # raise bass-note interval by an octave
                        new_intervals = IntervalList(list(self.root_intervals) + [bass_distance_from_root]) # add bass note to top of chord
                        # recursively re-initialise:
                        self.__init__(intervals=new_intervals, root=self.root, bass=bass)
                        return self._parse_inversion(bass.name)
                    else:
                        raise Exception
                        ### should this trigger chord re-identification by notes instead?
                        print('     Bass note above root would not be above the highest interval in this chord,')
                        print('      so we move it below instead (and shift everything up)')
                        new_intervals = IntervalList([~bass_distance_from_root] + self.root_intervals) # add bass note below the root
                        print(f' new_intervals before transposition: {new_intervals}')
                        new_intervals = new_intervals - ~bass_distance_from_root # transpose interval list upward so that bass is the new root
                        print(f' new_intervals after transposition: {new_intervals}')
                        # recursively re-initialise:
                        self.__init__(intervals=new_intervals, root=bass)
                        # this is now NOT an inversion:
                        return self._parse_inversion(None)
                else:
                    ### e.g. for D/C# case
                    print('     Throwing bass note on top of this chord and calling it an inversion')
                    new_intervals = IntervalList(list(self.root_intervals) + [bass_distance_from_root])
                assert new_intervals == new_intervals.sorted()
                print(f'    New intervals: {new_intervals}')
                # recursively re-initialise:
                self.__init__(intervals=new_intervals, root=self.root, bass=bass)
                return self._parse_inversion(bass.name)

            ####################################################################

            inversion_degree = [k for k,v in self.factor_notes.items() if v == bass][0]
            # get inversion from inversion_degree:
            for x, deg in enumerate(sorted(self.factors.keys())):
                if inversion_degree == deg:
                    inversion = x
                    break
            if isinstance(inversion, str):
                pdb.set_trace()

        # infer inverted note order by finding the bass's place in our root_notes notelist:
        bass_place = [i for i, n in enumerate(self.root_notes) if n == bass][0]
        assert inversion == bass_place ### is this always true?
        # and rearranging the notes by rotation, e.g. from ordering [0,1,2] to [1,2,0]:
        # inverted_notes = self.root_notes.rotate(bass_place)
        # inverted_intervals = [Interval(0)] + [n - bass for n in inverted_notes[1:]]
        inverted_intervals = self.root_intervals.invert(bass_place)
        inverted_notes = [bass + i for i in inverted_intervals]

        inv_params = (inversion, inversion_degree, bass)
        return (inv_params), inverted_notes, inverted_intervals

    @property
    def _inv_string(self):
        """inversion string, used internally by suffix method (and inherited by subclasses)"""
        return f'/{self.bass.name}' if (self.inversion is not None) else ''

    def _detect_sharp_preference(self, default=False): #tonic, quality='major', default=False):
        """detect if a chord should prefer sharp or flat labelling
        depending on its tonic and quality"""
        if self.quality.major:
            if self.root in sharp_major_tonics:
                return True
            elif self.root in flat_major_tonics:
                return False
            else:
                return default
        elif self.quality.minor:
            if self.root in sharp_minor_tonics:
                return True
            elif self.root in flat_minor_tonics:
                return False
            else:
                return default
        else:
            return default

    def _set_sharp_preference(self, prefer_sharps=None):
        """set the sharp preference of this Chord,
        and of all notes inside this Chord,
        including the tonic, root, and constituent factors"""
        if prefer_sharps is None:
            # detect from object attributes
            prefer_sharps = self._detect_sharp_preference()

        self.prefer_sharps = prefer_sharps
        self.root._set_sharp_preference(prefer_sharps)
        self.bass._set_sharp_preference(prefer_sharps)
        for n in self.notes:
            n._set_sharp_preference(prefer_sharps)

    @property
    def sharp_notes(self):
        """returns notes inside self, all with sharp preference"""
        return NoteList([Note(n.chroma, prefer_sharps=True) for n in self.notes])

    @property
    def flat_notes(self):
        """returns notes inside self, all with flat preference"""
        return NoteList([Note(n.chroma, prefer_sharps=False) for n in self.notes])

    @property
    def name(self):
        return f'{self.root.name}{self.suffix}'



    def __str__(self):
        # note_list = self.inverted_notes
        # interval_short_names = ['Root'] + [i.short_name for i in self.intervals[1:]]
        # intervals_str = ', '.join(interval_short_names)
        # return f'♫ {self.name}  | {intervals_str} |'
        notes_str = [] # notes are annotated with accent marks depending on which octave they're in wrt root
        for i, n in zip(self.intervals, self.notes):
            assert (self.bass + i) == n, f'bass ({self.bass}) + interval ({i}) should be {n}, but is {self.bass + i}'
            if i < -12:
                notes_str.append(f'{n}\u0324') # lower diaresis
            elif i < 0:
                notes_str.append(f'{n}\u0323') # lower dot
            elif i < 12:
                notes_str.append(str(n))
            elif i < 24:
                notes_str.append(f'{n}\u0307') # upper dot
            else:
                notes_str.append(f'{n}\u0308') # upper diaresis
        notes_str = ', '.join(notes_str)

        return f'♬ {self.name} [ {notes_str} ]'

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        """Chords are equal to others on the basis of their root, factors and inversion"""
        if type(other) == Chord:
            return (self.factors == other.factors) and (self.inversion == other.inversion) and (self.root == other.root)
        else:
            raise TypeError(f'Chords can only be compared to other Chords')

    # enharmonic equality:
    def enharmonic_to(self, other):
        """Compares enharmonic equivalence across Chords,
        i.e. whether they contain the exact same notes (but not necessarily in the same order),
        or with Chord and AbstractChord, i.e. do they contain the same intervals"""
        if isinstance(other, Chord):
            matching_notes = 0
            for note in self.notes:
                if note in other.notes:
                    matching_notes += 1
            if matching_notes == len(self.notes) and len(self.notes) == len(other.notes):
                return True
            else:
                return False
        elif isinstance(other, AbstractChord):
            return self.intervals == other.intervals
        else:
            raise TypeError(f'Enharmonic equivalence operator & not defined between Chord and: {type(other)}')

    # enharmonic comparison operator:
    def __and__(self, other):
        return self.enharmonic_to(other)

    ### relative majors/minors are not very well-defined for chords (as opposed to keys), but we can have them anyway:
    @property
    def relative_minor(self):
        # assert not self.minor, f'{self} is already minor, and therefore has no relative minor'
        assert self.quality.major, f'{self} is not major, and therefore has no relative minor'
        rel_root = relative_majors[self.root.name]
        new_factors = ChordFactors(self.factors)
        new_factors[3] -= 1 # flatten third
        return Chord(factors=new_factors, root=rel_root, inversion=self.inversion)

    @property
    def relative_major(self):
        # assert not self.major, f'{self} is already major, and therefore has no relative major'
        assert self.quality.minor, f'{self} is not minor, and therefore has no relative major'
        rel_root = relative_majors[self.root.name]
        new_factors = ChordFactors(self.factors)
        new_factors[3] += 1 # raise third
        return Chord(factors=new_factors, root=rel_root, inversion=self.inversion)

    @property
    def relative(self):
        if self.quality.major:
            return self.relative_minor
        elif self.quality.minor:
            return self.relative_major
        else:
            raise Exception(f'Chord {self} is neither major or minor, and therefore has no relative')

    def __invert__(self):
        """inversion operator on Chords returns the relative major or minor"""
        return self.relative

    def _get_flags(self):
        """Returns a list of the boolean flags associated with this object"""
        flags_names = {
                       'inverted': self.inverted,
                       'minor': self.minor,
                       'major': self.major,
                       'suspended': self.suspended,
                       'diminished': self.diminished,
                       'augmented': self.augmented,
                       'indeterminate': self.indeterminate,
                       'fifth chord': self.fifth_chord,
                       'extended': self.extended,

                       }
        return [string for string, attr in flags_names.items() if attr]

    #### useful properties:

    @property
    def properties(self):
        flags = ', '.join(self._get_flags())
        return f"""
        {str(self)}
        Type:           {type(self)}

        Name:           {self.name}
        Root:           {self.root}
        Intervals:      {self.intervals}
        Notes:          {self.notes}

        Factors:        {self.factors}
        Inversion:      {self.inversion}
          (bass note):  {self.bass}

        Suffix:         {self.suffix}
        Quality:        {self.quality}

        SharpPref:      {self.prefer_sharps}

        Flags:          {flags}
        ID:             {id(self)}"""

    def summary(self):
        print(self.properties)


    #### audio methods:

    # wrappers for the NoteList audio methods of self.notes:
    def _waves(self, *args, **kwargs):
        return self.notes._waves(*args, **kwargs)

    def _chord_wave(self, *args, **kwargs):
        return self.notes._chord_wave(*args, **kwargs)

    def _melody_wave(self, *args, **kwargs):
        return self.notes._melody_wave(*args, **kwargs)

    def play(self, *args, **kwargs):
        self.notes.play(*args, **kwargs)


################################################################################

##### attempt no2 at chord types/rarities:

chord_names_by_rarity = { 0: ['', 'm', '7', 'm7', '5'],   # basic chords: major/minor triads, dom/minor 7s, and power chords
                          1: ['maj7', 'mmaj7', '+', 'sus4', 'add9', '(no5)'], # maj/mmaj 7s, augs, and common alterations like sus2/4 and add9
                          2: ['dim', 'dim7', 'dim9', 'hdim7', 'sus2', '6', 'm6'], # dissonant chords: diminished, 6ths and sus2s
                          3: ['dm9'] + [f'{q}{d}' for q in ('', 'm', 'maj', 'mmaj') for d in (9,11,13)], # the four major types of extended chords, and dominant minor 9ths
                          4: [], 5: [], 6: [], 7: []}

# these chord names cannot be modified:
unmodifiable_chords = ['', '5', '(no5)']
# '' because most ordinary chord types imply modification from major, i.e. 'sus4' implies ['' + 'sus4']
# '5' and '(no5)' because they both imply simple removals of triad degrees, and are best handled by fuzzy matching


# # ensure that we have exhausted all the chord names in qualities.chord_types
# assert len([c for c in qualities.chord_types if c not in chord_name_rarities_proxy]) == 0
# # assert len([c for c in qualities.chord_modifiers if c not in chord_name_rarities]) == 0
#

# loop over these chords and build a dict mapping intervals/factors to their names:
factors_to_chord_names, intervals_to_chord_names = {}, {}
# (while adding chord modifications as well)

# since we change chord_names_by_rarity while trying to loop across it, we loop across a proxy dict instead:
# chord_names_by_rarity_proxy = chord_names_by_rarity.copy()
chord_name_rarities = unpack_and_reverse_dict(chord_names_by_rarity)

# starting_size1 = len(chord_names_by_rarity_proxy)
# starting_size2 = sum([len(v) for v in chord_names_by_rarity_proxy.values()])

new_rarities = {i: [] for i in range(8)}

for rarity, chord_names in chord_names_by_rarity.items():
    print(f'Handling rarity={rarity}, chords={chord_names}')

    for chord_name in chord_names:
        base_chord = AbstractChord(chord_name)
        print(f'Handling base chord: r:{rarity} {chord_name}')

        if base_chord.factors in factors_to_chord_names or base_chord.intervals in intervals_to_chord_names:
            log(f'  {chord_name} clash with {intervals_to_chord_names[base_chord.intervals]}')
        else:
            factors_to_chord_names[base_chord.factors] = chord_name
            intervals_to_chord_names[base_chord.intervals] = chord_name

            # now: add chord modifications to each base chord as well, increasing rarity accordingly
            for mod_name, modifier in qualities.chord_modifiers.items():
                # add a modification if it does not already exist by name and is valid on this base chord:
                # (we check if chord_name is major because the modifiers on their own apply to major chords,
                #  i.e. the chord 'sus2' implies ['' + 'sus2'])
                if chord_name not in unmodifiable_chords and modifier.valid_on(base_chord.factors):
                    altered_name = chord_name + mod_name

                    altered_factors = base_chord.factors + modifier
                    altered_intervals = altered_factors.to_intervals()
                    # avoid double counting: e.g. this ensures that '9sus4' and 'm9sus4' are treated as one chord, '9sus4', despite both being a valid chord init
                    if altered_factors not in factors_to_chord_names and altered_intervals not in intervals_to_chord_names:
                        factors_to_chord_names[altered_name] = altered_factors

                        intervals_to_chord_names[altered_intervals] = altered_name

                        # figure out the rarity of this modification and add it to the rarity dict:
                        mod_rarity = chord_name_rarities[mod_name] if (mod_name in chord_name_rarities) else 3
                        altered_rarity = chord_name_rarities[chord_name] + mod_rarity
                        new_rarities[altered_rarity].append(altered_name)

                        # finally: do the same again, but one level deeper!
                        for mod2_name, modifier2 in qualities.chord_modifiers.items():
                            # do not apply the same modifier twice, and do so only if valid:
                            if (modifier2 is not modifier) and modifier2.valid_on(altered_factors):
                                # and, special case, not if (no5) is the first mod, since it always comes last:
                                if mod_name != '(no5)':
                                    altered2_name = altered_name + mod2_name

                                    altered2_factors = altered_factors + modifier2
                                    altered2_intervals = altered2_factors.to_intervals()
                                    # avoid the lower triangular: (e.g. m(no5)add9 vs madd9(no5))
                                    if altered2_factors not in factors_to_chord_names and altered2_intervals not in intervals_to_chord_names:
                                        factors_to_chord_names[altered2_name] = altered2_factors
                                        intervals_to_chord_names[altered2_intervals] = altered2_name

                                        # these are all rarity 7, the 'legendary chords'
                                        new_rarities[7].append(altered2_name)

# update chord_names_by_rarity with new rarities:
for r, names in new_rarities.items():
    chord_names_by_rarity[r].extend(names)

# re-instantiate the reverse dict since we've added to the forward one (but we still needed it earlier:)
chord_name_rarities = unpack_and_reverse_dict(chord_names_by_rarity)



### WIP, incomplete class
class ChordVoicing(Chord):
    """a Chord built on a specific note of a specific pitch, whose members are OctaveNotes.
    unlike its parent classes, a ChordVoicing can have repeats of the same Note at multiple pitches.

    exact same attributes as chord, except also having a self.octave attribute defined"""
    def __init__(self, name=None, root=None, octave=None, factors=None, intervals=None, inversion=None, qualifiers=None, in_key=None):

        self.root, self.octave, chord_name = self._parse_root_octave(name, root, octave)

        self.factors, self.intervals, self.inversion = self._parse_input(chord_name, factors, intervals, inversion, inversion_degree, qualifiers)

        ### TBI: everything else

    @staticmethod
    def _parse_root_octave(name, root, octave):
        """takes the class's name and root input args
        and returns an OctaveNote object as root, integer as octave,
        and string or None object as chord_name"""
        # parse root and octave:
        if name is not None:
            assert root is None, f"ChordVoicing initialised with name string ({name}) as root, but also received mutually exclusive root keyword: {root}"
            assert octave is not None, f"ChordVoicing initialised with name string ({name}) as root but no octave arg provided"
            root_name, chord_name = parsing.note_split(name)
            root = Note(root_name)
            if len(chord_name) == 0:
                chord_name = None
            return root, octave, chord_name
        else:
            if isinstance(root, OctaveNote):
                # if root is an OctaveNote, we accept that:
                root = root
                assert octave is None, f"ChordVoicing initialised with OctaveNote ({root}) as root but also received mutually exclusive octave keyword: {octave}"
                octave = root.octave
            elif isinstance(root, Note):
                assert octave is not None, f"ChordVoicing initialised with Note ({root}) as root but no octave arg provided"
                root = root.in_octave(octave)
                octave = octave
            elif isinstance(root, str):
                if root[-1].isnumeric():
                    # string that seems to be an OctaveNote
                    assert octave is None, f"ChordVoicing initialised with string denoting OctaveNote ({root}) but also received mutually exclusive octave keyword: {octave}"
                    root = OctaveNote(root)
                    octave = root.octave
                else:
                    assert octave is not None, f"ChordVoicing initialised with Note string ({root}) as root but no octave arg provided"
                    octave = octave
                    root = Note(root).in_octave(octave)
            return root, octave, name


def unit_test():
    # test inversion by factor/bass, AbstractChord->Chord initialisation, and unusual note names:
    test(Chord('E#m7/C'), AbstractChord('m7/2').root('F'))
    # test correct production of root notes/intervals and inverted notes/intervals:
    test(Chord('Am/C').root_notes, Chord('Am').root_notes)
    test(Chord('Am/C').root_intervals, Chord('Am').root_intervals)
    test(Chord('Am/C').notes, Chord('C6(no5)').notes)
    test(Chord('Am/C').intervals, Chord('C6(no5)').intervals)

    # test chord factor init by strings and lists:
    test(ChordFactors('1-♭3-b5'), ChordFactors(['1', '♭3', 'b5']))

    # test recursive init:
    print(Chord('D/C#'))
    print(Chord('Amaj7/B'))

if __name__ == '__main__':
    unit_test()
