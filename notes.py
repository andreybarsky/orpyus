# python library for handling musical notes, intervals, and chords

from muse.intervals import Interval
from muse.parsing import note_names, parse_octavenote_name, is_flat, is_sharp, is_valid_note_name
import muse.conversion as conv

from muse.util import log, test

import math
import pdb

# relative values (positions within scale) with respect to C major, starting with 0=C:
note_positions = {note_name:i for i, note_name in enumerate(note_names['generic'])}
note_positions.update({note_name:i for i, note_name in enumerate(note_names['flat'])})
note_positions.update({note_name:i for i, note_name in enumerate(note_names['sharp'])})

note_positions.update({note_name:i for i, note_name in enumerate(note_names['flat_unicode'])})
note_positions.update({note_name:i for i, note_name in enumerate(note_names['sharp_unicode'])})
note_positions.update({note_name:i for i, note_name in enumerate(note_names['natural_unicode'])})

# get note name string from position in octave:
def accidental_note_name(pos, prefer_sharps=False):
    """Gets the note name for a specific position according to preferred sharp/flat notation,
    or just the natural note name if a a white note"""
    # if we've accidentally been given an Interval object for position, we quietly parse it:
    if isinstance(pos, Interval):
        pos = pos.value
    name = note_names['flat'][pos] if not prefer_sharps else note_names['sharp'][pos]
    return name

#
# #### string-specific parsing functions
# #### (all moved to parsing.py)
#
# def is_valid_note_name(name: str):
#     """returns True if string can be cast to a Note,
#     and False if it cannot (in which case it must be something else, like a Note)"""
#     if not isinstance(name, str):
#         return False
#     # force to upper case, in case we've been given e.g. lowercase 'c', still valid
#     if len(name) == 1:
#         return name.upper() in valid_note_names
#     elif len(name) == 2: # force to upper+lower case, in case we've been given e.g. 'eb', still valid
#         name2 = name[0].upper() + name[1].lower()
#         return name2 in valid_note_names
#     else:
#         return False
#
# def parse_out_notes(note_string):
#     """for some string of valid note letters, of undetermined length,
#     such as e.g.: 'CAC#ADbGbE', parse out the individual notes and return
#     a list of corresponding Note objects"""
#
#     first_note_fragment = note_string[:2]
#     if is_accidental(first_note_fragment[-1]):
#         letter, accidental = first_note_fragment
#         first_note = Note(letter + parse_accidental(accidental))
#         next_idx = 2
#     else:
#         first_note = Note(first_note_fragment[0])
#         next_idx = 1
#
#     assert is_valid_note_name(first_note), f'{first_note} is not a valid note name'
#     note_list = [first_note]
#
#     while next_idx < len(note_string):
#         next_note_fragment = note_string[next_idx : next_idx+2]
#         if is_accidental(next_note_fragment[-1]):
#             letter, accidental = next_note_fragment
#             next_note = Note(letter + parse_accidental(accidental))
#             next_idx += 2
#         else:
#             next_note = Note(next_note_fragment[0])
#             next_idx += 1
#         note_list.append(next_note)
#     return note_list
#
# # string checking/cleaning for accidental unicode characters:
# def is_sharp(char):
#     return (char in ['#', '♯'])
# def is_flat(char):
#     return (char in ['b', '♭'])
# def is_accidental(char):
#     return (char in ['#', 'b', '♯', '♭'])
# def parse_accidental(acc):
#     """reads what might be unicode accidentals and casts to '#' or 'b' if required"""
#     assert len(acc) == 1
#     if acc == '♭':
#         return 'b'
#     elif acc == '♯':
#         return '#'
#     elif acc in ['#', 'b']:
#         return acc
#     else:
#         return None
#         # raise ValueError(f'{acc} is not an accidental')


class Note:
    """a note quality not associated with a specific note inside an octave, such as C or D#"""
    def __init__(self, name=None, position=None, prefer_sharps=None):
        # set main object attributes from init args:
        self.name, self.position, self.prefer_sharps = self._parse_input(name, position, prefer_sharps)

        # string denoting pitch class: ('C#', 'Db', 'E', etc.)
        self.chroma = self.name # these two are the same for Note class, but may be different for OctaveNote subclass

        self.sharp_name = accidental_note_name(self.position, prefer_sharps=True)
        self.flat_name = accidental_note_name(self.position, prefer_sharps=False)

    #### main input/arg-parsing private method:
    @staticmethod
    def _parse_input(name, position, prefer_sharps):
        # check that exactly one has been provided:
        assert ((name is not None) + (position is not None) == 1), "Argument to init must include exactly one of: name or position"
        if isinstance(name, int):
            # auto detect initialisation with note value as first arg, silently initialise
            # log(f'Name given but int detected, so initialising instead by value: {name}')
            position = name
            name = None

        if name is not None:
            if not isinstance(name, str):
                raise TypeError(f'expected str or int but received {type(name)} to initialise Note object')
            # log(f'Initialising Note with name: {name}')

            # detect if sharp or flat:
            if prefer_sharps is None:
                # if no preference is set then we infer from the name argument supplied
                if is_sharp(name[-1]):
                    prefer_sharps = True
                elif len(name) == 2 and is_flat(name[-1]):
                    prefer_sharps = False
                else: # fallback on global default
                    prefer_sharps = False
            else:
                prefer_sharps = prefer_sharps

            # cast to correct case:
            if len(name) == 1:
                name = name.upper()
            elif len(name) == 2:
                name = name[0].upper() + name[1].lower()
            else:
                raise ValueError(f'{name} is too long to be a valid Note')

            position = note_positions[name]
            name = accidental_note_name(position, prefer_sharps=prefer_sharps)
        elif position is not None:
            if prefer_sharps is None:
                prefer_sharps = False # default

            # log(f'Initialising Note with position: {position}')
            name = accidental_note_name(position, prefer_sharps=prefer_sharps)
        return name, position, prefer_sharps

    ## private utility functions:
    def _set_sharp_preference(self, prefer_sharps):
        """modify sharp preference in place"""
        self.prefer_sharps = prefer_sharps
        self.name = accidental_note_name(self.position, prefer_sharps=self.prefer_sharps)

    #### magic methods and note constructors:
    def __add__(self, interval):
        """returns a new Note based on shifting up or down by some number of semitones"""
        # assert isinstance(interval, (int, Interval)), "Only an integer or Interval can be added to a Note"
        if isinstance(interval, Interval):
            interval = interval.value  # cast to int

        new_pos = (self.position + interval) % 12
        new_note = Note(position = new_pos, prefer_sharps = self.prefer_sharps) # inherit sharpness from self
        # log(f'Adding interval ({interval}) to self ({self}) to produce Note: {chrm}')
        return new_note

    def __sub__(self, other):
        """if 'other' is an integer, returns a new Note that is shifted down by that many semitones.
        if 'other' is another Note, return the (unsigned) interval distance between them, with other as the root."""

        if isinstance(other, (int, Interval)): # construct Note
            new_pos = (self.position - other) % 12
            new_note = Note(position = new_pos, prefer_sharps = self.prefer_sharps)
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
        return OctaveNote(f'{self.name}{int(octave)}')

    # quick accessor for in_octave method defined above:
    def __getitem__(self, octave):
        """returns OctaveNote in the specified octave"""
        assert isinstance(octave, int)
        return self.in_octave(octave)

    ## comparison operators:
    def __eq__(self, other):
        """Enharmonic equality comparison between Notes, returns True if
        they have the same chroma (by comparing Note.position).

        note that this does NOT compare the value of OctaveNotes;
        C4 is equal to C5 because they are enharmonic.
        to compare OctaveNote value, use C4.value == C5.value explicitly"""

        if isinstance(other, str) and is_valid_note_name(other):
            # cast to Note if possible
            other = Note(other)
        if isinstance(other, Note):
            return self.position == other.position
        # elif isinstance(other, OctaveNote):
        #     return self == other.note
        else:
            raise TypeError('Notes can only be compared to other Notes')

    def __hash__(self):
        """unlike __eq__ which compares enharmonic equivalence,
        the __hash__ method DOES take note value into account"""
        return hash(str(self))

    def __str__(self):
        # specific_name = accidental_note_name(self.position, prefer_sharps=self.prefer_sharps)
        return f'♩{self.name}'

    def __repr__(self):
        return str(self)

    #### useful public methods:
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
        print(self.properties())

    ## chord constructors:
    def chord(self, arg='major'):
        """instantiate Chord object by parsing either:
        1) a string denoting a Chord quality, like 'major' or 'minor' or 'dom7'
        2) an iterable of semitone intervals relative to this Note as root
        in the exact same way as Chord.__init__ (we pass this arg there directly)"""

        from chords import Chord
        return Chord(self, arg)
        # # case 1: string denoting chord quality
        # if isinstance(arg, str):
        #     quality = arg
        #     return chords.Chord(self.name, quality)
        # # case 2: iterable of semitone intervals
        # else:
        #     assert isinstance(arg, (list, tuple)), "Note.chord method expects a string or iterable as its one input arg"
        #     # cast ints to intervals if needed:
        #     intervals = [i if isinstance(i, Interval) else Interval(i) for i in arg]
        #     return chords.Chord(self.name, intervals)

    # quick accessor for chord method defined above:
    def __call__(self, arg='major'):
        """returns a Chord based on this Note as tonic"""
        return self.chord(arg)





#### subclass for specific notes on keyboard
class OctaveNote(Note):
    """a note in a specific octave, rounded to twelve-tone equal temperament, such as C4 or D#2.

    this class functions as a Note in every respect,
    except it also has .octave, .value, .pitch attrs defined on top,
    and its addition/subtraction operators respect octave/value as well as position.
    """

    def __init__(self, name=None, value=None, pitch=None, prefer_sharps=None):
        """initialises a Note object from one of the following:
        name: a string denoting a specific note, like 'C#3', or a pitch class, like 'C#'
        value: an integer denoting the note's position on an 88-note piano keyboard,
                where A0 is 1, C4 is 40, and C8 is 88. (the core internal representation)
        pitch: an integer or float corresponding to the note's frequency in Hz,
                where the reference note A4 is 440 Hz"""

        # set main object attributes from init args:
        self.chroma, self.value, self.pitch = self._parse_input(name, value, pitch, prefer_sharps)
        # compute octave, position, and name:
        self.octave, self.position = conv.oct_pos(self.value)
        self.name = f'{self.chroma}{self.octave}'

        self.prefer_sharps = prefer_sharps

    #### main input/arg-parsing private method:
    @staticmethod
    def _parse_input(name, value, pitch, prefer_sharps):
        """parses name, value, pitch input args (and sharp preference)
        returns correct name, value, pitch, octve, and chroma"""
        # check that exactly one of our input args has been provided:
        assert ((name is not None) + (value is not None) + (pitch is not None) == 1), "Argument to init must include exactly one of: name, value, or pitch"

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
            log(f'Initialising OctaveNote with name: {name}')
            chroma, octave = parse_octavenote_name(name)
            position = note_positions[chroma]
            value = conv.oct_pos_to_value(octave, position)
            pitch = conv.value_to_pitch(value)
        if value is not None:
            log(f'Initialising OctaveNote with value: {value}')
            value = value
            octave, position = conv.oct_pos(value)
            chroma = accidental_note_name(position, prefer_sharps=prefer_sharps)
            pitch = conv.value_to_pitch(value)
        if pitch is not None:
            log(f'Initialising OctaveNote with pitch: {pitch}')
            pitch = pitch
            value = conv.pitch_to_value(pitch, nearest=True)
            octave, position = conv.oct_pos(value)
            chroma = accidental_note_name(position, prefer_sharps=prefer_sharps)
        return chroma, value, pitch

    ## private utility function:
    def _set_sharp_preference(self, preference):
        """modify sharp preference in place"""
        self.prefer_sharps = preference
        self.chroma = accidental_note_name(self.position, prefer_sharps=self.prefer_sharps)
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

    def __eq__(self, other):
        """Enharmonic equivlence comparison: Compares with another Note
        and returns True if both have the same position, but disregards note value.

        (if OctaveNote value comparison is needed, you should compare OctaveNote.value directly)
        """

        assert isinstance(other, Note), "OctaveNotes can only be enharmonic to other notes"
        return self.position == other.position

    def __str__(self):
        """Returns a pretty version of this OctaveNote's name,
        which includes its chroma as well as its octave."""
        return f'♪{self.name}'

    def __repr__(self):
        return str(self)

    #### useful public methods:

    ## Note parent class constructor
    def note(self):
        """returns the parent class Note object
        associated with this OctaveNote"""
        return Note(self.chroma)

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

# case by case tests:
if __name__ == '__main__':
    ### magic method tests:
    # Notes:

    test(C+2, D)
    test(D-2, C)
    test(D-C, 2)
    test(C+Interval(4), E)

    # OctaveNotes:
    test(OctaveNote('C4')+15, OctaveNote('Eb5'))
