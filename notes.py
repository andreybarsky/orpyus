# python library for handling musical notes, intervals, and chords

from intervals import Interval, M3

from util import log, test
import math
import pdb

PREFER_SHARPS = True


# note name lookups
note_names = ['C', 'C# / Db', 'D', 'D# / Eb', 'E', 'F', 'F# / Gb', 'G', 'G# / Ab', 'A', 'A# / Bb', 'B', ]
is_blacknote = [False, True, False, True, False, False, True, False, True, False, True, False]
note_names_flat = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
note_names_sharp = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
valid_note_names = set(note_names + note_names_flat + note_names_sharp)

# relative values (positions within scale) with respect to C major, starting with 0=C:
note_positions = {note_name:i for i, note_name in enumerate(note_names)}
note_positions.update({note_name:i for i, note_name in enumerate(note_names_flat)})
note_positions.update({note_name:i for i, note_name in enumerate(note_names_sharp)})
# detect unicode notes too:
note_names_flat_unicode = [n.replace('b', '♭') for n in note_names_flat]
note_names_sharp_unicode = [n.replace('#', '♯') for n in note_names_sharp]
note_names_natural_unicode = [n + '♮' if len(n)== 1 else n for n in note_names]
note_positions.update({note_name:i for i, note_name in enumerate(note_names_flat_unicode)})
note_positions.update({note_name:i for i, note_name in enumerate(note_names_sharp_unicode)})
note_positions.update({note_name:i for i, note_name in enumerate(note_names_natural_unicode)})

# get note name string from position in octave:
def specific_note_name(pos, prefer_sharps=PREFER_SHARPS):
    name = note_names_sharp[pos] if prefer_sharps else note_names_flat[pos]
    return name

#### name/value/pitch conversion functions:

# get octave and position from note value:
def oct_pos(value): # equivalent to div_mod
    oct = math.floor((value+8) / 12)
    pos = (value - 4) % 12
    return oct, pos

# get note value from octave and position
def location(oct, pos):
    value = ((12*oct)-8) + pos
    return value

### name-value conversion

def value_to_name(value, prefer_sharps=PREFER_SHARPS):
    oct, pos = oct_pos(value)
    name = specific_note_name(pos, prefer_sharps=prefer_sharps)
    note_name = f'{name}{oct}'
    return note_name

# string checking/cleaning for accidental unicode characters:
def is_sharp(char):
    return (char in ['#', '♯'])
def is_flat(char):
    return (char in ['b', '♭'])
def is_accidental(char):
    return (char in ['#', 'b', '♯', '♭'])
def parse_accidental(acc):
    """detects unicode accidentals and casts to '#' or 'b' if needed"""
    assert len(acc) == 1
    if acc == '♭':
        return 'b'
    elif acc == '♯':
        return '#'
    elif acc in ['#', 'b']:
        return acc
    else:
        raise ValueError(f'{acc} is not an accidental')

def parse_note_name(name):
    """Takes the name of a note as a string,
    for example 'C4' or 'A#3' or 'Gb1',
    and extracts the note and octave components."""
    note_letter = name[0].upper()
    if (len(name) > 1) and is_accidental(name[1]): # check for accidental
        # check string validity:
        accidental = parse_accidental(name[1])
        note_name = note_letter + accidental
        assert note_name in valid_note_names, f"Invalid note name: {note_letter}"

        if len(name) == 2: # default to 4th octave if not specified
            octave = 4
        elif len(name) == 3:
            octave = int(name[2])
        else:
            raise ValueError(f'Provided note name is too long: {name}')
    else: # assume natural note
        # check string validity:
        assert note_letter in valid_note_names, f"Invalid note name: {note_letter}"
        note_name = note_letter

        if len(name) == 1: # default to 4th octave if not specified
            octave = 4
        elif len(name) == 2:
            octave = int(name[1])
        else:
            raise ValueError(f'Provided note name is too long: {name}')
    return note_name, octave

def name_to_value(name):
    # get pitch class and octave
    note_name, oct = parse_note_name(name)
    # convert pitch class to position within octave:
    pos = note_positions[note_name]
    return location(oct, pos)
    # octave_value = (12*octave)-8
    # value = octave_value + note_name_value
    # return value

v2n = value_to_name
n2v = name_to_value


### pitch-value conversion

def pitch_to_value(pitch, nearest=True):
    """Given a pitch in Hz, returns the value of the corresponding piano key.
    If the pitch is not exact, will return the value of the *nearest* piano key
    instead, unless round is False, in which case will return a float of the hypothetical
    real-valued piano key corresponding to that pitch."""
    exact_key = 12 * math.log(pitch/440., 2) + 49
    if nearest:
        return round(exact_key)
    else:
        return exact_key

def value_to_pitch(value):
    """Given a piano key value (for an 88-note piano), return the corresponding
    pitch in Hz as a float."""
    pitch = 2 ** ((value-49)/12) * 440.
    return round(pitch, 2)

p2v = pitch_to_value
v2p = value_to_pitch

### pitch-name conversion
def pitch_to_name(pitch, round=True, prefer_sharps=True):
    val = pitch_to_value(pitch)
    return value_to_name(val, prefer_sharps=prefer_sharps)

def name_to_pitch(name):
    val = name_to_value(name)
    return value_to_pitch(val)

p2n = pitch_to_name
n2p = name_to_pitch


# polymorphic note getters:
def note_name(inp, prefer_sharps=True):
    ### parse input as either value or pitch, retrieve coresponding note name
    if type(inp) == int:
        return value_to_name(inp, prefer_sharps=prefer_sharps)
    elif type(inp) == float:
        return pitch_to_name(inp, prefer_sharps=prefer_sharps)
    elif type(inp) == str:
        # cast string to int then try again
        try:
            print(f'Casting {inp} to int and trying again')
            return note_name(int(inp), prefer_sharps=prefer_sharps)
        except:
            try:
                print(f'Casting {inp} to float and trying again')
                # cast to float then try again
                return note_name(float(inp), prefer_sharps=prefer_sharps)
            except:
                raise Exception('Invalid string input to note_name')

def note_value(inp):
    ### parse input as either name or pitch, retrieve corresponding note value
    if type(inp) == str:
        return name_to_value(inp)
    elif type(inp) in (tuple, list):
        # inverse oct-pos
        oct, pos = inp

    else:
        return pitch_to_value(inp)

def note_pitch(inp):
    ### parse input as either name or value, retrieve corresponding note pitch
    if type(inp) == str:
        return name_to_pitch(inp)
    else:
        return value_to_pitch(inp)




class Note:
    """a note quality not associated with a specific note inside an octave, such as C or D#"""
    def __init__(self, name=None, position=None, prefer_sharps=None):

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
                if is_sharp(name[-1]):
                    self.prefer_sharps = True
                elif len(name) == 2 and is_flat(name[-1]):
                    self.prefer_sharps = False
                else: # fallback on global default
                    self.prefer_sharps = PREFER_SHARPS
            else:
                self.prefer_sharps = prefer_sharps

            # force to correct case:
            if len(name) == 1:
                name = name.upper()
            elif len(name) == 2:
                name = name[0].upper() + name[1].lower()
            else:
                raise ValueError(f'{name} is too long to be a valid Note')

            self.position = note_positions[name]
            self.name = specific_note_name(self.position, prefer_sharps=self.prefer_sharps)
        elif position is not None:
            if prefer_sharps is None:
                self.prefer_sharps = PREFER_SHARPS
            else:
                self.prefer_sharps = prefer_sharps
            # log(f'Initialising Note with position: {position}')
            self.position = position
            self.name = specific_note_name(position, prefer_sharps=self.prefer_sharps)

        self.chroma = self.name # is the same for Note class, but may be different for OctaveNote subclass

        self.sharp_name = specific_note_name(self.position, prefer_sharps=True)
        self.flat_name = specific_note_name(self.position, prefer_sharps=False)

        # chord constructor method aliases:
        self.major = self.major_triad = self.major3 = self.maj3 = self.triad = self.maj
        self.minor = self.minor_triad = self.minor3 = self.min3 = self.min
        self.major7 = self.maj7
        self.minor7 = self.min7
        self.dominant7 = self.seventh = self.dom7

    def _set_sharp_preference(self, preference):
        """modify sharp preference in place"""
        self.prefer_sharps = preference
        self.name = specific_note_name(self.position, prefer_sharps=self.prefer_sharps)

    def properties(self):
        f"""Describe all the useful properties this Note has"""
        prop_str = """<{str(self)}
        name: {self.name}
        position: {self.position}
        sharp preference: {self.prefer_sharps}
        type: {type(self)}
        id: {id(self)}>"""
        return prop_str

    def summary(self):
        print(self.properties())


    # note constructors:

    def __add__(self, interval):
        """returns a new Note based on shifting up or down by some number of semitones"""
        assert isinstance(interval, (int, Interval)), "Only an integer or Interval can be added to a Note"

        new_pos = (self.position + interval) % 12
        chrm = Note(position = new_pos, prefer_sharps = self.prefer_sharps) # inherit sharpness from self
        # log(f'Adding interval ({interval}) to self ({self}) to produce Note: {chrm}')
        return chrm

    def __sub__(self, other):
        """if 'other' is an integer, returns a new Note that is shifted down by that many semitones.
        if 'other' is another Note, return the interval distance between them, with other as the root."""

        if isinstance(other, (int, Interval)): # construct Note
            new_pos = (self.position - other) % 12
            chrm = Note(position = new_pos, prefer_sharps = self.prefer_sharps)
            # log(f'Subtracting interval ({other}) from self ({self}) to produce Note: {chrm}')
            return chrm
        elif isinstance(other, Note):       # construct Interval
            distance = (self.position - other.position) % 12
            intrv = Interval(distance)
            # log(f'Subtracting root Note ({other}) from self ({self}) to produce Interval: {intrv}')
            return Interval(distance)
        else:
            raise Exception('Only integers, Intervals, and other Notes can be subtracted from a Note')

    def __call__(self, octave):
        """returns OctaveNote in the specified octave"""
        assert isinstance(octave, int)

        return self.in_octave(octave)

    def in_octave(self, octave=4):
        """instantiates an OctaveNote object corresponding to this Note played in a specific octave"""
        return OctaveNote(f'{self.name}{int(octave)}')

    ### chord constructors:

    def chord(self, *args):
        """instantiate Chord object by parsing either:
        1) a string denoting a Chord quality, like 'major' or 'minor' or 'dom7'
        2) a list of semitone intervals relative to this Note as root"""

        import chords
        # case 1:
        if len(args) == 1 and isinstance(args[0], str):
            quality = args[0]
            return chords.Chord(self.name, quality)

        # case 2:
        else:
            intervals = args
            # positions = [root] + [(self + interval).position for interval in intervals]
            return chords.Chord(self.name, intervals)

    def __mul__(self, other):
        """combine with one or more other Notes to create a Chord"""
        assert isinstance(other, Note), "Notes can only be combined with other Notes"
        other_position = other.position
        return self.chord(other.position)

    def maj(self):
        """returns the Chord of this note's major triad"""
        return self.chord(4, 7)

    def min(self):
        """returns the Chord of this note's minor triad"""
        return self.chord(3, 7)

    def fourth(self):
        return self.chord(5)

    def fifth(self):
        return self.chord(7)

    def maj7(self):
        return self.chord(4, 7, 11)

    def dom7(self):
        return self.chord(4, 7, 10)

    def min7(self):
        return self.chord(3, 7, 10)

    def sus2(self):
        return self.chord(2, 7)

    def sus4(self):
        return self.chord(5, 7)

    # comparison operators:
    def __eq__(self, other):
        if isinstance(other, str) and self.is_valid_note_name(other):
            # cast to Note if possible
            other = Note(other)
        if isinstance(other, Note):
            return self.position == other.position
        elif isinstance(other, OctaveNote):
            return self == other.note
        else:
            raise TypeError('Notes can only be compared to other Notes')

    def __hash__(self):
        return hash(str(self))

    def __str__(self):
        # specific_name = specific_note_name(self.position, prefer_sharps=self.prefer_sharps)
        return f'♩{self.name}'

    def __repr__(self):
        return str(self)


    # check if string is valid to be initialised as a note
    @staticmethod
    def is_valid_note_name(name: str):
        """returns True if string can be cast to a Note,
        and False if it cannot (in which case it must be something else, like a Note)"""
        if not isinstance(name, str):
            return False
        # force to upper case, in case we've been given e.g. lowercase 'c', still valid
        if len(name) == 1:
            return name.upper() in valid_note_names
        elif len(name) == 2: # force to upper+lower case, in case we've been given e.g. 'eb', still valid
            name2 = name[0].upper() + name[1].lower()
            return name2 in valid_note_names
        else:
            return False


class OctaveNote(Note):
    """a note in a specific octave, rounded to twelve-tone equal temperament, such as C4 or D#2"""

    def __init__(self, name=None, value=None, pitch=None):
        """initialises a Note object from one of the following:
        name: a string denoting a specific note, like 'C#3', or a pitch class, like 'C#'
        value: an integer denoting the note's position on an 88-note piano keyboard,
                where A0 is 1, C4 is 40, and C8 is 88. (the core internal representation)
        pitch: an integer or float corresponding to the note's frequency in Hz,
                where the reference note A4 is 440 Hz"""

        # check that exactly one has been provided:
        assert ((name is not None) + (value is not None) + (pitch is not None) == 1), "Argument to init must include exactly one of: name, value, or pitch"

        if type(name) == int:
            # auto detect initialisation with note value as first arg, silently initialise
            log(f'Name given to Note init but int detected, so initialising instead by value')
            value = name
            name = None
        elif type(name) == float:
            log(f'Name given to Note init but float detected, so initialising instead by pitch')
            pitch = name
            name = None

        # initialisation must define: octave, position, value, and pitch
        # anything that involves rendering of sharps or flats is NOT set at init

        if name is not None:
            log(f'Initialising Note with name: {name}')
            chroma, self.octave = parse_note_name(name)
            self.position = note_positions[chroma]
            self.value = location(self.octave, self.position)
            self.pitch = value_to_pitch(self.value)
            self.note = Note(chroma)

        if value is not None:
            log(f'Initialising with value: {value}')
            self.value = value
            self.octave, self.position = oct_pos(value)
            self.pitch = value_to_pitch(self.value)
            self.note = Note(self.position)

        if pitch is not None:
            log(f'Initialising with pitch: {pitch}')
            self.pitch = pitch
            self.value = pitch_to_value(pitch, nearest=True)
            self.octave, self.position = oct_pos(self.value)
            self.note = Note(self.position)

        ### now octave, position, value and pitch are defined
        self.chroma = self.note.name


    ### chord constructors:
    def chord(self, *intervals):
        import chords

        notes = [self.value] + [self + interval for interval in intervals]
        return chords.NoteSet(notes)


    def major_triad(self):
        """returns the NoteSet of this note's major triad"""
        return self.chord(4, 7)

    def minor_triad(self):
        return self.chord(3, 7)

    def maj7(self):
        return self.chord(4, 7, 11)


    ### operators & magic methods:

    def __add__(self, interval: int):
        """returns a new Note that is shifted up by some integer number of semitones."""
        assert isinstance(interval, (int, Interval)), "Only an integer interval can be added or subtracted to a note"
        return OctaveNote(value = self.value + interval)

    def __sub__(self, other):
        """if 'other' is an integer or Interval, returns a new Note that is shifted down by that many semitones.
        if 'other' is another Note, return the interval distance between them, with other as the root."""
        if isinstance(other, (int, Interval)):
            return OctaveNote(value = self.value - other)
        elif isinstance(other, OctaveNote):
            return Interval(self.value - other.value)
        else:
            raise Exception('Only integers and other Notes can be subtracted from a Note')

    def __ge__(self, other):
        assert isinstance(other, OctaveNote), "OctaveNotes can only be greater or less than other notes"
        return self.value >= other.value

    def __lt__(self, other):
        assert isinstance(other, OctaveNote), "OctaveNotes can only be greater or less than other notes"
        return self.value < other.value

    # note: octavenote equality compares value with other octavenotes, but position with base class Notes
    def __eq__(self, other):
        assert isinstance(other, Note), "OctaveNotes can only be equal to other notes"
        if isinstance(other, OctaveNote):
            return self.value == other.value
        elif isinstance(other, Note):
            return self.position == other.position

    def __str__(self):
        note_name = specific_note_name(self.position, prefer_sharps=PREFER_SHARPS)
        return f'♪{note_name}{self.octave}'

    def __repr__(self):
        return str(self)


# constants:

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
notes = [C, Db, D, Eb, E, F, Gb, G, Ab, A, Bb, B]
# their relative minors:
relative_minors = {c : (c - 3) for c in notes}
relative_minors.update({c.sharp_name: (c-3).sharp_name for c in notes})
relative_minors.update({c.flat_name: (c-3).flat_name for c in notes})

relative_majors = {value:key for key,value in relative_minors.items()}

# some notes (as chord/key tonics) correspond to a preference for sharps or flats:
# (though I think this applies to diatonic keys only?)
sharp_tonic_names = ['G', 'D', 'A', 'E', 'B']
flat_tonic_names = ['F', 'Bb', 'Eb', 'Ab', 'Db']
neutral_tonic_names = ['C', 'Gb'] # no sharp/flat preference, fall back on default

sharp_major_tonics = [Note(t) for t in sharp_tonic_names]
flat_major_tonics = [Note(t) for t in flat_tonic_names]
neutral_major_tonics = [Note(t) for t in neutral_tonic_names]

sharp_minor_tonics = [relative_minors[Note(t)] for t in sharp_tonic_names]
flat_minor_tonics = [relative_minors[Note(t)] for t in flat_tonic_names]
neutral_minor_tonics = [relative_minors[Note(t)] for t in neutral_tonic_names]


# case by case tests:
if __name__ == '__main__':

    ### name/value/pitch conversion tests:

    print('\n=== Value to name:\n')
    test(v2n(1), 'A0')
    test(v2n(13), 'A1')
    test(v2n(14), 'A#1')
    test(v2n(40), 'C4')

    print('\n=== Name to value:\n')
    test(n2v('A0'), 1)
    test(n2v('A#1'), 14)
    test(n2v('C4'), 40)
    test(n2v('D'), 42)

    print('\n=== Value to pitch:\n')
    test(v2p(49), 440.)
    test(v2p(40), 261.63)

    print('\n=== Pitch to value:\n')
    test(p2v(440), 49)
    test(p2v(261.63), 40)

    print('\n=== Polymorphisms:\n')
    test(note_name(40), 'C4')
    test(note_name(440.), 'A4')
    test(note_value('C4'), 40)
    test(note_value(440.), 49)
    test(note_pitch('C4'), 261.63)
    test(note_pitch(49), 440.)

    # magic method tests:
    # notes:

    test(C+2, D)
    test(D-2, C)
    test(D-C, 2)
    test(C+M3, E)

    # notes:
    ... # TBI
