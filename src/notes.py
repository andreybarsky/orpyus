### this module contains the Note, OctaveNote, and NoteList classes.
### Notes are abstract pitch classes in no particular octave, such as the note C.
### OctaveNotes are specific notes like the keys of a piano, such as C4 (aka middle C)
### NoteLists are simply lists of either types of note, with some useful methods.

from .intervals import Interval, IntervalList
from .parsing import fl, sh, nat, dfl, dsh
from .util import log, rotate_list, check_all
from . import parsing, tuning, _settings
from . import conversion as conv

from functools import cached_property
import math


class Note:
    """a note/chroma/pitch-class defined in the abstract,
    i.e. not associated with a specific note inside an octave,
    such as: C or D#"""
    def __init__(self, name=None, position=None, prefer_sharps=None, case_sensitive=True, strip_octave=False):
        """a Note can be initialised in one of two ways:
            1. by passing to 'name' a valid note name, such as C or D# or Ebb
            2. by passing to 'position' an integer between 0 and 11 (inclusive),
                denoting a semitone offset from C.
                i.e. position 0 is C, 1 is C#, 2 is D... 11 is B

        optional args:
        'prefer_sharps':
            if True, this note will be displayed with sharps where applicable.
            if False, will be displayed with flats where applicable.
            if None (default), will infer sharp/flat preference from 'name' arg,
                or else fall back on global default (defined in _settings module)
        'case_sensitive':
            if True (default), requires note names to be capitalised and will
                throw an error otherwise.
            if False, will accept lowercase chromas like 'c#' as well as ambiguous
                names like 'bb'
        'strip_octave':
            if True, will ignore integers in the note name that may
                have been supplied by mistake.
                e.g. Note('C5') will be interpreted as Note('C')
            if False (default), will throw an error, as this looks like a mistaken
                attempt to initialise an OctaveNote instead of a Note.
        """



        if isinstance(name, Note):
            # accept re-casting: just take the input note's name
            name, prefer_sharps = name.chroma, name.prefer_sharps
        elif isinstance(name, int):
            # we've been passed a position int by mistake instead of a name,
            # which is fine, silently correct:
            position = name
            name = None

        # detect if we've been fed an OctaveNote name by accident:
        if name is not None and name[-1].isdigit():
            if not strip_octave:
                raise ValueError(f"Looks like an OctaveNote name has mistakenly been passed to Note init: {name}")
            else:
                # parse everything but the numeric chars:
                name = ''.join([n for n in name if not n.isdigit()])

        # set main object attributes from init args:
        self.chroma, self.position, self.prefer_sharps = self._parse_input(name, position, prefer_sharps, case_sensitive)
        # 'chroma' is the string denoting pitch class: ('C#', 'Db', 'E', etc.)

        # store sharp and flat names of this note in case they are needed:
        self.sharp_name = preferred_name(self.position, prefer_sharps=True)
        self.flat_name = preferred_name(self.position, prefer_sharps=False)


    #### main input/arg-parsing private method:
    @staticmethod
    def _parse_input(name, position, prefer_sharps, case_sensitive):
        # check that exactly one has been provided:
        assert ((name is not None) + (position is not None) == 1), "Argument to init must include exactly one of: name or position"
        if isinstance(name, int):
            # auto detect initialisation with note value as first arg, silently initialise
            # log(f'Name given but int detected, so initialising instead by value: {name}')
            position = name
            name = None

        if name is not None:
            if isinstance(name, Note):
                # accept Note objects as init arg
                name = name.chroma

            if not isinstance(name, str):
                raise TypeError(f'expected str or int but received {type(name)} to initialise Note object')
            # log(f'Initialising Note with name: {name}')

            # name is definitely a string now

            # detect if sharp or flat:
            if prefer_sharps is None:
                # if no preference is set then we infer from the name argument supplied
                if parsing.is_sharp_ish(name[1:]):
                    prefer_sharps = True
                elif parsing.is_flat_ish(name[1:]):  # len(name) == 2 and
                    prefer_sharps = False
                else: # fallback on global default
                    prefer_sharps = _settings.DEFAULT_SHARPS
            else:
                prefer_sharps = prefer_sharps

            if not case_sensitive:
            # cast to proper case:
                name = name.capitalize()

            position = parsing.note_positions[name]
            name = preferred_name(position, prefer_sharps=prefer_sharps)
        elif position is not None:
            if prefer_sharps is None:
                prefer_sharps = _settings.DEFAULT_SHARPS # global default

            # log(f'Initialising Note with position: {position}')
            name = preferred_name(position, prefer_sharps=prefer_sharps)
        return name, position, prefer_sharps

    @staticmethod
    def from_cache(name=None, position=None, prefer_sharps=None):
        # efficient note init by cache of names to note objects

        if type(name) is int:
            # quietly re-parse args:
            position = name
            name = None

        # get sharp preference from note name if available:
        if (prefer_sharps is None) and isinstance(name, str):
            if parsing.contains_sharp(name):
                prefer_sharps = True
            elif parsing.contains_flat(name):
                prefer_sharps = False

        if name is not None:
            if type(name) is Note:
                # no need to fetch from cache: just return the passed object
                return name
                # name = name.chroma

            if (name, prefer_sharps) in cached_notes:
                return cached_notes[(name, prefer_sharps)]
            else:
                note_obj = Note(name, prefer_sharps=prefer_sharps)
                if _settings.DYNAMIC_CACHING:
                    log(f'Registering note with name {name} and prefer_sharps={prefer_sharps} to cache')
                    cached_notes[(name, prefer_sharps)] = note_obj
                return note_obj
        elif position is not None:
            if (position, prefer_sharps) in cached_notes:
                return cached_notes[(position, prefer_sharps)]
            else:
                note_obj = Note(position=position, prefer_sharps=prefer_sharps)
                if _settings.DYNAMIC_CACHING:
                    log(f'Registering note with position {position} and prefer_sharps={prefer_sharps} to cache')
                    cached_notes[(position, prefer_sharps)] = note_obj
                return note_obj
        else:
            raise Exception(f'Note init from cache must include one of "name" or "position"')


    #### magic methods and note constructors:
    def __add__(self, other):
        """addition with Interval is simple transposition;
        addition with Note produces a Chord object,
        addition with an IntervalList adds each Interval to this Note in sequence to produce a NoteList"""
        # assert isinstance(interval, (int, Interval)), "Only an integer or Interval can be added to a Note"
        if isinstance(other, (int, Interval)):
            # note transposition by interval
            # interval = other.value  # cast to int
            new_pos = (self.position + int(other)) % 12
            new_note = Note.from_cache(position = new_pos, prefer_sharps = self.prefer_sharps) # inherit sharpness from self
            # log(f'Adding interval ({interval}) to self ({self}) to produce Note: {chrm}')
            return new_note
        elif isinstance(other, (str, Note)):
            # addition with other note to produce chord
            if isinstance(other, str):
                other = Note.from_cache(other)
            assert isinstance(other, Note)
            from .chords import Chord # lazy import
            chord_notes = [self, other]
            return Chord(notes=chord_notes)
        elif isinstance(other, IntervalList):
            notes = [self + iv for iv in other]
            return NoteList(notes)
        else:
            raise TypeError(f'Notes can only be added with Intervals or with other Notes, not {type(other)}')

    def __sub__(self, other):
        """if 'other' is an integer, returns a new Note that is shifted down by that many semitones.
        if 'other' is another Note, return the unsigned, symmetric interval distance between them,
        with other as the root. i.e. how many steps LEFT do you have to go to find other?"""

        if isinstance(other, (int, Interval)): # construct Note
            new_pos = (self.position - other) % 12
            new_note = Note.from_cache(position = new_pos, prefer_sharps = self.prefer_sharps)
            # log(f'Subtracting interval ({other}) from self ({self}) to produce Note: {chrm}')
            return new_note
        elif isinstance(other, Note):       # construct Interval
            distance = (self.position - other.position) % 12
            # log(f'Subtracting root Note ({other}) from self ({self}) to produce Interval: {intrv}')
            return Interval(distance)
        else:
            raise Exception(f'Only integers, Intervals, and other Notes can be subtracted from a Notes, not {type(other)}')

    def in_octave(self, octave=4):
        """instantiates an OctaveNote object corresponding to this Note played in a specific octave"""
        return OctaveNote(f'{self.chroma}{int(octave)}')

    # quick accessor for in_octave method defined above:
    def __getitem__(self, octave):
        """returns OctaveNote in the specified octave"""
        assert isinstance(octave, int)
        return self.in_octave(octave)

    ## comparison operators:
    def __eq__(self, other):
        """Enharmonic equality comparison between Notes, returns True if
        they have the same chroma (by comparing Note.position)."""

        if isinstance(other, str) and parsing.is_valid_note_name(other):
            # cast string to Note if possible
            other = Note.from_cache(other)
        if isinstance(other, Note):
            return self.position == other.position
        # elif isinstance(other, OctaveNote):
        #     return self == other.note
        elif other is None:
            return False
        else:
            raise TypeError(f'Notes can only be compared to other Notes, but got: {type(other)}')

    def __hash__(self):
        """note and octavenote hash-equivalence is based on position alone, not value"""
        return hash(f'Note:{self.position}')

    def __ge__(self, other):
        """greater/lesser comparison between abstract Notes treats C as the 'lowest' note,
        and B as the 'highest'"""
        # slightly dubious, but this is based on octave numbering conventions
        if type(other) == Note:
            return self.position > other.position
        else:
            raise Exception(f'> operation for Notes only defined over other Notes, not {type(other)}')

    def __lt__(self, other):
        """see Note.__gt__"""
        if type(other) == Note:
            return self.position < other.position
        else:
            raise Exception(f'< operation for Notes only defined over other Notes, not {type(other)}')

    @property
    def name(self):
        return f'{self.chroma}'

    #### useful public methods / properties:

    def is_natural(self):
        """True if this is a white note, False otherwise"""
        return self.chroma in parsing.natural_note_names
    @property
    def natural(self):
        return self.is_natural()

    def summary(self):
        """list all the properties this Note has"""

        prop_str = f"""
        {str(self)}
        name: {self.name}
        position: {self.position}
        sharp preference: {self.prefer_sharps}
        type: {type(self)}
        id: {id(self)}"""
        print(prop_str)

    @property
    def properties(self):
        """print all the properties of this Note object"""
        return self.summary()

    ## chord constructor:
    def chord(self, modifier=None, intervals=None):
        """instantiate Chord object by parsing either:
        1) a string denoting a Chord modifier, like 'major' or 'minor' or 'dom7'
        2) an iterable of semitone intervals relative to this Note as root
        in the exact same way as Chord.__init__ (we pass this arg there directly)"""
        from src.chords import Chord
        if modifier is None:
            if intervals is None:
                # major by default:
                return Chord(root=self)
            else:
                return Chord(root=self, intervals=intervals)
        elif modifier is not None:
            if isinstance(modifier, str):
                return Chord(self.chroma + modifier)
            elif isinstance(modifier, ChordModifier):
                return Chord(self.chroma, modifiers=modifier)

    ## deep music theory: the 'tempo' of a note:
    def get_tempo(self, max_tempo=120, temperament=None):
        """gets the tempo associated with this note's pitch, below a given
        maximum bpm"""
        first_octavenote = self[1]
        note_pitch_hz = first_octavenote.get_pitch(temperament=temperament)
        bpm = conv.pitch_to_bpm(note_pitch_hz, max_tempo)
        return round(bpm, 1)

    @property
    def tempo(self):
        return self.get_tempo()

    def _wave(self, duration, falloff=True, **kwargs):
        """Outputs a sine wave corresponding to this note,
        by default with exponential volume increase and falloff"""
        # from audio import sine_wave, exp_falloff
        # non-OctaveNotes have no pitch defined,
        # so instantiate a child OctaveNote in default octave=4 and return its wave method instead:
        return self[4]._wave(duration=duration, falloff=falloff, **kwargs)


    def play(self, duration=3, octave=4, type='KS', falloff=True, temperament=None):
        """plays this Note as audio in a desired octave, 4 by default"""
        return self.in_octave(octave).play(duration=duration, type=type,
                                           falloff=falloff, temperament=temperament)

    def __str__(self):
        # e.g. '♩C#'
        return f'{self._marker}{self.name}'

    def __repr__(self):
        return str(self)

    # Note object unicode identifier:
    _marker = _settings.MARKERS['Note']



#### subclass for specific notes at specific pitches
class OctaveNote(Note):
    """a note in a specific octave, rounded to twelve-tone equal temperament, such as C4 or D#2.

    this class inherits everything from Note,
    except it also has .octave, .value, .pitch attrs defined on top,
    and its addition/subtraction operators respect octave/value as well as position.
    """

    def __init__(self, name=None, value=None, pitch=None, prefer_sharps=None):
        """initialises an OctaveNote object from one of the following:
        name: a string denoting a specific note, like 'C#3', or a pitch class, like 'C#'
        value: an integer denoting the note's position on an 88-note piano keyboard,
                where A0 is 1, C4 is 40, and C8 is 88. (the core internal representation)
        pitch: an integer or float corresponding to the note's frequency in Hz,
                where the reference note A4 is 440 Hz by default (though changeable in _settings)"""

        # set main object attributes from init args:
        self.chroma, self.value, self.prefer_sharps = self._parse_input(name, value, pitch, prefer_sharps)
        # compute octave, position, and name:
        self.octave, self.position = conv.oct_pos(self.value)

        self.reference_pitch = self.get_pitch(temperament='EQUAL') # reference (12-TET) pitch calculated by formula

    @property
    def pitch(self):
        return self.get_pitch()
    def get_pitch(self, temperament=None):
        """gets the pitch of this OctaveNote according to the specified tuning temperament,
        which must be one of: EQUAL, JUST, or RATIONAL.
        by default, this uses the global tuning mode specified in _settings.TUNING_SYSTEM"""
        if temperament is None:
            temperament = tuning.get_temperament('PLAYBACK')
        return conv.value_to_pitch(self.value, temperament)

    #### main input/arg-parsing private method:
    @staticmethod
    def _parse_input(name, value, pitch, prefer_sharps):
        """parses name, value, pitch input args (and sharp preference)
        returns correct chroma, value, and pitch"""
        # check that exactly one of our input args has been provided:
        assert ((name is not None) + (value is not None) + (pitch is not None) == 1), "Argument to init must include exactly one of: name, value, or pitch"

        # accept OctaveNote as input, instantiate a new one with the same properties:
        if isinstance(name, OctaveNote):
            return name.chroma, name.value, name.prefer_sharps
        # accept Note as well:
        elif isinstance(name, Note):
            name = name.name
            raise Exception('Note object incorrectly passed to OctaveNote init method')

        if type(name) == int:
            # auto detect initialisation with note value as first arg, silently substitute if there's a TypeError:
            log(f'Positional name arg passed to OctaveNote.__init__ as int instead of str, so initialising instead by value')
            value = name
            name = None
        elif type(name) == float:
            log(f'Positional name arg passed to OctaveNote.__init__ as float instead of str, so initialising instead by pitch')
            pitch = name
            name = None

        ### the following block defines: chroma, value, and pitch
        if name is not None:
            # log(f'Initialising OctaveNote with name: {name}')
            # detect if sharp or flat:
            if prefer_sharps is None:
                # if no preference is set then we infer from the name argument supplied
                if parsing.is_sharp_ish(name[1:-1]):
                    prefer_sharps = True
                elif parsing.is_flat_ish(name[1:-1]):  # len(name) == 2 and
                    prefer_sharps = False
                else: # fallback on global default
                    prefer_sharps = _settings.DEFAULT_SHARPS
            else:
                prefer_sharps = prefer_sharps

            chroma, octave = parsing.parse_octavenote_name(name)
            position = parsing.note_positions[chroma]
            value = conv.oct_pos_to_value(octave, position)
            # pitch = conv.value_to_pitch(value)
        if value is not None:
            # log(f'Initialising OctaveNote with value: {value}')
            value = value
            octave, position = conv.oct_pos(value)
            chroma = preferred_name(position, prefer_sharps=prefer_sharps)
            # pitch = conv.value_to_pitch(value)
        if pitch is not None:
            # log(f'Initialising OctaveNote with pitch: {pitch}')
            pitch = float(pitch)
            assert pitch > 0, "Pitch must be greater than 0"
            value = conv.pitch_to_value(pitch, nearest=True)
            octave, position = conv.oct_pos(value)
            chroma = preferred_name(position, prefer_sharps=prefer_sharps)
        return chroma, value, prefer_sharps

    #### operators & magic methods:
    def __add__(self, interval):
        """returns a new OctaveNote that is shifted up by some integer number of semitones."""
        assert isinstance(interval, (int, Interval)), "Only Intervals/integers can be added or subtracted to an Octave note"
        return OctaveNote(value = self.value + interval, prefer_sharps=self.prefer_sharps)

    def __sub__(self, other):
        """if 'other' is an integer or Interval, returns a new Note that is shifted down by that many semitones.
        if 'other' is another Note, return the interval distance between them, with other as the root."""
        if isinstance(other, (int, Interval)):
            return OctaveNote(value = self.value - other, prefer_sharps=self.prefer_sharps)
        elif isinstance(other, OctaveNote):
            return Interval(self.value - other.value)
        else:
            raise Exception("Only Intervals/integers can be added or subtracted to an Octave note")

    def __pow__(self, i):
        """raise this note by i octaves"""
        return OctaveNote(self.value + (12*i))

    def __ge__(self, other):
        assert isinstance(other, OctaveNote), "OctaveNotes can only be greater or less than other OctaveNotes"
        return self.value >= other.value

    def __lt__(self, other):
        assert isinstance(other, OctaveNote), "OctaveNotes can only be greater or less than other OctaveNotes"
        return self.value < other.value

    def __and__(self, other):
        """Enharmonic equivlence comparison: Compares with another Note
        and returns True if both have the same position, but disregards note value."""

        assert isinstance(other, Note), "OctaveNotes can only be enharmonic to other notes"
        return self.position == other.position

    def __eq__(self, other):
        """OctaveNotes are equal to other OctaveNotes that share their position and octave."""
        if isinstance(other, OctaveNote):
            return self.value == other.value
        else:
            raise TypeError(f'OctaveNote __eq__ only defined for other OctaveNotes, not: {type(other)}')

    def __hash__(self):
        """note and octavenote hash-equivalence is based on position alone, not value"""
        return hash(f'Note:{self.position}')

    @property
    def name(self):
        return f'{self.chroma}{self.octave}'

    #### useful public methods:



    ## Note parent class constructor
    @property
    def note(self):
        """returns the parent class Note object
        associated with this OctaveNote"""
        return Note.from_cache(self.chroma)


    #### utility methods for name-value-pitch conversion

    ## polymorphic note getters:
    @staticmethod
    def get_note_name(inp, prefer_sharps=_settings.DEFAULT_SHARPS):
        """Takes an input as either value (int) or pitch (float),
        returns appropriate OctaveNote name, e.g. F#4"""
        ### parse input as either value or pitch, retrieve coresponding note name
        if type(inp) == int:
            return conv.value_to_name(inp, prefer_sharps=prefer_sharps)
        elif type(inp) == float:
            return conv.pitch_to_name(inp, prefer_sharps=prefer_sharps)
        elif type(inp) == str:
            # cast string to int then try again
            try:
                print(f'Casting {inp} to int and trying again')
                return OctaveNote.get_note_name(int(inp), prefer_sharps=prefer_sharps)
            except:
                try:
                    print(f'Casting {inp} to float and trying again')
                    # cast to float then try again
                    return OctaveNote.get_note_name(float(inp), prefer_sharps=prefer_sharps)
                except:
                    raise Exception('Invalid string input to note_name')
        elif type(inp) in (tuple, list):
            # inverse oct-pos
            assert len(inp) == 2, "Received iterable to get_note_name, expected an (oct,pos) pair but got {len(inp)} values instead"
            oct, pos = inp
            value = conv.oct_pos_to_value(oct, pos)
            return conv.value_to_name(value, prefer_sharps=prefer_sharps)

    @staticmethod
    def get_note_value(inp):
        """Takes an input as either name (string, e.g.: 'F#4') or pitch (float, e.g.: 370.0),
        or (oct, pos) pair
        returns appropriate OctaveNote value, e.g. 46"""
        if type(inp) == str:
            return conv.name_to_value(inp)
        elif type(inp) in (tuple, list):
            # inverse oct-pos
            assert len(inp) == 2, "Received iterable to get_note_value, expected an (oct,pos) pair but got {len(inp)} values instead"
            oct, pos = inp
            return conv.oct_pos_to_value(oct, pos)
        elif type(inp) == float:
            return conv.pitch_to_value(inp)
        else:
            raise TypeError('Can only get_note_value from string, float, or (oct,pos) pair')

    @staticmethod
    def get_note_pitch(inp):
        ### parse input as either name or value, retrieve corresponding note pitch
        if type(inp) == str:
            return conv.name_to_pitch(inp)
        elif type(inp) == int:
            return conv.value_to_pitch(inp)
        elif type(inp) in (tuple, list):
            # inverse oct-pos
            assert len(inp) == 2, "Received iterable to get_note_pitch, expected an (oct,pos) pair but got {len(inp)} values instead"
            oct, pos = inp
            value = conv.oct_pos_to_value(oct, pos)
            return conv.value_to_pitch(value)
        else:
            raise TypeError('Can only get_note_pitch from string, int, or (oct,pos) pair')

    def next(self, chroma):
        """returns an OctaveNote object of a specified chroma
        that is the next highest one after self"""
        if isinstance(chroma, Note):
            chroma = chroma.chroma
        target_position = parsing.note_positions[chroma]
        pos_offset = (target_position - self.position) % 12
        return OctaveNote(value = self.value + pos_offset, prefer_sharps=self.prefer_sharps)
        # candidates = OctaveNote(f'{chroma}{self.octave}'), OctaveNote(f'{chroma}{self.octave+1}')
        # low_cand, high_cand = candidates
        # if low_cand > self:
        #     return low_cand
        # else:
        #     return high_cand

    def _wave(self, duration, type='KS', falloff=False, temperament=None, cache=True):
        """Outputs a sine wave corresponding to this note,
        by default with exponential volume increase and falloff"""
        from .audio import synth_wave
        # get this note's pitch by desired temperament system: (default from settings)
        tuned_pitch = self.get_pitch(temperament=temperament)
        # wave = sine_wave(freq=self.pitch, duration=duration)
        # use karplus-strong wave table synthesis for guitar-string timbre:
        wave = synth_wave(freq=tuned_pitch, duration=duration, type=type, falloff=falloff, cache=cache)
        # log(f'Adding note {self} with pitch {tuned_pitch} (temperament={temperament})', force=True, depth=6)
        return wave

    def play(self, duration=2, type='KS', falloff=True, block=False, temperament=None):
        from .audio import play_wave
        wave = self._wave(duration=duration, type=type, falloff=falloff, temperament=temperament)
        play_wave(wave, block=block)

    @property
    def _marker(self):
        """unicode marker associated with this class"""
        return '♪'

    def __str__(self):
        """Returns a pretty version of this OctaveNote's name,
        which includes its chroma as well as its octave."""
        return f'{self._marker}{self.name}'

    def __repr__(self):
        return str(self)

    # OctaveNote object unicode identifier:
    _marker = _settings.MARKERS['OctaveNote']


class NoteList(list):
    """List subclass that is instantianted with an iterable of Note-like objects and forces them all to Note type"""
    def __init__(self, *items, strip_octave=True):
        self.strip_octave = strip_octave

        if len(items) == 1:
            arg = items[0]

            # if we have been passed a single string as arg, parse it out as a series of notes:
            if isinstance(arg, str):
                arg = parsing.parse_out_note_names(arg)

            # now either way we should have an iterable of note-likes:
            try:
                note_items = self._cast_notes(arg, strip_octave=strip_octave)
            except Exception as e:
                print(f'Could not parse NoteList input as a series of notes: {arg}')
                raise e
        else:
            # we've been passed a series of items that we can unpack
            note_items = self._cast_notes(items, strip_octave=strip_octave)

        super().__init__(note_items)


    # TBI: is this needed or does it just cause bloat? (might be needed for sharp-preference inside KeyChords etc.)
    def _recast(self, note_obj, strip_octave=None):
        """accepts a Note or OctaveNote and re-casts it to the same type"""
        if strip_octave is None:
            strip_octave = self.strip_octave
        if isinstance(note_obj, OctaveNote):
            if strip_octave:
                return Note.from_cache(position=note_obj.position, prefer_sharps=note_obj.prefer_sharps)
            else:
                return OctaveNote(note_obj.name)
        elif isinstance(note_obj, Note):
            return Note.from_cache(position=note_obj.position, prefer_sharps=note_obj.prefer_sharps)
        else:
            raise TypeError(f'Cannot recast non-Note object: {type(note_obj)}')

    def _cast_notes(self, items, strip_octave):
        """accepts an iterable of Note objects, or strings that cast to Note objects,
        and returns them strictly as a list of Note objects"""
        note_items = []
        for item in items:
            if isinstance(item, str):
                if parsing.begins_with_valid_note_name(item):
                    note_items.append(Note.from_cache(item)) # , strip_octave=strip_octave))
                else:
                    raise ValueError(f'{item} is a string but does not cast to a note name')
            elif isinstance(item, Note):
                note_items.append(self._recast(item))
        return note_items

    def append(self, other):
        """Cast any appendands to Notes"""
        super().append(self._recast(other))

    def extend(self, other):
        """Cast any extensions to Notes"""
        assert isinstance(other, (list, tuple)), "Can only extend NoteList by a list or tuple"
        for n in other:
            self.append(n)
        # self.extend([self._recast(n) for n in other])

    def __add__(self, other):
        """adds a scalar to each note in this list,
        concatenates with another NoteList,
        or accepts another iterable and performs point-wise addition."""
        if isinstance(other, (int, Interval)):
            return NoteList([n + other for n in self])
        elif isinstance(other, NoteList):
            # concatenation with another notelist: (as with regular list)
            return NoteList(list(self) + list(other))
        elif isinstance(other, (list, tuple)):
            assert len(self) == len(other), "Can only add NoteLists with scalars, other NoteLists, or other iterables of equal length"
            # return a NoteList, since nothing but Intervals can be added to Notes, and the result is always a new Note
            return NoteList([i + j for i,j in zip(self, other)])
        else:
            raise Exception(f"Can't add NoteList with {type(other)}")

    def __sub__(self, other):
        """subtracts a scalar from each Note in this list (producing NoteList),
        subtracts a single Note from each note in this list (producing IntervalList)
        or performs point-wise subtraction with an iterable, (producing NoteList or
            IntervalList depending on the resulting types)"""
        if isinstance(other, (int, Interval)):
            return NoteList([n - other for n in self])
        elif isinstance(other, Note):
            return IntervalList([n - other for n in self])
        elif isinstance(other, (list, tuple)):
            assert len(self) == len(other), "Can only subtract NoteLists with Notes, scalars, or with iterables of equal length"
            out_list = [i - j for i,j in zip(self, other)]
            if isinstance(other, IntervalList) or check_all(out_list, 'isinstance', Note):
                # return a NoteList if we've ended up with only notes:
                return NoteList(out_list)
            elif isinstance(other, NoteList) or check_all(out_list, 'isinstance', (int, Interval)):
                # or an IntervalList if we've ended up with only intervals:
                return IntervalList(out_list)
            else:
                # else just return a plain list
                return out_list
        else:
            raise Exception(f"Can't subtract {type(other)} from NoteList")

    ### there was previously a __contains__ method here,
    ### but it is not needed since list.__contains__ suffices combined with
    ### note equivalence behaviour with strings, i.e. Note('C') == 'C'

    def unique(self):
        """returns a new NoteList, where repeated notes are dropped after the first"""
        unique_notes = []
        unique_notes_set = set() # for efficiency
        for n in self:
             if n not in unique_notes_set:
                 unique_notes.append(n)
                 unique_notes_set.add(n)
        return NoteList(unique_notes)

    def repeated(self):
        """Opposite of self.unique - returns a new NoteList containing only the
        notes that are repeated more than once in this existing object"""
        repeated_notes_set = set()
        unique_notes_set = set() # for efficiency
        for i in self:
             if i not in unique_notes_set:
                 unique_notes_set.add(i)
             else:
                 repeated_notes_set.add(i)
        # return in same order as original:
        return NoteList([n for n in self if n in repeated_notes_set])

    def __hash__(self):
        """NoteLists hash as tuples for the purposes of chord/key reidentification"""
        return hash(tuple(self))

    def rotate(self, num_places):
        """returns the rotated NoteList that begins num_steps up
        from the beginning of this one. used for inversions,
        i.e. the 2nd inversion of [0,1,2] is [1,2,0], (a rotation of 1 place in this case)
        and for modes, which are rotations of scales. """

        return NoteList(rotate_list(self, num_places))

    def relative_intervals(self, root=None):
        """casts Notes into Intervals, strictly positive, relative to a 'root'
        note. if None, this is the first note in the NoteList by default"""
        if root is None:
            root = self[0]
        elif type(root) is not Note:
            root = Note(root)

        relative_intervals = (self - root).flatten()
        return relative_intervals
    intervals_from_root = relative_intervals # convenience alias

    def ascending_intervals(self):
        """sorts notes into ascending order from first note (as root)"""
        # wrap around first octave and calculate intervals from root:
        octaved_notes = self.force_octave(1)
        root = octaved_notes[0]
        return IntervalList([o - root for o in octaved_notes])

    def from_octave(self, octave):
        return self.force_octave(start_octave=octave, min_octave=0, max_octave=9)

    @property
    def intervals(self):
        return self.ascending_intervals()

    def force_octave(self, start_octave=None, min_octave=1, max_octave=5):
        """returns another NoteList of ascending OctaveNotes corresponding to
        the Notes in this NoteList, either starting at some specified octave
        or within some min and max octave constraints"""
        octavenotes = []

        # use the first note's octave if it is an OctaveNote, else fall back on default
        auto_octave = False
        if start_octave is None:
            if isinstance(self[0], OctaveNote):
                start_octave = self[0].octave
                # add octavenote to list:
                octavenotes.append(self[0])
            else:
                start_octave = 3
                auto_octave = True
                # cast abstract first note to octavenote:
                octavenotes.append(self[0].in_octave(start_octave))
                # auto_octave will let us adjust pitch down later
        else:
            # cast abstract first note to octavenote:
            if not isinstance(self[0], OctaveNote):
                octavenotes.append(self[0].in_octave(start_octave))
            else:
                # overwrite octave of existing octavenote:
                octavenotes.append((self[0].note).in_octave(start_octave))

        for note in self[1:]:
            if isinstance(note, OctaveNote):
                octavenotes.append(note)
            else:
                # append the next ascending OctaveNote of that chroma:
                octavenotes.append(octavenotes[-1].next(note.chroma))

        return octavenotes

    def matching_chords(self, *args, **kwargs):
        """wrapper for chords.matching_chords function: displays or returns
        a listing of the possible chords that fit these (unordered) notes"""
        from . import chords
        return chords.matching_chords(self, *args, **kwargs)

    def most_likely_chord(self, *args, **kwargs):
        from . import chords
        return chords.most_likely_chord(self, *args, **kwargs)

    def matching_keys(self, *args, **kwargs):
        """wrapper for keys.matching_keys function: displays or returns
        a listing of the possible keys that fit these (unordered) notes"""
        from src.keys import matching_keys
        return matching_keys(notes=self, *args, **kwargs)

    def _waves(self, duration, octave, type, falloff=False, temperament=None):
        wave_notes = self.force_octave(start_octave=octave)
        print(f'  -synthesising notes: {wave_notes}')
        waves = [n._wave(duration=duration, type=type, falloff=falloff, temperament=temperament) for n in wave_notes]
        return waves

    def _chord_wave(self, duration, octave, delay=None, type='KS', falloff=True, temperament=None):
        from .audio import arrange_chord
        from .chords import most_likely_chord
        if delay is None:
            # print(f' synthesising chord: {(most_likely_chord(self)).name} in octave {octave}')
            log(f' synthesising chord: {(most_likely_chord(self)).name} in octave {octave}')
            chord_wave = arrange_chord(self._waves(duration, octave, type, temperament=temperament), norm=False, falloff=falloff)
            return chord_wave
        else:
            # delay arg has been given so we stagger the chord, making it an arpeggio instead:
            return self._melody_wave(duration=duration, octave=octave, delay=delay, type=type, falloff=falloff, temperament=temperament)

    def _melody_wave(self, duration, octave, delay, type='KS', falloff=True, temperament=None):
        from .audio import arrange_melody
        from .chords import most_likely_chord
        # log(f' synthesising arpeggio: {(most_likely_chord(self)).name} in octave:{octave if octave is not None else "Default"} (w/ delay={delay})')
        log(f' synthesising arpeggio from notes: {self} in octave:{octave if octave is not None else "Default"} (w/ delay={delay})')
        melody_wave = arrange_melody(self._waves(duration, octave, type, temperament=temperament), delay=delay, norm=False, falloff=falloff)
        return melody_wave

    def play(self, delay=0.2, duration=3, octave=None, falloff=True, block=False, temperament=None, type='KS', **kwargs):
        from .audio import play_wave
        if octave is None and isinstance(self[0], OctaveNote):
            # auto infer octave if this list starts with an octavenote:
            octave = self[0].octave

        if delay is not None:
            wave = self._melody_wave(duration=duration, octave=octave,
                                     delay=delay, type=type, falloff=falloff,
                                    temperament=temperament, **kwargs)
        else:
            wave = self._chord_wave(duration=duration, octave=octave,
                                    type=type, falloff=falloff,
                                    temperament=temperament, **kwargs)
        play_wave(wave, block=block)

    def join(self, s, markers=False):
        """returns a string of the notes in this notelist joined by the specified char/s"""
        if markers:
            return s.join([str(n) for n in self])
        else:
            return s.join([n.name for n in self])

    def __str__(self):
        lb, rb = self._brackets
        return f'{lb}{self.join(", ")}{rb}'

    def __repr__(self):
        # return f'𝄃{super().__repr__()}𝄂'
        return str(self)

    _brackets = _settings.BRACKETS['NoteList']


# get note name string from position in octave:
def preferred_name(pos, prefer_sharps=_settings.DEFAULT_SHARPS):
    """Gets the note name for a specific position according to preferred sharp/flat notation,
    or just the natural note name if a a white note"""
    # if we've accidentally been given an Interval object for position, we quietly parse it:
    if isinstance(pos, Interval):
        pos = pos.value
    name = parsing.preferred_note_names[fl][pos] if not prefer_sharps else parsing.preferred_note_names[sh][pos]
    return name

# quality-of-life alias:
Notes = NoteList

# predefined Note objects:
A = Note('A')
Ash, Bb = Note('A#'), Note('Bb')
B = Note('B')
C = Note('C')
Csh, Db = Note('C#'), Note('Db')
D = Note('D')
Dsh, Eb = Note('D#'), Note('Eb')
E = Note('E')
F = Note('F')
Fsh, Gb = Note('F#'), Note('Gb')
G = Note('G')
Gsh, Ab = Note('G#'), Note('Ab')

MiddleC = OctaveNote('C4')

# all chromatic pitch classes:
chromatic_flat_notes = [C, Db, D, Eb, E, F, Gb, G, Ab, A, Bb, B]
chromatic_sharp_notes = [C, Csh, D, Dsh, E, F, Fsh, G, Gsh, A, Ash, B]
# whichever is the default is determined by _settings default sharp preference:
chromatic_notes = chromatic_sharp_notes if _settings.DEFAULT_SHARPS else chromatic_flat_notes

# note cache by name for efficient init:
cached_notes = {(n,s): Note(n, prefer_sharps=s) for n in parsing.common_note_names for s in [None, False, True]}
cached_notes.update({(p,s) : Note(position=p, prefer_sharps=s) for p in range(12) for s in [None, False, True]})

# relative minors/majors of all chromatic notes:
relative_minors = {c.name : (c - 3).name for c in chromatic_notes}
relative_minors.update({c.sharp_name: (c-3).sharp_name for c in chromatic_notes})
relative_minors.update({c.flat_name: (c-3).flat_name for c in chromatic_notes})

relative_majors = {value:key for key,value in relative_minors.items()}

# some chord/key tonics correspond to a preference for sharps or flats:
sharp_tonic_names = ['G', 'D', 'A', 'E', 'B']
flat_tonic_names = ['F', f'B{fl}', f'E{fl}', f'A{fl}', f'D{fl}']
neutral_tonic_names = ['C', f'G{fl}'] # no sharp/flat preference, fall back on default

sharp_major_tonics = [Note.from_cache(t, prefer_sharps=True) for t in sharp_tonic_names]
flat_major_tonics = [Note.from_cache(t, prefer_sharps=False) for t in flat_tonic_names]
neutral_major_tonics = [Note.from_cache(t) for t in neutral_tonic_names]
major_tonics = sorted(sharp_major_tonics + flat_major_tonics + neutral_major_tonics)

sharp_minor_tonics = [Note.from_cache(relative_minors[t], prefer_sharps=True) for t in sharp_tonic_names]
flat_minor_tonics = [Note.from_cache(relative_minors[t], prefer_sharps=False) for t in flat_tonic_names]
neutral_minor_tonics = [Note.from_cache(relative_minors[t]) for t in neutral_tonic_names]
minor_tonics = sorted(sharp_minor_tonics + flat_minor_tonics + neutral_minor_tonics)

### TBI: improved recognition of double-sharp and double-flat notes for exotic keys?
