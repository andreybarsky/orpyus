from . import notes, parsing, _settings
from .parsing import fl, sh, nat, dfl, dsh
from .intervals import Interval, IntervalList
from .notes import Note, NoteList
from .scales import Scale, ScaleFactors, ScaleDegree, ScaleChord, NaturalMajor, NaturalMinor, parallel_scales, canonical_scale_interval_names
from .chords import Chord, AbstractChord
from .util import check_all, precision_recall, reverse_dict, log

from collections import Counter
from functools import cached_property
from pdb import set_trace

# natural notes in order of which are flattened/sharpened in a key signature:
flat_order = ['B', 'E', 'A', 'D', 'G', 'C', 'F']
sharp_order = ['F', 'C', 'G', 'D', 'A', 'E', 'B']

# # circle of 5ths in both directions as linked lists:
# co5s_clockwise = {Note('C')+(7*i) : Note('C')+(7*(i+1)) for i in range(12)}
# co5s_counterclockwise = {Note('C')-(7*i) : Note('C')-(7*(i+1)) for i in range(12)}


relative_co5_distances = IntervalList([0, 5, 2, 3, 4, 1, 6, 1, 4, 3, 2, 5])
# this list looks funny, but it's the circle-of-fifths distance for each key with tonic
# N+i, with respect to the key that has tonic N.
# e.g. co5_distance between E and D is based on the interval between E and D,
# i.e. Note('E') - Note('D'), which is 2, or Note('D') - Note('E'), which is 10
# so the co5_distance is relative_co5_distances[2] (or [10]), which either way is 2.
# this works for any diatonic key, and is just a property of how the notes are arranged

# # build co5 distance between key tonics:
# co5_distances = {}
# for n_left in notes.chromatic_notes:
#     for n_right in notes.chromatic_notes:
#         num_steps = 0
#         clockwise_n = Note(n_left)
#         counterclockwise_n = Note(n_left)
#         while (clockwise_n != n_right) and (counterclockwise_n != n_right):
#             clockwise_n += 7
#             counterclockwise_n -= 7
#             num_steps += 1
#         co5_distances[(n_left, n_right)] = num_steps

class Key(Scale):
    """a Scale that is also rooted on a tonic, and therefore associated with a set of notes"""
    # def __init__(self, scale_name=None, intervals=None, tonic=None, notes=None, mode=1, chromatic_intervals=None, chromatic_notes=None, stacked=True, alias=None):
    """Initialised in one of three ways:

    1. from 'notes' arg, as a list or string of Notes or Note-like objects,
    in which case we parse the tonic and intervals from there

    2. from 'name' arg, when as a proper Key name (like "C#" or "Bb harmonic minor" or "Gbb lydian b5"),
        in which case we extract the tonic note from the string and initialise the rest as with Scale class.

    3. from 'tonic' arg, as a Note or string that casts to Note,
        in combination with any other args that would initialise a valid Scale object.
        i.e. one of 'scale_name' or 'intervals'."""

    def __init__(self, name=None, intervals=None, factors=None,
                    alterations=None, chromatic_intervals=None,
                    notes=None, chromatic_notes=None, tonic=None,
                    mode=1):

        name, intervals, factors, notes, tonic = self._reparse_key_args(name, intervals, factors, notes, tonic)

        # if notes have been provided, parse them into tonic and intervals:
        if notes is not None:
            # ignore intervals/factors/root inputs
            assert tonic is None and intervals is None and name is None
            note_list = NoteList(notes)
            assert len(note_list) == 7, f"a Key must have exactly 7 notes, but there are {len(note_list)} in: {note_list}"
            # recover intervals and tonic, and continue to init as normal:
            intervals = NoteList(notes).ascending_intervals()
            tonic = note_list[0]

        # get correct tonic and scale name from (key_name, tonic) input args:
        self.tonic, scale_name = self._parse_tonic(name, tonic)
        if scale_name == '': # catch special case of: only tonic is given
            scale_name = 'natural major'

        if chromatic_notes is not None:
            assert chromatic_intervals is None, 'Key init can only include ONE of chromatic_notes or chromatic_intervals, but both are supplied'
            # though TBI, this could be fixed to be more generous
            chromatic_notes = NoteList(chromatic_notes)
            # re-parse into chromatic intervals and let Scale init handle it
            chromatic_intervals = [n - self.tonic for n in chromatic_notes]

        # initialise everything else as Scale class does:
        super().__init__(scale_name, intervals, factors, alterations, chromatic_intervals, mode)
        # (this sets self.factors, self.degrees, self.intervals, self.chromatic_intervals, and their mappings

        # set Key-specific attributes: notes, degree_notes, etc.
        self.notes = NoteList([self.tonic + i for i in self.intervals])
        self.chromatic_notes = [self.tonic + iv for iv in self.chromatic_intervals]

        self.degree_notes = {d: self.tonic + iv for d,iv in self.degree_intervals.items()}
        self.factor_notes = {f: self.tonic + iv for f,iv in self.factor_intervals.items()}
        self.interval_notes = {iv:n for n,iv in zip(self.notes, self.intervals)}

        self.note_degrees = reverse_dict(self.degree_notes)
        self.note_factors = reverse_dict(self.factor_notes)
        self.note_intervals = reverse_dict(self.interval_notes)



        # # used only for Keys with strange chromatic notes not built on integer degrees, like blues notes
        # if self.chromatic_intervals is not None:
        #     self.chromatic_notes = NoteList([self.tonic + i for i in self.chromatic_intervals])
        #     self.diatonic_notes = NoteList([self.tonic + i for i in self.diatonic_intervals.pad()])
        # else:
        #     self.chromatic_notes = None
        #     self.diatonic_notes = self.notes

        # # we don't store the unison interval in the Scale.interval attr, because of mode rotation
        # # so we pad them here:
        # padded_intervals = [Interval(0)] + self.diatonic_intervals
        # self.note_intervals = {self.notes[i]: padded_intervals[i] for i in range(7)}
        # self.interval_notes = reverse_dict(self.note_intervals)
        # # self.interval_notes = {padded_intervals[i]: self.notes[i] for i in range(7)}
        #
        # self.degree_notes = {d: self.notes[d-1] for d in range(1,8)}
        # self.note_degrees = reverse_dict(self.degree_notes)
        # # self.note_degrees = {self.notes[d-1]: d for d in range(1,8)}
        #
        # # these are the same for Key objects, but may differ for Subkeys:
        # self.base_degree_notes = self.degree_notes
        # self.note_base_degrees = self.note_degrees

        # update this Key's notes to prefer sharps/flats depending on its tonic:
        self._set_sharp_preference()
        self._set_key_signature()


    ####### internal init subroutines:
    def _reparse_key_args(self, name, intervals, factors, notes, tonic):
        """detect if notes or factors etc. have been given as first arg instead of name,
        and return corrected (name, intervals, factors, notes, tonic) tuple."""
        # this method overrides Scale._reparse_args and also looks for note and tonic args

        # if first arg is an IntervalList or NoteList, treat them as such:
        if isinstance(name, IntervalList):
            intervals = name
            name = None
        elif isinstance(name, NoteList):
            notes = name
            name = None
        elif isinstance(name, (list, tuple)):
            # interpret a base list as needing to be cast to a NoteList by default
            notes = NoteList(name)
            name = None
        elif (isinstance(name, str) and name[0].isnumeric()) or (isinstance(name, (ScaleFactors, dict))):
            # initialised by ScaleFactors, either from string or direct dict:
            if type(name) is not ScaleFactors:
                name = ScaleFactors(name)
            factors = name
            name = None
        elif type(name) is str:
            # can only be notelist or key name
            # first, either must begin with a note:
            tonic_idx = parsing.begins_with_valid_note_name(name)
            assert tonic_idx > 0, f"Key init by string must start with a valid note name, but got: {name}"
            assert tonic is None, f"Key init by string parsed tonic {name[:tonic_idx]} but got conflicting tonic arg: {tonic}"
            _tonic, rest_name = parsing.note_split(name)

            # then check if tonic is followed by more notes
            rest_notes = parsing.parse_out_note_names(rest_name, graceful_fail=True)
            if not rest_notes:
                # failure to parse as note list, so treat as key name instead
                name = name
            else:
                # parsed as a valid note list
                notes = NoteList(name)
                name = None
        elif isinstance(name, Scale):
            # accept re-casting from Scale or Key here too
            # just strip the factors and tonic attrs from a Scale or Key object:
            factors = name.factors
            if isinstance(name, Key):
                tonic = name.tonic
            else:
                assert tonic is not None, "Key arg init by re-parsing Scale object requires a tonic arg"
            name = None
        elif name is not None:
            raise TypeError(f'Key init did not expect first arg of type: {type(name)}')
        else:
            # name is None, assert that another arg has been provided
            assert factors is not None or intervals is not None or notes is not None
            # raise Exception('Should never happen')

        return name, intervals, factors, notes, tonic


    @staticmethod
    def _parse_tonic(name, tonic):
        """takes the class's name and tonic args, and determines which has been given.
        returns root as a Note object, and scale name as string or None"""
        if name is not None:
            if parsing.begins_with_valid_note_name(name):
                # parse as the name of a Key:
                assert tonic is None, f'Key object initiated by Key name ({name}) but provided conflicting tonic arg ({tonic})'
                tonic, scale_name = parsing.note_split(name)
                scale_name = scale_name.strip()
            else:
                assert tonic is not None, f'Key object initiated by Scale name ({name}) but no tonic note provided'
                scale_name = name
            tonic = Note(tonic)
        elif tonic is not None:
            tonic = Note(tonic)
            scale_name = name # i.e. None
        else:
            raise Exception('neither scale_name nor tonic provided to Key init, we need one or the other!')
        return tonic, scale_name

    def _detect_sharp_preference(self, default=False):
        """detect if this key's tonic note should prefer sharp or flat labelling
        depending on its chroma and quality"""
        if (self.quality.major and self.tonic in notes.sharp_major_tonics) or (self.quality.minor and self.tonic in notes.sharp_minor_tonics):
            return True
        elif (self.quality.major and self.tonic in notes.flat_major_tonics) or (self.quality.minor and self.tonic in notes.flat_minor_tonics):
            return False
        else:
            # fall back on whatever the tonic prefers:
            # (which catches the distinction between Key('F#') and Key('Gb'))
            return self.tonic.prefer_sharps

    def _set_sharp_preference(self, prefer_sharps=None):
        """set the sharp preference of this Key,
        and of all notes inside this Key, in-place."""
        if prefer_sharps is None:
            # detect from tonic and quality
            prefer_sharps = self._detect_sharp_preference()

        self.tonic._set_sharp_preference(prefer_sharps)
        # by default, the Key's prefer_sharps attribute is the same as the tonic:
        self.prefer_sharps = prefer_sharps

        # but in general, flat/sharp preference of a Key is decided by having one note letter per degree of the scale:

        if self.is_natural or self.is_subscale:
            # computation not needed for non-natural scales; and no idea how to handle subscales yet
            # just assign same sharp preference as tonic to every note:
            for n in self.notes:
                n._set_sharp_preference(prefer_sharps)

        else:
            # compute flat/sharp preference by assigning one note to each natural note name
            tonic_nat = self.tonic.chroma[0] # one of the few cases where note sharp preference matters
            next_nat = parsing.next_natural_note[tonic_nat]
            for d in range(2,8):
                n = self.degree_notes[d]
                if n.name == next_nat:
                    # this is a natural note, so its sharp preference shouldn't matter,
                    # but set it to the tonic's anyway for consistency
                    n._set_sharp_preference(prefer_sharps)
                else:
                    # which accidental would make this note's chroma include the next natural note?
                    if n.flat_name[0] == next_nat:
                        n._set_sharp_preference(False)
                    elif n.sharp_name[0] == next_nat:
                        n._set_sharp_preference(True)
                    else:
                        # this note needs to be a double sharp or double flat or something
                        # log(f'Found a possible case for a double-sharp or double-flat: degree {d} ({n}) in scale: {self}')
                        # fall back on same as tonic:
                        n._set_sharp_preference(prefer_sharps)
                next_nat = parsing.next_natural_note[next_nat]

    def _set_key_signature(self):
        """reads the sharp and flat preference of the notes inside this Key
        and sets internal attributes reflecting that key signature"""
        self.num_sharps = sum([(sh in n.chroma) for n in self.notes])
        self.num_flats = sum([(fl in n.chroma) for n in self.notes])
        self.key_signature = fl* self.num_flats + sh*self.num_sharps

        # expressed as a dict of accidental offsets:
        self.key_signature_values = {}
        for n in self.notes:
            if sh in n.chroma:
                self.key_signature_values[n] = 1
            elif fl in n.chroma:
                self.key_signature_values[n] = -1

        # expressed as a string:
        # (this is an inefficient loop and could be optimised if needed)
        flat_str = ' '.join([f'{n}{fl}' for n in flat_order if f'{n}{fl}' in self.notes])
        sharp_str = ' '.join([f'{n}{sh}' for n in sharp_order if f'{n}{sh}' in self.notes])
        self.key_signature_str = f'{flat_str} {sharp_str}'

    @cached_property
    def scale_name(self):
        """a Key's scale_name is whatever name it would get as a Scale"""
        return Scale.get_name(self) # inherits from Scale

    @cached_property
    def scale(self):
        """returns the abstract Scale associated with this key"""
        return Scale(factors=self.factors)

    @property
    def members(self):
        # a Key's members are its notes
        return self.notes

    def get_chord(self, degree, order=3):
        """overwrites Scale.get_chord, returns a Chord object instead of an AbstractChord"""
        abstract_chord = Scale.get_chord(self, degree, order)
        root_interval = self.get_interval_from_degree(degree)
        root_note = self.tonic + root_interval
        chord_obj = abstract_chord.on_bass(root_note)
        # initialised chords inherit this key's sharp preference:
        chord_obj._set_sharp_preference(self.prefer_sharps)
        return chord_obj

    def get_tertian_chord(self, degree, order=3, prefer_chromatic=False):
        """overwrites Scale.get_tertian_chord, returns a Chord object instead of an AbstractChord"""
        abstract_chord = Scale.get_tertian_chord(self, degree, order, prefer_chromatic=prefer_chromatic)
        root_interval = self.get_interval_from_degree(degree)
        root_note = self.tonic + root_interval
        chord_obj = abstract_chord.on_bass(root_note)
        # initialised chords inherit this key's sharp preference:
        chord_obj._set_sharp_preference(self.prefer_sharps)
        return chord_obj

    def valid_chords_on(self, degree, *args, display=True, **kwargs):
        """wrapper around Scale.get_valid_chords but feeding it the appropriate root note from this Key"""
        abs_chords = Scale.valid_chords_on(self, degree, *args, display=False, **kwargs) # _root_note = self.degree_notes[degree], **kwargs)
        root_note = self.degree_notes[degree]
        chords = [a.on_bass(root_note) for a in abs_chords]
        if display:
            from src.display import chord_table
            title = f"Valid chords built on degree {degree} of {self}"
            print(title)
            chord_table(chords,
                        columns=['chord', 'notes', 'degrees', 'tert', 'likl', 'cons'],
                        parent_scale=self, parent_degree=degree, margin=' | ', **kwargs)
        else:
            return chords # already in sorted order by valid_chords_on method

    def clockwise(self, value=1):
        """fetch the next key from clockwise around the circle of fifths,
        or if value>1, go clockwise that many steps"""
        return Key(factors=self.factors, tonic=self.tonic + (7*value))
        # reference_key = self if self.major else self.relative_major
        # new_co5s_pos = (co5s_positions[reference_key] + value) % 12
        # # instantiate new key object: (just in case???)
        # new_key = co5s[new_co5s_pos]
        # new_key = new_key if self.major else new_key.relative_minor
        # # set_trace(context=30)
        # return Key(new_key.name)

    def counterclockwise(self, value=1):
        return self.clockwise(-value)

    def mode(self, N):
        """as Scale.mode, but returns Keys with transposed tonics too.
        so that the modes of C major are D dorian, E phrygian, etc."""
        # mod the rotation value into our factor range:
        N = ((N-1) % self.order) + 1
        scale_mode = Scale.mode(self, N)
        mode_tonic = self.degree_notes[N]
        return scale_mode.on_tonic(mode_tonic)

    # @property
    # def modes(self):
    #     return [self.rotate(m) for m in range(1,8)]


    # @property
    # def parallel_modes(self):
    #     """the 'parallel' modes of a Key are all its modes that start on the same tonic"""
    #     return [self.rotate(m) for m in range(1,8)]

    @property
    def modes(self):
        """the modes of a Key are the relative keys that share its notes but start on a different tonic
        i.e. modes of C major are D dorian, E phrygian, etc."""
        return [self.mode(n) for n in range(1,8)]
        # return [Key(notes=Key('C').notes.rotate(i)) for i in range(1,8)]

    # def subscale(self, degrees=None, omit=None, chromatic_intervals=None, name=None):
    #     """as Scale.subscale, but adds this key's tonic as well and initialises a Subkey instead"""
    #     return Subkey(parent_scale=self, degrees=degrees, omit=omit, chromatic_intervals=chromatic_intervals, assigned_name=name, tonic=self.tonic) # [self[s] for s in degrees]


    @property
    def pentatonic(self):
        """as Scale.pentatonic, but returns a Key on the same tonic"""
        return Scale.get_pentatonic(self).on_tonic(self.tonic)

    @property
    def relative_minor(self):
        # assert not self.minor, f'{self} is already minor, and therefore has no relative minor'
        assert self.quality.major, f'{self} is not major, and therefore has no relative minor'
        rel_tonic = notes.relative_minors[self.tonic.name]
        if self.scale in parallel_scales:
            return parallel_scales[self.scale].on_tonic(rel_tonic)
        else:
            raise Exception(f'Relative major/minor not defined for {self}')

    @property
    def relative_major(self):
        # assert not self.minor, f'{self} is already minor, and therefore has no relative minor'
        assert self.quality.minor, f'{self} is not minor, and therefore has no relative major'
        rel_tonic = notes.relative_majors[self.tonic.name]
        if self.scale in parallel_scales:
            return parallel_scales[self.scale].on_tonic(rel_tonic)
        else:
            raise Exception(f'Relative major/minor not defined for {self}')


    @property
    def relative(self):
        if self.quality.major:
            return self.relative_minor
        elif self.quality.minor:
            return self.relative_major
        else:
            raise Exception(f'Key of {self.name} is neither major or minor, and therefore has no relative')

    @property
    def parallel_minor(self):
        if not self.quality.major:
            raise Exception(f'{self.name} is not major, and therefore has no parallel minor')
        else:
            return self.parallel

    @property
    def parallel_major(self):
        if not self.quality.minor:
            raise Exception(f'{self.name} is not minor, and therefore has no parallel major')
        else:
            return self.parallel

    @property
    def parallel(self):
        if self.scale in parallel_scales:
            return parallel_scales[self.scale].on_tonic(self.tonic)
        else:
            raise Exception(f'Parallel major/minor not defined for {self.name}')

    def __invert__(self):
        """~ operator returns the parallel major/minor of a key"""
        return self.parallel

    def __contains__(self, item):
        """if item is an Interval, does it fit in our list of degree-intervals plus chromatic-intervals?
        if it is a Chord, can it be made using the notes in this key?"""
        if isinstance(item, int):
            item = Interval(item)
        elif isinstance(item, str):
            # assume a raw string is a chord, not a note
            item = Chord(item)

        if isinstance(item, Interval):
            return item in self.intervals
        elif isinstance(item, Note):
            return item in self.notes
        elif type(item) is Chord:
            # chord is 'in' this Key if all of its notes are:
            if item.root not in self.notes:
                return False
            else:
                for note in item.notes:
                    if note not in self.notes:
                        return False
            return True
        elif isinstance(item, ScaleChord):
            # ScaleChords exist on a specific degree of their scale/key:
            abs_chord = item.abstract()
            return self.contains_degree_chord(item.degree, abs_chord)
        elif isinstance(item, (list, tuple)):
            # check if each individual item in an iterable is contained here:
            for subitem in item:
                if subitem not in self:
                    return False
            return True
        else:
            raise TypeError(f'Key.__contains__ not defined for items of type: {type(item)}')

    def __eq__(self, other):
        if isinstance(other, Key):
            return self.notes == other.notes
        else:
            raise TypeError(f'__eq__ not defined between Key and {type(other)}')

    def __hash__(self):
        return hash((self.notes, self.diatonic_intervals, self.intervals, self.chromatic_intervals))

    def show(self, tuning='EADGBE', **kwargs):
        """just a wrapper around the Guitar.show method, which is generic to most musical classes,
        so this method is also inherited by all Scale subclasses"""
        from .guitar import Guitar
        Guitar(tuning).show_key(self, **kwargs)

    def play(self, *args, **kwargs):
        # plays the notes in this key (we also add an octave over root on top for resolution)
        # played_notes = NoteList([n for n in self.notes] + [self.tonic])
        # played_notes.play(*args, **kwargs)
        Scale.play(self, *args, on=f'{self.tonic.name}3', **kwargs)

    def progression(self, *degrees, order=3):
        """accepts a sequence of (integer) degrees,
        and produces a ChordProgression in this key rooted on those degrees"""
        # if len(degrees) == 1:
        #     # if a single list or tuple was provided, unpack it here:
        #     degrees = degrees[0]
        from .progressions import Progression
        return Progression(*degrees, scale=self.scale, order=order).on_tonic(self.tonic)

    @property
    def suffix(self):
        # a key's suffix is its scale name (with a leading space),
        # UNLESS it is natural major or minor,
        # in which case it is shortened:
        if self.scale_name == 'natural major':
            return ''
        elif self.scale_name == 'natural minor':
            return 'm'
        else:
            return ' ' + self.scale_name


    @property
    def name(self):
        return f'{self.tonic.chroma}{self.suffix}'

    def __str__(self):
        return f'{self._marker}Key of {self.name}'

    def __repr__(self):
        lb, rb = self.notes._brackets
        if self.chromatic_notes is None:
            note_names = [str(n) for n in self.notes]
        else:
            # show diatonic notes as in normal note list, and chromatic notes in square brackets
            which_chromatic = self.which_intervals_chromatic()
            note_names = [f'[{n}]' if which_chromatic[i]  else str(n)  for i,n in enumerate(self.notes)]
        notes_str = ', '.join(note_names)
        return f'{str(self)}  {lb}{notes_str}{rb}'

    # Key object unicode identifier:
    _marker = _settings.MARKERS['Key']




class KeyChord(Chord, ScaleChord):
    """As ScaleChord, but lives in a Key instead of a Scale,
    and therefore inherits from Chord instead of AbstractChord"""
    def __init__(self, *args, key, degree=None, degree_on_bass=True, **kwargs):
        # initialise as chord:
        Chord.__init__(self, *args, **kwargs)

        # if True, inverted chords are treated as having
        # the scale degree of their bass note, instead of
        # their 'proper' root note:
        self.degree_on_bass = degree_on_bass

        if not isinstance(key, Key):
            key = Key(key)
        if degree is None:
            # auto-infer degree from this chord's root (or bass)
            deg_note = self.root if not degree_on_bass else self.bass
            degree = key.note_degrees[deg_note]
        if not isinstance(degree, ScaleDegree):
            degree = ScaleDegree.from_scale(key.scale, degree)
        self.key = key
        self.scale = key.scale
        self.degree = degree

        # flag whether this chord belongs in the key/scale specified:
        self.in_key = self in self.key
        self.in_scale = self.scale.contains_degree_chord(degree, self)

        # KeyChord inherits its key's sharp preference unless explicitly overwritten:
        if 'prefer_sharps' not in kwargs:
            self.prefer_sharps = self.key.prefer_sharps

    def __repr__(self):
        in_str = 'not ' if not self.in_key else ''
        return f'{Chord.__repr__(self)} ({in_str}in: {self.key})'


def matching_keys(chords=None, notes=None, exclude=None, require_tonic=True, require_roots=True,
                    display=True, return_matches=False, natural_only=False,
                    upweight_first=True, upweight_last=True, upweight_chord_roots=True, upweight_key_tonics=True, upweight_pentatonics=False, # upweight_pentatonics might be broken
                    min_recall=0.8, min_precision=0.7, min_likelihood=0.5, max_results=5):
    """from an unordered set of chords, return a dict of candidate keys that could match those chord.
    we make no assumptions about the chord list, except in the case of assume_tonic, where we slightly
    privilege keys that have their tonic on the root of the starting chord in chord list."""

    # TBI: if this needs to be made faster, could we check across all Scale intervals, rather than across all Key notes?

    if isinstance(chords, str):
        try:
            chord_names = ChordList(chords)
        except:
            # catch an edge case: have we been fed a note list as first arg?
            note_names = parse_out_note_names(chords, graceful_fail=True)
            if note_names is not False:
                # reallocate args
                notes = NoteList(note_names)
                chords = None
            else:
                raise ValueError(f'Could not understand matching_keys string input as a list of chords or notes: {chords}')

    if chords is not None:
        if not isinstance(chords, ChordList):
            chords = ChordList(chords)
        # assert isinstance(chords, (list, tuple)), f'chord list input to matching_keys must be an iterable, but got: {type(chords)}'
        # chords = [Chord(c) if isinstance(c, str) else c for c in chords]

        # assert check_all(chords, 'isinstance', Chord), f"chord list input to matching_keys must be a list of Chords (or strings that cast to Chords), but got: {[type(c) for c in chords]}"

        # keep track of the number of times each note appears in our chord list,
        # which will be the item weights to our precision_recall function:
        note_counts = Counter()

        for chord in chords:
            note_counts.update(chord.notes)
            if upweight_chord_roots:
                # increase the weight of the root note too:
                note_counts.update([chord.root])

        # if assume_tonic:
        # upweight all the notes of the first and last chord
        first_assumed_tonic = chords[0].root
        last_assumed_tonic = chords[-1].root
        if upweight_first:
            note_counts.update(chords[0].notes)
            # and the tonic especially:
            note_counts.update([chords[0].notes[0]] * 2)
        if upweight_last:
            note_counts.update(chords[-1].notes)
            note_counts.update([chords[-1].notes[0]] * 2)
    elif notes is not None:
        # just use notes directly
        notes = NoteList(notes)
        note_counts = Counter(notes)
        # if assume_tonic:
        first_assumed_tonic = notes[0]
        last_assumed_tonic = notes[-1]
        if upweight_first:
            note_counts.update([notes[0]])
        if upweight_last:
            note_counts.update([notes[-1]])
    else:
        raise Exception(f'matching_keys requires one list of either: chords or notes')

    if exclude is None:
        exclude = [] # but should be a list of Note objects
    elif exclude is not None and len(exclude) > 0:
        assert isinstance(exclude[0], (str, Note)), "Objects to exclude must be Notes, or strings that cast to notes"
        exclude = NoteList(exclude)

    unique_notes = list(note_counts.keys())

    # set min precision to be at least the fraction of unique notes that have been given
    min_precision = min([min_precision, len(unique_notes) / 7]) # at least the fraction of unique notes that have been given

    candidates = {} # we'll build a list of Key object candidates as we go
    # keying candidate Key objs to (rec, prec, likelihood, consonance) tuples

    if require_tonic:
        # we only try building scales with their tonic on a root or bass of a chord in the chord list
        if chords is not None:
            candidate_tonics = list(set([c.root for c in chords] + [c.bass for c in chords]))
        else: # or the first note in the note list
            candidate_tonics = [notes[0]]
    else:
        # we try building keys on any note that occurs in the chord list:
        candidate_tonics = unique_notes

    if natural_only:
        # search only natural major and minor scales:
        shortlist_interval_scale_names = {NaturalMajor.intervals: 'natural major', NaturalMinor.intervals: 'natural minor'}
    else:
        # search all known scales and modes
        shortlist_interval_scale_names = canonical_scale_interval_names

    for t in candidate_tonics:
        for intervals, mode_names in shortlist_interval_scale_names.items():
            candidate_notes = [t] + [t + i for i in intervals]

            does_not_contain_exclusions = True
            for exc in exclude:
                if exc in candidate_notes:
                    does_not_contain_exclusions = False
                    break
            if require_roots and (chords is not None):
                for c in chords:
                    if c.root not in candidate_notes:
                        does_not_contain_exclusions = False
                        break
            if does_not_contain_exclusions:
                # initialise candidate object:
                # (this can be removed for a fast method; it's mostly for upweighting key fifths)

                this_cand_weights = dict(note_counts)
                if upweight_key_tonics:
                    # count the key's tonic several times more, because it's super important
                    this_cand_weights.update({t: 3})
                if upweight_pentatonics:
                    candidate = Key(notes=candidate_notes)
                    # count the notes in this key's *pentatonic* scale as extra:
                    this_cand_weights.update({n:1 for n in candidate.pentatonic.notes})

                precision, recall = precision_recall(unique_notes, candidate_notes, weights=this_cand_weights)

                if recall >= min_recall and precision >= min_precision:
                    # initialise candidate if it has not been already:
                    if not upweight_pentatonics:
                        candidate = Key(notes=candidate_notes)

                    likelihood = candidate.likelihood
                    # if assume_tonic:
                    #     # slightly upweight the likelihood of keys with tonics that are the roots of the first or last chord:
                    #     if candidate.tonic == first_assumed_tonic:
                    #         likelihood += 0.051
                    #     if candidate.tonic == last_assumed_tonic:
                    #         likelihood += 0.049
                    # now handled by rec/prec

                    consonance = candidate.consonance
                    if likelihood >= min_likelihood:
                        candidates[candidate] = {'precision': round(precision, 2),
                                                'likelihood': round(likelihood,2),
                                                    'recall': round(recall,    2),
                                                'consonance': round(consonance,3)}


    # return sorted candidates dict: (note that unlike in matching_chords we sort by precision rather than recall first)
    sorted_cands = sorted(candidates,
                          key=lambda c: (candidates[c]['precision'],
                                         candidates[c]['likelihood'],
                                         candidates[c]['recall'],
                                         candidates[c]['consonance']),
                          reverse=True)[:max_results]


    if display:
        # print result as nice dataframe instead of returning a dict
        if chords is not None:
            title = [f"Key matches for chords: {', '.join([c.name for c in chords])} with notes: {NoteList(unique_notes)}"]
            if upweight_first:
                title.append(f'(upweighted first chord: {chords[0].name})')
            if upweight_last:
                title.append(f'(upweighted last chord: {chords[-1].name})')
            if upweight_pentatonics:
                title.append('(and upweighted pentatonics)')
            # title.append(f'\n With note weights: {note_counts}')
        elif notes is not None:
            title = [f"Key matches for notes: {', '.join([n.name for n in notes])}"]

        title = ' '.join(title)
        print(title)

        # we'll figure out how long we need to make each 'column' by iterating through cands:
        key_name_parts = []
        note_list_parts = []
        for cand in sorted_cands:
            # break key string up for nice viewing:
            key_name_parts.append(cand.name)
            note_list_parts.append(str(cand.notes))
        longest_name_len = max([len(str(s)) for s in (key_name_parts + ['  key name'])])+3
        longest_notes_len = max([len(str(s)) for s in (note_list_parts + ['    notes'])])+3

        left_header =f"{'  key name':{longest_name_len}} {'    notes':{longest_notes_len}}"
        score_parts = ['precision', 'lklihood', 'recall', 'consonance']
        hspace = 8
        right_header = ' '.join([f'{h:{hspace}}' for h in score_parts])
        out_list = [left_header + right_header]


        for i, cand in enumerate(sorted_cands):
            scores = candidates[cand]
            prec, lik, rec, cons = list(scores.values())
            name_str, notes_str = key_name_parts[i], note_list_parts[i]

            descriptor = f'{name_str:{longest_name_len}} {notes_str:{longest_notes_len}}'
            scores = f' {str(prec):{hspace}} {str(lik):{hspace}}  {str(rec):{hspace}}  {cons:.03f}'
            out_list.append(descriptor + scores)
        print('\n'.join(out_list))
    if return_matches:
        return {c: candidates[c] for c in sorted_cands}


def most_likely_key(*args, **kwargs):
    """wrapper around matching_keys that simply returns the single most likely Key as an object"""
    matches = matching_keys(*args, display=False, return_matches=True, **kwargs)
    if len(matches) == 0:
        # re run with no minimums
        matches = matching_keys(*args, display=False, min_recall=0, min_precision=0, min_likelihood=0, return_matches=True, **kwargs)
    # return top match:
    return list(matches.keys())[0]
