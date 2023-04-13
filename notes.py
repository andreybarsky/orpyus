# python library for handling musical notes, intervals, and chords

from intervals import Interval, IntervalList
import parsing
# from parsing import parsing.note_positions, preferred_note_names, parse_octavenote_name, is_flat, is_sharp, is_valid_note_name, parse_out_note_names
import conversion as conv

from util import log, test, rotate_list

import math
import pdb

### TBI: enharmonic equivalence operator? &? ^?


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
    def __init__(self, name=None, position=None, prefer_sharps=None, case_sensitive=True):
        # set main object attributes from init args:
        self.name, self.position, self.prefer_sharps = self._parse_input(name, position, prefer_sharps, case_sensitive)

        # string denoting pitch class: ('C#', 'Db', 'E', etc.)
        self.chroma = self.name # these two are the same for Note class, but may be different for OctaveNote subclass

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

    ## private utility functions:
    def _set_sharp_preference(self, prefer_sharps):
        """modify sharp preference in place"""
        self.prefer_sharps = prefer_sharps
        self.name = preferred_name(self.position, prefer_sharps=self.prefer_sharps)

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
        if 'other' is another Note, return the unsigned, symmetric interval distance between them,
        with other as the root. i.e. how many steps LEFT do you have to go to find other?"""

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
        return OctaveNote(f'{self.chroma}{int(octave)}')

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

        if isinstance(other, str) and parsing.is_valid_note_name(other):
            # cast to Note if possible
            other = Note(other)
        if isinstance(other, Note):
            return self.position == other.position
        # elif isinstance(other, OctaveNote):
        #     return self == other.note
        else:
            raise TypeError('Notes can only be compared to other Notes')

    def __hash__(self):
        """note and octavenote hash-equivalence is based on position alone, not value"""
        return hash(f'Note:{self.position}')

    def __str__(self):
        # e.g. is of form: '♩C#'
        return f'♩{self.name}'

    def __repr__(self):
        return str(self)

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
        self.chroma, self.value, self.pitch = self._parse_input(name, value, pitch, prefer_sharps)
        # compute octave, position, and name:
        self.octave, self.position = conv.oct_pos(self.value)
        self.name = f'{self.chroma}{self.octave}'

        self.prefer_sharps = prefer_sharps

    #### main input/arg-parsing private method:
    @staticmethod
    def _parse_input(name, value, pitch, prefer_sharps):
        """parses name, value, pitch input args (and sharp preference)
        returns correct chroma, value, and pitch"""
        # check that exactly one of our input args has been provided:
        assert ((name is not None) + (value is not None) + (pitch is not None) == 1), "Argument to init must include exactly one of: name, value, or pitch"

        # accept OctaveNote as input, instantiate a new one with the same properties:
        if isinstance(name, OctaveNote):
            return name.chroma, name.value, name.pitch
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
            log(f'Initialising OctaveNote with name: {name}')
            chroma, octave = parsing.parse_octavenote_name(name)
            position = parsing.note_positions[chroma]
            value = conv.oct_pos_to_value(octave, position)
            pitch = conv.value_to_pitch(value)
        if value is not None:
            log(f'Initialising OctaveNote with value: {value}')
            value = value
            octave, position = conv.oct_pos(value)
            chroma = preferred_name(position, prefer_sharps=prefer_sharps)
            pitch = conv.value_to_pitch(value)
        if pitch is not None:
            log(f'Initialising OctaveNote with pitch: {pitch}')
            pitch = float(pitch)
            assert pitch > 0, "Pitch must be greater than 0"
            value = conv.pitch_to_value(pitch, nearest=True)
            octave, position = conv.oct_pos(value)
            chroma = preferred_name(position, prefer_sharps=prefer_sharps)
        return chroma, value, pitch

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

    def __eq__(self, other):
        """Enharmonic equivlence comparison: Compares with another Note
        and returns True if both have the same position, but disregards note value.

        (if OctaveNote value comparison is needed, you should compare OctaveNote.value directly)
        """

        assert isinstance(other, Note), "OctaveNotes can only be enharmonic to other notes"
        return self.position == other.position

    def __hash__(self):
        """note and octavenote hash-equivalence is based on position alone, not value"""
        return hash(f'Note:{self.position}')

    def __str__(self):
        """Returns a pretty version of this OctaveNote's name,
        which includes its chroma as well as its octave."""
        return f'♪{self.name}'

    def __repr__(self):
        return str(self)

    #### useful public methods:

    ## Note parent class constructor
    @property
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

    def next(self, chroma):
        """returns an OctaveNote object of a specified chroma
        that is the next highest one after self"""
        candidates = OctaveNote(f'{chroma}{self.octave}'), OctaveNote(f'{chroma}{self.octave+1}')
        low_cand, high_cand = candidates
        if low_cand > self:
            return low_cand
        else:
            return high_cand

    def _wave(self, duration, type='KS', falloff=False):
        """Outputs a sine wave corresponding to this note,
        by default with exponential volume increase and falloff"""
        from audio import synth_wave
        # wave = sine_wave(freq=self.pitch, duration=duration)
        # use karplus-strong wave table synthesis for guitar-string timbre:
        wave = synth_wave(freq=self.pitch, duration=duration, type=type, falloff=falloff)
        return wave

    def play(self, duration=2, falloff=True, block=False):
        from audio import play_wave
        # return self[4].play(duration=duration, falloff=falloff)
        wave = self._wave(duration=duration, falloff=falloff)
        play_wave(wave, block=block)




class NoteList(list):
    """List subclass that is instantianted with an iterable of Note-like objects and forces them all to Note type"""
    def __init__(self, *items):
        if len(items) == 1:
            arg = items[0]

            # if we have been passed a single string as arg, parse it out as a series of notes:
            if isinstance(arg, str):
                arg = parsing.parse_out_note_names(arg)

            # now either way we should have an iterable of note-likes:
            try:
                note_items = self._cast_notes(arg)
            except:
                raise Exception(f'Could not parse NoteList input as a series of notes: {arg}')

        else:
            # we've been passed a series of items that we can unpack
            note_items = self._cast_notes(items)

        super().__init__(note_items)

    @staticmethod
    def _cast_notes(items):
        note_items = []
        for item in items:
            if isinstance(item, Note):
                # add note
                note_items.append(item)
            elif parsing.is_valid_note_name(item):
                # cast string to note
                note_items.append(Note(item))
            elif item[-1].isdigit():
                # cast string to octavenote
                note_items.append(OctaveNote(item))
            else:
                raise Exception('NoteList can only be initialised with Notes, or objects that cast to Notes')
        return note_items

    def __repr__(self):
        # return f'𝄃{super().__repr__()}𝄂'
        return f'𝄃{", ".join([str(n) for n in self])} 𝄂'

    def append(self, other):
        """Cast any appendices to Notes"""
        self.append(Note(other))

    def extend(self, other):
        """Cast any extensions to Notes"""
        self.extend([Note(n) for n in other])

    def __add__(self, other):
        if isinstance(other, (int, Interval)):
            return NoteList([n + other for n in self])
        elif isinstance(other, (list, tuple)):
            assert len(self) == len(other), "Can only add NoteLists with scalars or with iterables of equal length"
            assert not isinstance(other, NoteList), "NoteLists cannot be added to NoteLists"
            # return a NoteList, since nothing but Intervals can be added to Notes, and the result is always a new Note
            return NoteList([i + j for i,j in zip(self, other)])
        else:
            raise Exception(f"Can't add NoteList with {type(other)}")

    def __sub__(self, other):
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

    def unique(self):
        """returns a new NoteList, where repeated notes are dropped after the first"""
        unique_notes = []
        unique_notes_set = set() # for efficiency
        for n in self:
             if n not in unique_notes_set:
                 unique_notes.append(n)
                 unique_notes_set.add(n)
        return NoteList(unique_notes)

    def __hash__(self):
        """NoteLists hash as tuples for the purposes of chord/key reidentification"""
        return hash(tuple(self))

    def rotate(self, num_places):
        """returns the rotated NoteList that begins num_steps up
        from the beginning of this one. used for inversions,
        i.e. the 2nd inversion of [0,1,2] is [1,2,0], (a rotation of 1 place in this case)
        and for modes, which are rotations of scales. """

        # rotated_start_place = num_places
        # rotated_idxs = [(rotated_start_place + i) % len(self) for i in range(len(self))]
        # rotated_lst= [self[i] for i in rotated_idxs]
        # return NoteList(rotated_lst)

        return NoteList(rotate_list(self, num_places))

    def ascending_intervals(self):
        """sorts notes into ascending order from root (which is first note)"""
        # wrap around first octave and calculate intervals from root:
        octaved_notes = self.force_octave(1)
        root = octaved_notes[0]
        return IntervalList([o - root for o in octaved_notes])

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
                start_octave = 4
                auto_octave = True
                # cast abstract first note to octavenote:
                octavenotes.append(self[0][start_octave])
                # auto_octave will let us adjust pitch down later
        else:
            # cast abstract first note to octavenote:
            if not isinstance(self[0], OctaveNote):
                octavenotes.append(self[0][start_octave])
            else:
                # overwrite octave of existing octavenote:
                octavenotes.append((self[0].note)[start_octave])

        for note in self[1:]:
            if isinstance(note, OctaveNote):
                octavenotes.append(note)
            else:
                # append the next ascending OctaveNote of that chroma:
                octavenotes.append(octavenotes[-1].next(note.chroma))

        if (auto_octave) and (octavenotes[-1].octave > max_octave):
            # keep the chord below c5 if it's ended up too high:
            octave_shift = wave_notes[-1] - max_octave
            if octavenotes[0] - (12*octave_shift) < min_octave:
                raise ValueError(f"NoteList's notes span too great of a pitch range: {octave_shift} octaves exceeds min={min_octave} and max={max_octave}")

            octavenotes = [n - (12*octave_shift) for n in wave_notes]

        return octavenotes

    def matching_chords(self, *args, **kwargs):
        """wrapper for chords.matching_chords function: displays or returns
        a listing of the possible chords that fit these (unordered) notes"""
        import chords
        return chords.matching_chords(self, *args, **kwargs)

    def most_likely_chord(self, *args, **kwargs):
        import chords
        return chords.most_likely_chord(self, *args, **kwargs)

    def _waves(self, duration, octave, type, falloff=False):
        wave_notes = self.force_octave(start_octave=octave)
        print(f'  -synthesising notes: {wave_notes}')
        waves = [n._wave(duration=duration, type=type, falloff=falloff) for n in wave_notes]
        return waves

    def _chord_wave(self, duration, octave, delay=None, type='KS', falloff=True):
        from audio import arrange_chord
        from chords import most_likely_chord
        if delay is None:
            print(f' synthesising chord: {(most_likely_chord(self)).name} in octave {octave}')
            chord_wave = arrange_chord(self._waves(duration, octave, type), norm=False, falloff=falloff)
            return chord_wave
        else:
            # delay arg has been given so we stagger the chord, making it an arpeggio instead:
            return self._melody_wave(duration=duration, octave=octave, delay=delay, type=type, falloff=falloff)

    def _melody_wave(self, duration, octave, delay, type='KS', falloff=True):
        from audio import arrange_melody
        from chords import most_likely_chord
        print(f' synthesising arpeggio: {(most_likely_chord(self)).name} in octave:{octave if octave is not None else "Default"} (w/ delay={delay})')
        melody_wave = arrange_melody(self._waves(duration, octave, type), delay=delay, norm=False, falloff=falloff)
        return melody_wave

    def play(self, delay=None, duration=3, octave=None, falloff=True, block=False, type='KS', **kwargs):
        from audio import play_wave
        if delay is not None:
            wave = self._melody_wave(duration=duration, octave=octave, delay=delay, type=type, falloff=falloff, **kwargs)
        else:
            wave = self._chord_wave(duration=duration, octave=octave, type=type, falloff=falloff, **kwargs)
        play_wave(wave, block=block)

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


def unit_test():
    ### magic method tests:
    # Notes:
    test(C+2, D)
    test(D-2, C)
    test(D-C, 2)
    test(C+Interval(4), E)

    # OctaveNotes:
    test(OctaveNote('C4')+15, OctaveNote('Eb5'))

    # NoteList:
    test(NoteList('CEG'), NoteList(['C', 'E', 'G']))
    test(NoteList('CEG'), NoteList('C', 'E', 'G'))

    nl = NoteList('CEG')

    # test double sharps and double flats:

    test(Note('Ebb'), Note('C𝄪'))
    test(Note('E𝄫'), Note('C##'))

    import chords
    # test matching chords:
    test(NoteList('CEG').most_likely_chord()[0], chord.Chord('CEG'))

if __name__ == '__main__':
    unit_test()
