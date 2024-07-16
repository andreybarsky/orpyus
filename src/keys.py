from . import notes, scales, parsing, _settings
from .parsing import fl, sh, nat, dfl, dsh
from .intervals import Interval, IntervalList
from .notes import Note, NoteList, chromatic_notes
from .scales import Scale, ScaleFactors, ScaleDegree, ScaleChord, common_scales, scale_extensions, scale_contractions
from .chords import Chord, AbstractChord, ChordList
from .util import ModDict, check_all, precision_recall, reverse_dict, unpack_and_reverse_dict, log

from collections import Counter
from functools import cached_property
from pdb import set_trace

class Key(Scale):
    """a Scale that is also rooted on a tonic, and therefore associated with a set of notes"""

    def __init__(self, name=None, intervals=None, factors=None,
                    alterations=None, chromatic_intervals=None,
                    notes=None, chromatic_notes=None, tonic=None,
                    mode=1):
        """a Key can be Initialised in one of three ways:

        1. from 'notes' arg, as a list or string of Notes or Note-like objects,
            from which we parse the tonic and intervals

        2. from 'name' arg, when as a proper Key name (like "C#" or "Bb harmonic minor" or "Gbb lydian b5"),
            in which case we extract the tonic note from the string and initialise the rest as with Scale class.

        3. from 'tonic' arg, as a Note or string that casts to Note,
            in combination with any other args that would initialise a valid Scale object.
            i.e. 'intervals' or 'factors', or a valid scale name for 'name'."""

        name, intervals, factors, notes, tonic = self._reparse_key_args(name, intervals, factors, notes, tonic)

        # if notes have been provided, parse them into tonic and intervals:
        if notes is not None:
            # ignore intervals/factors/root inputs
            assert tonic is None and intervals is None and name is None
            note_list = NoteList(notes)
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
        del self.scale # this is the only part of scale init we don't need; gets overwritten by the Key.scale property-method

        # set Key-specific attributes: notes, degree_notes, etc.

        self.notes = NoteList([self.tonic + i for i in self.intervals])
        self.chromatic_notes = NoteList([self.tonic + iv for iv in self.chromatic_intervals])

        self._set_sharp_preference() # sets tonic and notes attrs to have appropriate spelling
        self._set_note_mappings() # sets degree_notes, factor_notes, etc. and their inverses
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
            tonic = Note.from_cache(tonic)
        elif tonic is not None:
            tonic = Note.from_cache(tonic)
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

        self.prefer_sharps = prefer_sharps

        if self.tonic.prefer_sharps != prefer_sharps:
            # replace the tonic if it has a different sharp preference.
            # n.b. we reinitialise note objects (to avoid caching interactions)
            self.tonic = Note.from_cache(position=self.tonic.position, prefer_sharps=prefer_sharps)

        if self.is_natural() or self.is_natural_pentatonic():
            # no complex computation needed for non-natural scales
            # just assign same sharp preference as tonic to every note.
            self.notes = NoteList([Note.from_cache(position=n.position, prefer_sharps=prefer_sharps) if n.prefer_sharps!=prefer_sharps  else n  for n in self.notes ])

        else:
            # compute flat/sharp preference of individual notes
            # by assigning one note to each natural note name

            tonic_nat = self.tonic.chroma[0] # one of the few cases where note sharp preference matters
            next_nat = parsing.next_natural_note[tonic_nat]
            new_notes = [self.tonic]

            which_chromatic = self.which_intervals_chromatic()

            for i,n in enumerate(self.notes[1:]):
                if not which_chromatic[i]:
                    # degree note
                    if n.name == next_nat:
                        # this is a natural note, so its sharp preference shouldn't matter,
                        # but set it to the tonic's anyway for consistency
                        n = Note.from_cache(position=n.position, prefer_sharps=prefer_sharps)
                    else:
                        # which accidental would make this note's chroma include the next natural note?
                        if n.flat_name[0] == next_nat:
                            n = Note.from_cache(position=n.position, prefer_sharps=False)
                        elif n.sharp_name[0] == next_nat:
                            n = Note.from_cache(position=n.position, prefer_sharps=True)
                        else:
                            # this note needs to be a double sharp or double flat or something
                            log(f'Found a possible case for a double-sharp or double-flat: note {i+2} ({n}) of {self}')
                            log(f'  because neither its sharp name ({n.sharp_name}) or its flat name ({n.flat_name}) starts with the desired natural note: {next_nat}')
                            # fall back on same as tonic:
                            n = Note.from_cache(position=n.position, prefer_sharps=prefer_sharps)
                    new_notes.append(n)
                    next_nat = parsing.next_natural_note[next_nat]
                else:
                    # chromatic note, just append without changing
                    new_notes.append(n)
            # combine with existing chromatic notes (which are not changed)
            self.notes = NoteList(new_notes)

    def _set_note_mappings(self):
        """based on self.notes and self.chromatic_notes,
        defines all the note mappings inside this Key object"""

        which_chromatic = self.which_intervals_chromatic()
        non_chromatic_notes = [n for i,n in enumerate(self.notes) if not which_chromatic[i]]

        self.degree_notes = ModDict({d: n for d,n in zip(self.degrees, non_chromatic_notes)}, index=1, raise_values=False)
        self.factor_notes = ModDict({f: n for f,n in zip(self.factors, non_chromatic_notes)}, index=1, raise_values=False)
        self.interval_notes = ModDict({iv:n for iv,n in zip(self.intervals, self.notes)}, index=0, max_key=11, raise_values=False)

        self.note_degrees = reverse_dict(self.degree_notes)
        self.note_factors = reverse_dict(self.factor_notes)
        self.note_intervals = reverse_dict(self.interval_notes)

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
    def fractional_degree_notes(self):
        """as Scale.fractional_degree_intervals, but maps to the notes of this key"""
        frac_deg_notes = {d: Note.from_cache(self.tonic+iv, prefer_sharps=self.tonic.prefer_sharps) for d,iv in self.fractional_degree_intervals.items()}
        return ModDict(frac_deg_notes, index=1, max_key=7, raise_values=False)

    @cached_property
    def fractional_note_degrees(self):
        return reverse_dict(self.fractional_degree_notes)

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

    ### convenience accessors for important tones: (analogous to self.tonic)
    @property
    def dominant(self):
        return self.factor_notes[5]
    @property
    def subdominant(self):
        return self.factor_notes[4]
    @property
    def leading_tone(self):
        return self.factor_notes[7]

    def get_chord(self, degree, order=3, linked=True):
        """overwrites Scale.get_chord, returns a Chord object instead of an AbstractChord.
        if linked, returns a KeyChord instead of a ScaleChord."""
        abstract_chord = Scale.get_chord(self, degree, order)
        root_interval = self.get_interval_from_degree(degree)
        root_note = self.tonic + root_interval
        if linked:
            chord_obj = KeyChord(factors=abstract_chord.factors, inversion=abstract_chord.inversion, root=root_note, key=self, degree=degree)
        else:
            chord_obj = abstract_chord.on_bass(root_note)
        # initialised chords inherit this key's sharp preference:
        chord_obj._set_sharp_preference(self.prefer_sharps)
        return chord_obj

    def get_tertian_chord(self, degree, order=3, linked=True, prefer_chromatic=False):
        """overwrites Scale.get_tertian_chord, returns a Chord object instead of an AbstractChord"""
        abstract_chord = Scale.get_tertian_chord(self, degree, order, linked=linked, prefer_chromatic=prefer_chromatic)
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
            from .display import chord_table
            title = f"Valid chords built on degree {degree} of {self}"
            print(title)
            chord_table(chords,
                        columns=['chord', 'notes', 'degrees', 'tert', 'likl', 'cons'],
                        parent_scale=self, parent_degree=degree, margin=' | ', **kwargs)
        else:
            return chords # already in sorted order by valid_chords_on method

    def clockwise(self, steps=1):
        """fetch the next key from clockwise around the circle of fifths,
        or if steps>1, go clockwise that many steps"""
        return Key(factors=self.factors, tonic=self.tonic + (7*steps))

    def counterclockwise(self, steps=1):
        return self.clockwise(-steps)
    anticlockwise = counterclockwise # convenience alias

    def mode(self, N):
        """as Scale.mode, but returns a Key with transposed tonics too.
        so that the modes of C major are D dorian, E phrygian, etc."""
        # mod the rotation value into our factor range:
        N = ((N-1) % self.order) + 1
        scale_mode = Scale.mode(self, N)
        mode_tonic = self.degree_notes[N]
        return scale_mode.on_tonic(mode_tonic)

    def get_modes(self):
        """the modes of a Key are the relative keys that share its notes but start on a different tonic
        i.e. modes of C major are D dorian, E phrygian, etc."""
        return [self.mode(n) for n in range(2,self.order+1)]

    @property
    def modes(self):
        return self.get_modes()

    def subscale(self, keep=None, omit=None):
        """as Scale.subscale, but returns a Key instead (a subkey?)"""
        sub = Scale.subscale(self, keep=keep, omit=omit)
        return sub.on_tonic(self.tonic)

    def get_pentatonic(self):
        """as Scale.pentatonic, but returns a Key on the same tonic"""
        # check if a pentatonic scale is defined under this scale's canonical name:
        naive_pentatonic_name = f'{self.scale_name} pentatonic'
        if naive_pentatonic_name in scales.all_scale_name_factors:
            return Scale(naive_pentatonic_name).on_tonic(self.tonic)
        else:
            # this will already be a Key due to inheritance of compute_pentatonics:
            return self.compute_best_pentatonic(preserve_character=True)

    def compute_pentatonics(self, *args, display=True, **kwargs):
        """as Scale.compute_pentatonics, but returns Keys instead of Scales.
            tries to find pentatonic subkeys of this key that preserve scale character
            while minimising dissonant pairwise intervals"""
        sorted_pentatonic_scales = Scale.compute_pentatonics(self, *args, display=False, **kwargs)
        if display:
            from .display import DataFrame
            title = f'Computed pentatonic scales of {self} (in {self.tonic.chroma})'
            pres_str = f'\n    while preserving scale character: {",".join(character.as_factors)}' if preserve_character else ''
            print(title + pres_str)

            df = DataFrame(['Subscale', 'Notes', 'Factors',  'Omit', 'Cons.'])
            for cand in sorted_pentatonic_scales:
                cand_iv_key = (cand.intervals, cand.chromatic_intervals if len(cand.chromatic_intervals) > 0 else None)
                scale_name = cand.assigned_name if cand_iv_key not in scales.canonical_scale_interval_names else scales.canonical_scale_interval_names[cand_iv_key]
                name = f'{self.tonic.chroma}{scale_name}'
                pent_notes = str(cand.notes)[1:-1]
                factors_str = str(cand.factors)[1:-1]
                omitted = [str(f) for f in self.factors if f not in cand.factors]
                # kept = [str(f) for f in cand.factors if f in self.factors]
                df.append([name, pent_notes, factors_str, ','.join(omitted), round(cand.consonance,3)])
            df.show(margin=' | ', **kwargs)
        else:
            sorted_pentatonic_keys = [s.on_tonic(self.tonic) for s in sorted_pentatonic_scales]
            return {x: round(x.consonance,3) for x in sorted_pentatonic_keys}

    @property
    def relative(self):
        """returns this Key's parallel scale on the tonic that forces it to have the same notes"""
        if self.has_parallel():
            parallel_scale_name = scales.parallel_scale_names[self.scale_name]
            # need to figure out where to place the tonic
            # so we want to find which mode of this scale is our parallel scale
            # first, which of the two is the base scale:
            if self.scale_name in scales.base_scale_names:
                self_is_base = True
                base_scale_name = self.scale_name
                mode_name = parallel_scale_name
            else:
                self_is_base = False
                base_scale_name = parallel_scale_name
                mode_name = self.scale_name
            # list the inverted mode names:
            mode_idx_names = scales.base_scale_mode_names[base_scale_name]
            mode_name_idxs = unpack_and_reverse_dict(mode_idx_names)
            mode_idx_of_base = mode_name_idxs[mode_name]
            # if the parallel is the base scale, we need to invert the mode idx:
            if not self_is_base:
                mode_idx_of_base = (self.order+2) - mode_idx_of_base
            relative_tonic = self.degree_notes[mode_idx_of_base]
            return Scale(parallel_scale_name).on_tonic(relative_tonic)

        else:
            raise Exception(f'{self.name} has no defined relative key')

    @property
    def parallel(self):
        if self.has_parallel():
            return Scale(scales.parallel_scale_names[self.scale_name]).on_tonic(self.tonic)
        else:
            raise Exception(f'Parallel major/minor not defined for {self.name}')

    @property
    def extension(self):
        """natural scales have extensions into harmonic/melodic chromatic notes,
        this property fetches the extended scale if it exists"""
        if self.scale in scale_extensions:
            return scale_extensions[self.scale].on_tonic(self.tonic)
        else:
            raise Exception(f'No scale extension defined for: {self.scale.name}')

    @property
    def extensions(self):
        """return one or both extensions of this scale"""
        if self.scale.extension in scale_extensions:
            return [self.extension, self.extension.extension]
        elif self.scale in scale_extensions:
            return [self.extension]
        else:
            return []

    @property
    def contraction(self):
        if self.scale in scale_contractions:
            return scale_contractions[self.scale].on_tonic(self.tonic)
        else:
            raise Exception(f'No scale extension defined for: {self.scale.name}')

    def get_closely_related_keys(self, modes=False):
        """a natural key's closely related keys are those directly adjacent on the
        circle of fifths, as well as its relative (and the relatives of its adjacents)"""
        if self.is_diatonic() and self.has_parallel():
            relative = [self.relative]
            adjacent_keys = [self.clockwise(), self.counterclockwise()]
            adjacent_relatives = [k.relative for k in adjacent_keys]

            return relative + adjacent_keys + adjacent_relatives
        elif self.has_parallel():
            return [self.relative]
    @property
    def closely_related_keys(self):
        return self.get_closely_related_keys()

    def common_notes(self, other_key):
        if not isinstance(other_key, Key):
            other_key = Key(other_key)
        return NoteList([n for n in self.notes if n in self and n in other_key])

    def common_chords(self, other_key):
        if not isinstance(other_key, Key):
            other_key = Key(other_key)
        unkeyed_chords = [ch.unkey() for ch in self.chords()]
        return ChordList([ch for ch in unkeyed_chords if ch in self and ch in other_key])

    def __invert__(self):
        """ ~ operator returns the relative major/minor of a key"""
        return self.relative

    def __neg__(self):
        """ - operator returns the parallel major/minor of a key"""
        return self.parallel

    def _get_arbitrary_degree_note(self, deg):
        """retrieves the note for any degree relative to this key,
        whether or not that degree is in this key"""
        if deg in self.degree_notes:
            return self.degree_notes[deg]
        else:
            return self.fractional_degree_notes[deg]

    def _get_arbitrary_note_degree(self, nt):
        """retrieves the degree for any note in this key,
        whether or not that degree is in this key"""
        if nt in self.note_degrees:
            return self.note_degrees[nt]
        else:
            return self.fractional_note_degrees[nt]

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
        elif type(item) in (Chord, KeyChord):
            # chord is 'in' this Key if all of its notes are:
            for note in item.notes:
                if note not in self.notes:
                    return False
            return True

        elif isinstance(item, AbstractChord):
            if not isinstance(item, ScaleChord):
                raise TypeError("A Scale/Key does not know if it contains a given AbstractChord without further clarification")
            # ScaleChords exist on a specific degree of their scale/key,
            # so we can tell if this scale contains that chord on that degree:
            abs_chord = item.abstract()
            return self.contains_degree_chord(item.scale_degree, abs_chord)
        elif isinstance(item, (list, tuple)):
            # check if each individual item in an iterable is contained here:
            for subitem in item:
                if subitem not in self:
                    return False
            return True

        else:
            raise TypeError(f'Key.__contains__ not defined for items of type: {type(item)}')

    def extended_contains(self, chord):
        """returns True if a given chord is in this scale or any of its extensions"""
        if not isinstance(chord, Chord):
            chord = Chord(chord)

        if chord in self:
            return True
        for ext_key in self.extensions:
            if chord in ext_key:
                return True
        return False

    def __add__(self, other):
        """Addition defined over Keys:
        1. Addition with interval (or int) is transposition onto a new tonic."""
        if isinstance(other, (Interval, int)):
            new_tonic = self.tonic + other
            return Key(tonic=new_tonic, factors=self.factors)
        else:
            raise TypeError(f'Cannot add Key with {type(other)}')

    def __sub__(self, other):
        """Subtraction over Keys:
        1. Subtraction with interval (or int) transposes onto a new tonic.
        2. Subtraction with Key returns the circle-of-fifths distance
            to the other key. major-minor swap counts as 0.5. Only for natural keys."""
        if isinstance(other, (Interval, int)):
            new_tonic = self.tonic - other
            return Key(tonic=new_tonic, factors=self.factors)
        elif isinstance(other, Key):
            if self.is_natural() and other.is_natural():
                if other.quality != self.quality:
                    # switch to relative major/minor and add a half-step
                    other = other.relative
                    parallel_adjustment = 0.5
                else:
                    parallel_adjustment = 0

                # distance along circle of fifths
                key_distance = 0.
                tonic_distance = self.tonic - other.tonic
                while tonic_distance != 0:
                    tonic_distance = (tonic_distance - 7) % 12
                    key_distance += 1.
                if key_distance > 6:
                    key_distance = -12 + key_distance # counterclockwise distance is negative
                    parallel_adjustment *= -1
                return key_distance + parallel_adjustment
            else:
                raise Exception(f'Subtraction between Keys is only defined for natural keys')
        else:
            raise TypeError(f'Cannot subtract Key with {type(other)}')


    def __eq__(self, other):
        if isinstance(other, Key):
            return self.notes == other.notes
        else:
            raise TypeError(f'__eq__ not defined between Key and {type(other)}')

    def __hash__(self):
        """Keys hash by their Factors and their tonic"""
        return hash((self.factors, self.tonic))

    def show(self, tuning='EADGBE', **kwargs):
        """just a wrapper around the Guitar.show method, which is generic to most musical classes,
        so this method is also inherited by all Scale subclasses"""
        from .guitar import Guitar
        Guitar(tuning).show_key(self, **kwargs)
    on_guitar = show # convenience alias

    @property
    def fretboard(self):
        return self.show()
    diagram = fretboard

    def play(self, *args, **kwargs):
        # plays the notes in this key (we also add an octave over root on top for resolution)
        # played_notes = NoteList([n for n in self.notes] + [self.tonic])
        # played_notes.play(*args, **kwargs)
        Scale.play(self, *args, on=f'{self.tonic.name}3', **kwargs)

    def progression(self, *degrees, order=3):
        """accepts a sequence of (integer) degrees,
            and produces a ChordProgression in this key rooted on those degrees.
        alternatively, accepts anything that would initialise a ChordList,
            and produces a ChordProgression of those chords in this key."""
        from .progressions import Progression, ChordProgression
        if len(degrees) == 1: # unpack single list arg
            degrees = degrees[0]
        # use list of integers:
        if check_all(degrees, 'isinstance', int):
            # use superclass progression method and place on tonic:
            prog = self.scale.progression(*degrees, order=order)
            return prog.on_tonic(self.tonic)
        else:
            # assume we have been given an input that resembles a chordlist
            if not isinstance(degrees, ChordList):
                degrees = ChordList(degrees)
            return ChordProgression(degrees, key=self)

    #### display methods:

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
    def __init__(self, *args, key, degree=None, factor=None, degree_on_bass=True, **kwargs):

        if not isinstance(key, Key):
            key = Key(key)
        self.key = key
        # KeyChord inherits its key's sharp preference unless explicitly overwritten:
        if 'prefer_sharps' not in kwargs:
            kwargs['prefer_sharps'] = self.key.prefer_sharps        # and then as ScaleChord: (without the associated abs_chord init)

        # initialise as Chord:
        Chord.__init__(self, *args, **kwargs)

        # if True, inverted chords are treated as having
        # the scale degree of their bass note, instead of
        # their 'proper' root note:
        self.degree_on_bass = degree_on_bass



        if degree is None and factor is None:
            # auto-infer degree from this chord's root (or bass)
            deg_note = self.root if not degree_on_bass else self.bass
            if deg_note in key.note_degrees:
                degree = key.note_degrees[deg_note]
            else:
                degree = key.fractional_note_degrees[deg_note]


        ScaleChord.__init__(self, scale=self.key.scale,
                            degree=degree, factor=factor, prefer_sharps=self.prefer_sharps,
                            _init_abs=False)

        # flag whether this chord belongs in the key/scale specified:
        self.in_key = self in self.key



    def to_key(self, key):
        """transposes this KeyChord to another with a different root,
        but the same degree, in another Key"""
        if not isinstance(key, Key):
            key = Key(key)
        new_root = key.degree_notes[self.scale_degree] if self.scale_degree in key.degree_notes else key.fractional_degree_notes[self.scale_degree]
        return KeyChord(root=new_root, factors=self.factors, inversion=self.inversion, key=key, degree=self.scale_degree)
        # return key.chord(degree=self.scale_degree, linked=True)

    def abstract(self):
        """return the ScaleChord that this KeyChord is associated with"""
        return ScaleChord(factors=self.factors, inversion=self.inversion, scale=self.key.scale, degree=self.scale_degree)

    def unkey(self):
        """returns the Chord that this KeyChord is associated with"""
        return Chord(factors=self.factors, inversion=self.inversion, root=self.root)

    def __str__(self):
        return self.name


    @property
    def mod_numeral(self):
        return self.get_numeral(modifiers=True, marks=False, diacritics=False)

    @property
    def name(self):
        # mod_numeral = self.get_numeral(modifiers=True, marks=False, diacritics=False)
        return f'{Chord.get_short_name(self)} ({self.mod_numeral} of {self.key._marker}{self.key.name})'

    @property
    def short_name(self):
        # mod_numeral = self.get_numeral(modifiers=True, marks=False, diacritics=False)
        return f'{Chord.get_short_name(self)} ({self.mod_numeral})'

    @property
    def chord_name(self):
        "the name of the chord itself, without the numeral"
        return f'{Chord.get_short_name(self)}'

    @property
    def compact_name(self):
        return self.short_name
        # ### compact repr for KeyChord class
        # mod_numeral = self.get_numeral(modifiers=True, marks=False, diacritics=False)
        # return f'{self._marker}{self.short_name} ({mod_numeral})'

    def _register(self):
        pass # KeyChords are not registered

    def __repr__(self):
        # in_str = 'not ' if not self.in_scale else ''
        # mod_numeral = self.get_numeral(modifiers=True, marks=False, diacritics=False)
        # dotted notes str as in Chord.__repr__:
        lb, rb = NoteList._brackets
        notes_str = self._dotted_notes(markers=True)
        return f'{self._marker}{self.name} {lb}{notes_str}{rb}'
        # return f'{self._marker}{self.get_numeral(modifiers=True, marks=False, diacritics=False)}'


    # overwrites Chord.from_cache:
    def from_cache(self, *args, **kwargs):
        raise TypeError('KeyChords are not cached')



# natural notes in order of which are flattened/sharpened in a key signature:
# (also implicitly contains circle-of-fifths ordering)
flat_order = ['B', 'E', 'A', 'D', 'G', 'C', 'F']
sharp_order = ['F', 'C', 'G', 'D', 'A', 'E', 'B']

relative_co5_distances = IntervalList([0, 5, 2, 3, 4, 1, 6, 1, 4, 3, 2, 5])
# this list looks funny, but it's the circle-of-fifths distance for each key with tonic
# N+i, with respect to the key that has tonic N, in semitones.
# e.g. co5_distance between E and D is based on the interval between E and D,
# i.e. Note('E') - Note('D'), which is 2, or Note('D') - Note('E'), which is 10
# so the co5_distance is relative_co5_distances[2] (or [10]), which either way is 2.
# this works for any diatonic key, and is just a property of how the notes are arranged,
# which is why it's hardcoded instead of being computed at init


def matching_diatonic_keys(chords=None, notes=None,
        min_precision=0, min_recall=0.9, # minimum accuracy stats to return a match
        weight_counts=True,  # if True, place more weight on repeated notes
        chord_factor_weights = {1: 1.5,  # if using chords, how much weight to place on each chord factor.
                                3: 1.2,  # by default, chord tonics and thirds are worth more,
                                5: 0.8}, # while fifths are worth less (because they are often implicit)
        scale_degree_weights = {1: 2,    # how much weight to place on each degree of candidate scales.
                                3: 1.5,  # by default, tonics, thirds, and fifths
                                5: 1.5},
        scale_chord_weights = {1: 3, 4: 2, 5: 2},
        verbose=False):
    ... # TBC


def matching_keys(chords=None, notes=None, tonic=None, tonic_guess=None, assume_tonic=False,
                  exact=False, exhaustive=None, modes=False, scale_lengths=None,
                  min_precision=0, min_recall=0.9,
                  min_likelihood=0.7, max_likelihood=1.0, max_rarity=None, min_rarity=None,
                  min_consonance=0, max_consonance=1.0,
                  chord_factor_weights = {1: 1.1}, weight_counts=True,
                  scale_factor_weights = {1: 2, 3: 1.5, 5: 1.5},
                  scale_chord_weights = {1: 3, 4: 2, 5: 2},
                  # (by default, upweight roots and thirds, downweight fifths)
                  sort_order=['recall', 'likelihood', 'consonance', 'precision', 'length'],
                  candidate_scales=scales.searchable_heptatonics,
                       # extended_searchable_heptatonics display is currently broken (shows 8th and 9th degrees)
                  display=True, max_results=None, verbose=log.verbose, **kwargs):
    """Accepts either a list of chords or a list of notes.
    exact: if True, only returns matches with perfect precision.
    exhaustive: if True, search all possible key tonics.
        if False, search only key tonics corresponding to input chord roots. (or input notes)
        if None, becomes set by default to True for notelists and False for chordlists.
    tonic: default None, but can be set to a note (or list of notes) to restrict searches
        to keys only with that tonic. (overrides 'exhaustive')
    tonic_guess: default None, but if provided, will prioritise keys with the specified tonic,
        unless none are found at all, in which case ignore the guess.
        incompatible with 'tonic' arg above - the difference is that 'tonic' will
        return an empty list if no tonic-matching keys are found.
    assume_tonic: if True, will take the tonic to be the first chord's root, or the first note
        in the supplied notelist.
        if False, makes no assumptions about key tonics.
        if None (default), and no other tonic args are provided,switches depending on
            input type: becomes True for notelists, False for chordlists.
        this cannot be True if either 'tonic' or 'tonic_guess' are set.
    natural_only: if True, only scores natural major and minor keys.
    modes: if True, returns all named modes of all matches.
        if False, only returns base keys and their relative keys.
    min_[precision/recall/consonance/likelihood]: minimum scores that a key must meet
        to count as 'matching'
    max_[consonance/likelihood]: scores above which keys will NOT be searched.
        (does not seem useful, but is more efficient when doing multiple-wave searching,
        since these constraints are applied before instantiating and looping over key objects)
    max_rarity, min_rarity: inverse of min/max_likelihood. default None, but overrides min/max_likelihood if set.
    weight_counts: if True, weights precision and recall by the relative frequency
        of each note in the input list.
    chord_factor_weights: a dict that determines how much to weight each input chord factor by.
        (only used if function is called with chords, not notes)
    scale_factor_weights: as above, but determines how much to weight candidate scale degrees.
    sort_order: list of strings that must strictly include all 5 default values, but in any order.
        controls the order in which the function output gets sorted.
    display: if True, prints a dataframe of the results.
        if False, returns a dict of results as {keys: scores} instead."""

    # quietly accept a notelist as first argument:
    if isinstance(chords, NoteList):
        notes = chords
        chords = None

    if exhaustive is None:
        # default behaviour: set to True for notes and False for chords
        exhaustive = (notes is not None)

    if max_rarity is not None:
        # translate rarity integer to likelihood score
        min_likelihood = Scale.rarity_to_likelihood(max_rarity)
    if min_rarity is not None:
        max_likelihood = Scale.rarity_to_likelihood(min_rarity)


    # parse input into counter-dict of notes frequencies:
    if chords is not None:
        assert notes is None
        if not isinstance(chords, ChordList):
            chords = ChordList(chords)
        # compute weighted notes wrt provided factor weights (and ignoring frequency counts if asked)
        input_note_weights = chords.weighted_note_counts(chord_factor_weights, ignore_counts=(not weight_counts))
    elif notes is not None:
        if not isinstance(notes, NoteList):
            notes = NoteList(notes)
        input_note_weights = Counter(notes)

    # print(f' Input note weights: {input_note_weights}')

    # list of notes to match:
    input_notes = list(input_note_weights.keys())


    #### LIST OF SCALES TO SEARCH
    # loop over all common base scales (and, by extension, their modes if desired)
    # provided they exceed minimum scale scores:
    if candidate_scales is None:
        candidate_scales = [s for s in scales.common_base_scales if (max_likelihood >= s.likelihood >= min_likelihood) and (max_consonance >= s.consonance >= min_consonance)]
        if not modes:
            # only include modes if they are common:
            candidate_scales.extend([m for m in scales.common_modes  if (max_likelihood >= m.likelihood >= min_likelihood) and (max_consonance >= m.consonance >= min_consonance)])

    log(f'Searching {len(candidate_scales)} possible scales: {", ".join([s.name for s in candidate_scales])}')

    #### SCALE LENGTH RESTRICTION
    # restrict search to scales only of certain lengths
    if scale_lengths is not None:
        if isinstance(scale_lengths, int): # catch single int arg
            scale_lengths = [scale_lengths]
        scales_to_search = [s for s in scales_to_search if len(s) in scale_lengths]
        log(f'Restricted to {len(scales_to_search)} of length/s {scale_lengths}: {", ".join([s.name for s in scales_to_search])}')

    #### TONIC RESTRICTION
    if assume_tonic is None and tonic is None and tonic_guess is None:
        # assume tonic by default if NoteList is given as input and no other tonic args are set
        if notes is not None:
            assume_tonic = True

    # set assumed tonic, if we are asked to assume one:
    if tonic is None and assume_tonic is True:
        # assume the first note is the tonic:
        if chords is not None:
            tonic = chords[0].root
        elif notes is not None:
            tonic = notes[0]
        assume_tonic = None

    if tonic is not None:
        assert assume_tonic is None, f"Incompatible 'tonic' and 'assume_tonic' args provided to function matching_keys"
        assert tonic_guess is None, f"Incompatible 'tonic' and 'tonic_guess' args provided to function matching_keys"
        # set explicit tonics only
        possible_tonics = NoteList(tonic).unique()

        # if we want modes, this also requires we modify scales_to_search
        # as e.g. D phrygian dominant will never appear if the possible
        # tonics include only D, because that is a mode of harmonic minor,
        # and we would search harmonic minor only on D (which would only
        # account for the fit of A phrygian dominant)

        if modes:
            # so here, we explicitly add the modes of desired base scales to
            # the search list, which is a bit combinatorially explosive but
            # balanced out by a restricted set of tonics to search
            uncommon_modes = []
            for s in scales_to_search:
                scale_modes = [m for m in s.modes if m not in common_scales]
                uncommon_modes.extend(scale_modes)

    elif exhaustive:
        # search all specified scales on all possible tonics
        possible_tonics = chromatic_notes
    else:
        if chords is not None:
            # search only the tonics that occur as chord roots:
            possible_tonics = NoteList([ch.root for ch in chords]).unique()
        elif notes is not None:
            # search tonics corresponding to input notes
            possible_tonics = notes.unique()

    log(f'Searching key tonics: {possible_tonics}')

    ###############################
    ###### main search loop: ######
    shortlist_scores = {}
    for scale in candidate_scales:
        scale_name = scale.name
        scale_intervals, chrom_intervals = scales.canonical_scale_name_intervals[scale_name]
        for key_tonic in possible_tonics:
            candidate_key_notes = [key_tonic + iv for iv in scale_intervals] # equiv. to degree_notes (from 0, not 1)

            ### determine weights for the notes in this key:
            scale_scale = len(chords)**0.5 if chords is not None else 1 # i.e. how much to weight the scale weights relative to the chord weights
            key_weights = Counter({n: 1*scale_scale for n in candidate_key_notes})
            # scale_degree_weights = [scale.degree_factors[d+1] for d,n in enumerate(candidate_key_notes)
            factors = [scale.degree_factors[d+1] for d in range(len(candidate_key_notes))]

            # update note weightings by scale factors:
            scale_note_weights = {n:scale_factor_weights[factors[i]] if factors[i] in scale_factor_weights  else 1  for i,n in enumerate(candidate_key_notes)}
            # and by scale chord notes:
            for root_degree, degree_weight in scale_chord_weights.items():
                root_chord = scale.chord(root_degree, order=3)
                chord_notes = [key_tonic + iv for iv in root_chord.intervals]
                chord_note_weights = {n: degree_weight for n in chord_notes}
                scale_note_weights.update(chord_note_weights)

            for n,w in scale_note_weights.items():
                key_weights[n] = round(key_weights[n] * w, 2)
            # now add input weights on top:
            # print(f' Key weights for candidate: {key_tonic.name} {scale_name}')
            # print(key_weights)

            key_weights.update(input_note_weights)
            # print(f'  Updated by input note weights to:')
            # print('  ' + str(key_weights))

            candidate_chrom_notes = [key_tonic + iv for iv in chrom_intervals] if chrom_intervals is not None else []
            candidate_notes = candidate_key_notes + candidate_chrom_notes
            ### main matching call:
            scores = precision_recall(input_notes, candidate_notes, weights=key_weights, return_unweighted_scores=True)

            # add a candidate to shortlist if it beats the minimum prec/rec requirements:
            if scores['precision'] >= min_precision and scores['recall'] >= min_recall:
                log(f'Found shortlist match ({key_tonic.chroma} {scale_name}) with precision {scores["precision"]:.2f} and recall {scores["recall"]:.2f}')
                candidate = Scale(scale_name).on_tonic(key_tonic)
                # add to shortlist dict:
                shortlist_scores[candidate] = scores

    if min_likelihood > 0 or min_consonance > 0:
        # filter out keys that do not meet minimums:
        filtered_scores = {key:scores for key,scores in shortlist_scores.items() if ((key.consonance >= min_consonance) and (key.likelihood >= min_likelihood))}
    else:
        # no filtering needed
        filtered_scores = shortlist_scores

    if modes is True and tonic is None:
        # add all (named) parallel modes of all matching keys
        # (though this behaviour is not necessary if a strict tonic requirement was set)
        mode_scores = {}
        for key, scores in filtered_scores.items():
            key_modes = [m for m in key.modes[1:] if m.factors in scales.canonical_scale_factor_names]
            # modes have the same prec/rec scores as their base keys:
            # (but different likelihoods and consonances)
            mode_scores.update({m:scores for m in key_modes})
        filtered_mode_scores = {key:scores for key,scores in mode_scores.items() if ((key.consonance >= min_consonance) and (key.likelihood >= min_likelihood))}
        filtered_scores.update(mode_scores)

    else:
        pass # modes are only included if they are common
        # relative_scores = {}
        # # just add relative modes (i.e. minor to major or vice versa) where relevant
        # for key, scores in filtered_scores.items():
        #     if key.is_natural() and key.has_parallel():
        #         if key.relative.likelihood >= min_likelihood and key.relative.consonance >= min_consonance:
        #             relative_scores[key.relative] = scores
        # filtered_scores.update(relative_scores)

    # filter by tonic guess if needed:
    if tonic_guess is not None:
        ### filter list to only include keys of that tonic, unless none exist
        if not isinstance(tonic_guess, Note):
            tonic_guess = Note.from_cache(tonic_guess)

    # sort matches according to desired order:
    sort_funcs = {'length': lambda x: len(x),
                 'precision': lambda x: -round(filtered_scores[x]['precision'],2),
                 'recall': lambda x: -round(filtered_scores[x]['recall'],2),
                 'likelihood': lambda x: -x.likelihood,
                 'consonance': lambda x: -x.consonance}
                 # note we round prec and rec to 2d.p. to allow 'soft' tiebreaks by likl/cons
    ordered_funcs = [sort_funcs[s] for s in sort_order]
    master_sort_func = lambda x: tuple([f(x) for f in ordered_funcs])
    sorted_keys = sorted(filtered_scores.keys(), key=master_sort_func)
    sorted_scores = {k: filtered_scores[k] for k in sorted_keys}

    if not display:
        return sorted_scores
    else:
        from .display import DataFrame, chord_table

        # title:
        if chords is not None:
            print(f'Matching keys for chords: {chords}')
            if verbose:
                chord_table(chords, ['chord', 'border', 'null', 'notes'])
            print('')
        elif notes is not None:
            print(f'Matching keys for notes: {notes}')
        if verbose:
            note_weights_str = ',  '.join([f'{n.name}: {w:.1f}' for n,w in input_note_weights.items()])
            print(f'Note weights:\n  {note_weights_str}')

        nlb, nrb = _settings.BRACKETS['NoteList']

        # show degrees as columns
        longest_scale_len = max([len(s) for s in sorted_scores]) if len(sorted_scores) > 0 else 7
        scale_degrees = [ScaleDegree(n) for n in range(1, longest_scale_len+1)]
        # degs_str = '  '.join([f'{str(d)}' for d in scale_degrees])
        ## degs_str removed because it plays havoc with extended scales
        degs_str = 'Notes'

        df = DataFrame(['  Key', '', degs_str, '', 'Miss.', 'Rec.', 'Prec.', 'Likl.', 'Cons.'])
        for cand, scores in sorted_scores.items():
            # scores = candidate_chords[cand]
            lik, cons = cand.likelihood, cand.consonance
            rec, prec = scores['recall'], scores['precision']
            # # take right bracket off the notelist and add it as its own column:
            # lb, rb = cand.notes._brackets

            cand_note_in_input = [(n in input_notes) for n in cand.notes]
            cand_note_is_chromatic = [(n in cand.chromatic_notes) for n in cand.notes]

            # we'll add chromatic markers to the first char of each note name
            # but to do that we first set up the list of the chromatic char if it exists
            # for each note in teh sequence
            chrom = _settings.DIACRITICS['chromatic']
            chrom_markers = [chrom if cand_note_is_chromatic[i] else '' for i in range(len(cand.notes))]

            # then combine that with the out-of-input diacritic in this list copm:
            ooi = _settings.DIACRITICS['note_not_in_input']
            ooi_notes = [f'{(note.name[0] + c + note.name[1:]):{2+len(c)}}' # chromatic diacritic goes between the first char, and the rest of the chars
                            if cand_note_in_input[i] # plain note name
                         else f"{note.name[0] + c + ooi + ''.join([f'{nc}{ooi}' for nc in note.name[1:]]):{2+len(note.name) + len(c)}}"
                         # else f"{(c + ''.join([f'{nc}{ooi}' for nc in note.name])):{2+len(note.name) + len(c)}}" # add diacritic to note name
                         for i,(note,c) in enumerate(zip(cand.notes, chrom_markers))]
            # add brackets around chromatic notes:
            # clb, crb = _settings.BRACKETS['chromatic_intervals']
            # cand_notes_strs = [f' {note_name:>{2+len(note_name)}}' if not cand_note_is_chromatic[i] # plain note name (maybe with diacritic)
            #                    else f'{(clb + note_name + crb):>{3+len(note_name)}}'   # brackets around chromatic notes
            #                    for i,note_name in enumerate(cand_notes_strs)]
            notes_str = ' '.join(ooi_notes)
            missing_notes = [n for n in input_notes if n not in cand.notes]
            missing_notes_str = ' '.join([f'{n.name:2}' for n in missing_notes]) if len(missing_notes) > 0 else ''
            # notes_str = (f'{cand.__repr__()}'.split(rb)[0]).split(lb)[-1].replace(Note._marker, '')
            df.append([f'{cand._marker}{cand.name}', ' '+nlb,
                        notes_str, nrb[-1], missing_notes_str,
                        f'{rec:.2f}', f'{prec:.2f}', f'{lik:.2f}', f'{cons:.3f}'])
        df.show(max_rows=max_results, margin=' ', **kwargs)


def most_likely_key(*args, **kwargs):
    """wrapper around matching_keys that simply returns the single most likely Key as an object"""
    matches = matching_keys(*args, display=False, **kwargs)
    if len(matches) == 0:
        # re run with no minimums
        matches = matching_keys(*args, display=False, min_recall=0, min_precision=0, min_likelihood=0, return_matches=True, **kwargs)
    # return top match:
    return list(matches.keys())[0]
