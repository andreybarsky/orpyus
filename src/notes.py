### this module contains the Note, OctaveNote, and NoteList classes.
### Notes are abstract pitch classes in no particular octave, such as the note C.
### OctaveNotes are specific notes like the keys of a piano, such as C4 (aka middle C)
### NoteLists are simply lists of either types of note, with some useful methods.

from .intervals import Interval, IntervalList
from . import parsing
from . import conversion as conv
from .util import log, rotate_list
from . import _settings

import math


# relative values (positions within scale) with respect to C major, starting with 0=C:
# parsing.note_positions = {note_name:i for i, note_name in enumerate(note_names['generic'])}
# parsing.note_positions.update({note_name:i for i, note_name in enumerate(note_names['flat'])})
# parsing.note_positions.update({note_name:i for i, note_name in enumerate(note_names['sharp'])})
#
# parsing.note_positions.update({note_name:i for i, note_name in enumerate(note_names['flat_unicode'])})
# parsing.note_positions.update({note_name:i for i, note_name in enumerate(note_names['sharp_unicode'])})
# parsing.note_positions.update({note_name:i for i, note_name in enumerate(note_names['natural_unicode'])})

# get note name string from position in octave:
def preferred_name(pos, prefer_sharps=False):
    """Gets the note name for a specific position according to preferred sharp/flat notation,
    or just the natural note name if a a white note"""
    # if we've accidentally been given an Interval object for position, we quietly parse it:
    if isinstance(pos, Interval):
        pos = pos.value
    name = parsing.preferred_note_names['b'][pos] if not prefer_sharps else parsing.preferred_note_names['#'][pos]
    return name


class Note:
    """a note/chroma/pitch-class defined in the abstract,
    i.e. not associated with a specific note inside an octave,
    such as: C or D#"""
    def __init__(self, name=None, position=None, prefer_sharps=None, case_sensitive=True, strip_octave=False):

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
        self.name, self.position, self.prefer_sharps = self._parse_input(name, position, prefer_sharps, case_sensitive)

        # 'chroma' is the string denoting pitch class: ('C#', 'Db', 'E', etc.)
        self.chroma = self.name # these two are the same for Note class, but may be different for OctaveNote subclass

        # boolean flag, is True for white notes:
        self.natural = self.chroma in parsing.natural_note_names

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
                    prefer_sharps = False
            else:
                prefer_sharps = prefer_sharps

            if not case_sensitive:
            # cast to proper case:
                name = name.capitalize()

            position = parsing.note_positions[name]
            name = preferred_name(position, prefer_sharps=prefer_sharps)
        elif position is not None:
            if prefer_sharps is None:
                prefer_sharps = False # default

            # log(f'Initialising Note with position: {position}')
            name = preferred_name(position, prefer_sharps=prefer_sharps)
        return name, position, prefer_sharps

    @staticmethod
    def from_cache(name=None, position=None, prefer_sharps=None):
        # efficient note init by cache of names to note objects
        if name is not None:
            if isinstance(name, Note): # recast note object input to string
                name = name.chroma
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

    ## private utility functions:
    def _set_sharp_preference(self, prefer_sharps):
        """modify sharp preference in place"""
        self.prefer_sharps = prefer_sharps
        self.name = preferred_name(self.position, prefer_sharps=self.prefer_sharps)

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
            raise TypeError(f'Notes can only be added with Intervals or with other Notes')

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
            raise Exception('Only integers, Intervals, and other Notes can be subtracted from a Note')

    def in_octave(self, octave=4):
        """instantiates an OctaveNote object corresponding to this Note played in a specific octave"""
        return OctaveNote(f'{self.chroma}{int(octave)}')

    # # quick accessor for in_octave method defined above:
    # def __getitem__(self, octave):
    #     """returns OctaveNote in the specified octave"""
    #     assert isinstance(octave, int)
    #     return self.in_octave(octave)

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
        else:
            raise TypeError('Notes can only be compared to other Notes')

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
            raise Exception('> operation for Notes only defined over other Notes')

    def __lt__(self, other):
        """see Note.__gt__"""
        if type(other) == Note:
            return self.position < other.position
        else:
            raise Exception('< operation for Notes only defined over other Notes')

    #### useful public methods:
    @property
    def properties(self):
        """Describe all the useful properties this Note has"""

        prop_str = """<{str(self)}
        name: {self.name}
        position: {self.position}
        sharp preference: {self.prefer_sharps}
        type: {type(self)}
        id: {id(self)}>"""
        return prop_str

    def summary(self):
        """Prints all the properties of this Note object"""
        print(self.properties)

    ## chord constructors:
    def chord(self, arg='major'):
        """instantiate Chord object by parsing either:
        1) a string denoting a Chord quality, like 'major' or 'minor' or 'dom7'
        2) an iterable of semitone intervals relative to this Note as root
        in the exact same way as Chord.__init__ (we pass this arg there directly)"""

        from chords import Chord
        return Chord(self, arg)

    def _wave(self, duration, falloff=True, **kwargs):
        """Outputs a sine wave corresponding to this note,
        by default with exponential volume increase and falloff"""
        # from audio import sine_wave, exp_falloff
        # non-OctaveNotes have no pitch defined,
        # so instantiate a child OctaveNote in default octave=4 and return its wave method instead:
        return self[4]._wave(duration=duration, falloff=falloff, **kwargs)
        # wave = sine_wave(freq=wave_note.pitch, duration=duration)
        # if falloff:
        #     wave = exp_falloff(wave, **kwargs)
        # return wave

    def play(self, duration=3, falloff=True):
        # from audio import play_wave
        return self[4].play(duration=duration, falloff=falloff)
        # wave = self._wave(duration=duration, falloff=falloff)
        # play_wave(wave)

    def __str__(self):
        # e.g. is of form: '♩C#'
        return f'{self._marker}{self.name}'

    def __repr__(self):
        return str(self)

    # Note object unicode identifier:
    _marker = _settings.MARKERS['Note']



#### subclass for specific notes on keyboard
class OctaveNote(Note):
    """a note in a specific octave, rounded to twelve-tone equal temperament, such as C4 or D#2.

    this class functions as a Note in every respect,
    except it also has .octave, .value, .pitch attrs defined on top,
    and its addition/subtraction operators respect octave/value as well as position.
    """

    def __init__(self, name=None, value=None, pitch=None, prefer_sharps=None):
        """initialises an OctaveNote object from one of the following:
        name: a string denoting a specific note, like 'C#3', or a pitch class, like 'C#'
        value: an integer denoting the note's position on an 88-note piano keyboard,
                where A0 is 1, C4 is 40, and C8 is 88. (the core internal representation)
        pitch: an integer or float corresponding to the note's frequency in Hz,
                where the reference note A4 is 440 Hz"""

        # set main object attributes from init args:
        self.chroma, self.value, self.pitch, self.prefer_sharps = self._parse_input(name, value, pitch, prefer_sharps)
        # compute octave, position, and name:
        self.octave, self.position = conv.oct_pos(self.value)
        self.name = f'{self.chroma}{self.octave}'

        # self.prefer_sharps = prefer_sharps

    #### main input/arg-parsing private method:
    @staticmethod
    def _parse_input(name, value, pitch, prefer_sharps):
        """parses name, value, pitch input args (and sharp preference)
        returns correct chroma, value, and pitch"""
        # check that exactly one of our input args has been provided:
        assert ((name is not None) + (value is not None) + (pitch is not None) == 1), "Argument to init must include exactly one of: name, value, or pitch"

        # accept OctaveNote as input, instantiate a new one with the same properties:
        if isinstance(name, OctaveNote):
            return name.chroma, name.value, name.pitch, name.prefer_sharps
        # accept Note as well:
        elif isinstance(name, Note):
            name = name.name
            raise Exception('Note object passed to OctaveNote init method')

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
                    prefer_sharps = False
            else:
                prefer_sharps = prefer_sharps

            chroma, octave = parsing.parse_octavenote_name(name)
            position = parsing.note_positions[chroma]
            value = conv.oct_pos_to_value(octave, position)
            pitch = conv.value_to_pitch(value)
        if value is not None:
            # log(f'Initialising OctaveNote with value: {value}')
            value = value
            octave, position = conv.oct_pos(value)
            chroma = preferred_name(position, prefer_sharps=prefer_sharps)
            pitch = conv.value_to_pitch(value)
        if pitch is not None:
            # log(f'Initialising OctaveNote with pitch: {pitch}')
            pitch = float(pitch)
            assert pitch > 0, "Pitch must be greater than 0"
            value = conv.pitch_to_value(pitch, nearest=True)
            octave, position = conv.oct_pos(value)
            chroma = preferred_name(position, prefer_sharps=prefer_sharps)
        return chroma, value, pitch, prefer_sharps

    ## private utility function:
    def _set_sharp_preference(self, preference):
        """modify sharp preference in place"""
        self.prefer_sharps = preference
        self.chroma = preferred_name(self.position, prefer_sharps=self.prefer_sharps)
        self.name = f'{self.chroma}{self.octave}'

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

    #### useful public methods:

    ## Note parent class constructor
    @property
    def note(self):
        """returns the parent class Note object
        associated with this OctaveNote"""
        return Note.from_cache(self.chroma)

    ## ChordVoicing constructor
    def chord(self, *args):
        """instantiate ChordVoicing object by parsing either:
        1) a string denoting a Chord quality, like 'major' or 'minor' or 'dom7'
        2) a list of semitone intervals relative to this Note as root
        in the exact fashion as ChordVoicing.__init__, since we pass our args there directly"""

        from chords import ChordVoicing # specific chord subclass defined on positions and octaves
        return ChordVoicing(self, *args)
        # # case 1:
        # if len(args) == 1 and isinstance(args[0], str):
        #     quality = args[0]
        #     return chords.ChordVoicing(self.name, quality, octave=self.octave)
        #
        # # case 2:
        # else:
        #     intervals = args
        #     # positions = [root] + [(self + interval).position for interval in intervals]
        #     return chords.ChordVoicing(self.name, intervals, octave=self.octave)



    #### utility methods for name-value-pitch conversion

    ## polymorphic note getters:
    @staticmethod
    def get_note_name(inp, prefer_sharps=False):
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
        candidates = OctaveNote(f'{chroma}{self.octave}'), OctaveNote(f'{chroma}{self.octave+1}')
        low_cand, high_cand = candidates
        if low_cand > self:
            return low_cand
        else:
            return high_cand

    def _wave(self, duration, type='KS', falloff=False, cache=True):
        """Outputs a sine wave corresponding to this note,
        by default with exponential volume increase and falloff"""
        from .audio import synth_wave
        # wave = sine_wave(freq=self.pitch, duration=duration)
        # use karplus-strong wave table synthesis for guitar-string timbre:
        wave = synth_wave(freq=self.pitch, duration=duration, type=type, falloff=falloff, cache=cache)
        return wave

    def play(self, duration=2, falloff=True, block=False):
        from .audio import play_wave
        # return self[4].play(duration=duration, falloff=falloff)
        wave = self._wave(duration=duration, falloff=falloff)
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
                return Note.from_cache(position=note_obj.position)
            else:
                return OctaveNote(note_obj.name)
        elif isinstance(note_obj, Note):
            return Note.from_cache(position=note_obj.position)
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

        # if (auto_octave) and (octavenotes[-1].octave > max_octave):
            # keep the chord below c5 if it's ended up too high:

            ### TBI: sort out what I was trying to do here
            # octave_shift = int(octavenotes[-1] - max_octave)
            # if octavenotes[0] - (12*octave_shift) < min_octave:
            #     raise ValueError(f"NoteList's notes span too great of a pitch range: {octave_shift} octaves exceeds min={min_octave} and max={max_octave}")

            # octavenotes = [n - (12*octave_shift) for n in octavenotes]

        return octavenotes

    def matching_chords(self, *args, **kwargs):
        """wrapper for chords.matching_chords function: displays or returns
        a listing of the possible chords that fit these (unordered) notes"""
        from . import chords
        return chords.matching_chords(self, *args, **kwargs)

    def most_likely_chord(self, *args, **kwargs):
        from . import chords
        return chords.most_likely_chord(self, *args, **kwargs)

    def _waves(self, duration, octave, type, falloff=False):
        wave_notes = self.force_octave(start_octave=octave)
        print(f'  -synthesising notes: {wave_notes}')
        waves = [n._wave(duration=duration, type=type, falloff=falloff) for n in wave_notes]
        return waves

    def _chord_wave(self, duration, octave, delay=None, type='KS', falloff=True):
        from .audio import arrange_chord
        from .chords import most_likely_chord
        if delay is None:
            # print(f' synthesising chord: {(most_likely_chord(self)).name} in octave {octave}')
            log(f' synthesising chord: {(most_likely_chord(self)).name} in octave {octave}')
            chord_wave = arrange_chord(self._waves(duration, octave, type), norm=False, falloff=falloff)
            return chord_wave
        else:
            # delay arg has been given so we stagger the chord, making it an arpeggio instead:
            return self._melody_wave(duration=duration, octave=octave, delay=delay, type=type, falloff=falloff)

    def _melody_wave(self, duration, octave, delay, type='KS', falloff=True):
        from .audio import arrange_melody
        from .chords import most_likely_chord
        # log(f' synthesising arpeggio: {(most_likely_chord(self)).name} in octave:{octave if octave is not None else "Default"} (w/ delay={delay})')
        log(f' synthesising arpeggio from notes: {self} in octave:{octave if octave is not None else "Default"} (w/ delay={delay})')
        melody_wave = arrange_melody(self._waves(duration, octave, type), delay=delay, norm=False, falloff=falloff)
        return melody_wave

    def play(self, delay=0.2, duration=3, octave=None, falloff=True, block=False, type='KS', **kwargs):
        from .audio import play_wave
        if octave is None and isinstance(self[0], OctaveNote):
            # auto infer octave if this list starts with an octavenote:
            octave = self[0].octave

        if delay is not None:
            wave = self._melody_wave(duration=duration, octave=octave, delay=delay, type=type, falloff=falloff, **kwargs)
        else:
            wave = self._chord_wave(duration=duration, octave=octave, type=type, falloff=falloff, **kwargs)
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

# quality-of-life alias:
Notes = NoteList

# predefined Note objects:
A = Note('A')
Bb = Note('Bb')
B = Note('B')
C = Note('C')
Db = Note('Db')
D = Note('D')
Eb = Note('Eb')
E = Note('E')
F = Note('F')
Gb = Note('Gb')
G = Note('G')
Ab = Note('Ab')

# all chromatic pitch classes:
chromatic_scale = [C, Db, D, Eb, E, F, Gb, G, Ab, A, Bb, B]

# note cache by name for efficient init:
cached_notes = {n: Note(n, prefer_sharps=s) for n in parsing.common_note_names for s in [None, False, True]}
cached_notes.update({p : Note(position=p, prefer_sharps=s) for p in range(12) for s in [None, False, True]})

# relative minors/majors of all chromatic notes:
relative_minors = {c.name : (c - 3).name for c in chromatic_scale}
relative_minors.update({c.sharp_name: (c-3).sharp_name for c in chromatic_scale})
relative_minors.update({c.flat_name: (c-3).flat_name for c in chromatic_scale})

relative_majors = {value:key for key,value in relative_minors.items()}

# some chord/key tonics correspond to a preference for sharps or flats:
sharp_tonic_names = ['G', 'D', 'A', 'E', 'B']
flat_tonic_names = ['F', 'Bb', 'Eb', 'Ab', 'Db']
neutral_tonic_names = ['C', 'Gb'] # no sharp/flat preference, fall back on default

sharp_major_tonics = [Note(t, prefer_sharps=True) for t in sharp_tonic_names]
flat_major_tonics = [Note(t, prefer_sharps=False) for t in flat_tonic_names]
neutral_major_tonics = [Note(t) for t in neutral_tonic_names]
major_tonics = sorted(sharp_major_tonics + flat_major_tonics + neutral_major_tonics)

sharp_minor_tonics = [Note(relative_minors[t], prefer_sharps=True) for t in sharp_tonic_names]
flat_minor_tonics = [Note(relative_minors[t], prefer_sharps=False) for t in flat_tonic_names]
neutral_minor_tonics = [Note(relative_minors[t]) for t in neutral_tonic_names]
minor_tonics = sorted(sharp_minor_tonics + flat_minor_tonics + neutral_minor_tonics)

### TBI: improved recognition of double-sharp and double-flat notes for exotic keys?
