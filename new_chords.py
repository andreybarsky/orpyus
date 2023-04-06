# new chord class with explicit factor recognition and compositional name generation/recognition

import notes as notes
from notes import Note, NoteList
from intervals import degree_names
from util import log, test, precision_recall, rotate_list
from parsing import valid_note_names, is_valid_note_name, parse_out_note_names
from collections import defaultdict
from qualities import Quality, major_offsets, perfect_offsets
from copy import deepcopy

import pdb

# a Chord is identified by its Root, its Factors, and its Inversion
# given these, we can define its Quality, which is maj/min/aug/dim

# we assume a Chord is a major triad by default,
# and then modify it with any number of Qualifiers,
# which include things like: minor, maj7, sus4, add9, etc.

# every chord has a Root
# and a Bass, which is the same as the Root for non-inverted chords
# but can be otherwise for inversions.


# a chord's factors look like this:
major_triad = ChordFactors({1: 0, 3: 0, 5: 0})
# meaning: default intervals of 1st, 3rd, and 5th degrees

class ChordFactors(dict):
    """a class representing the factors of an AbstractChord, as a dict which has:
        keys: chord degrees (1 representing the root, 5 representing the fifth, etc.)
        values: semitone offsets from default degree intervals.
            e.g. the fifth degree is 7 semitones by default, so {5: -1} implies
            a fifth that is diminished (-1 from perfect), i.e. 6 semitones from root.
        qualifiers: a list of Qualifier objects that have been applied to this object"""
    def __init__(self, *args, qualifiers=None, **kwargs):
        super().__init__(self, *args, **kwargs)
        # # sanity check:
        # for k, v in self.items():
        #     assert isinstance(k, int) and (k >= 1)
        #     assert isinstance(v, int) and (-2 <= v <= 2)
        if qualifiers is None:
            self.qualifiers = []
        else:
            self.qualifiers = qualifiers

    @property
    def degrees(self):
        return list(self.keys())

    @property
    def intervals(self):
        return list(self.values())

    def __add__(self, other):
        """modifies these factors by the alterations in a ChordQualifier"""
        assert isinstance(other, ChordQualifier)
        other.apply(self)
        # ensure that we keep ourselves sorted:
        sorted_keys = sorted(list(self.keys()))
        return ChordFactors({k: self[k] for k in sorted_keys}, qualifiers = self.qualifiers+[other])





class AbstractChord:
    """a hypothetical chord not built on any specific note but having all the qualifiers that a chord would,
    whose members are Intervals.
    an AbstractChord is fully identified by its Factors and its Inversion."""
    def __init__(self, *qualifiers, factors=None, intervals=None, inversion=None, **qualifier_kwargs):
        pass


class Chord(AbstractChord):
    """a Chord built on a note of the chromatic scale, but in no particular octave,
    whose members are Notes.
    a Chord is fully identified by its Root, its Factors, and its Inversion"""
    def __init__(self, *name, notes=None, factors=None, intervals=None, bass=None, inversion=None, ):
        """The first arg, *name, is unpacked into an iterable that we assume is either:
          length 1: the whole chord name (which we then parse)
          length 2+: the chord's root, followed by a series of ChordQualifiers (or names of ChordQualifiers)
          length 0: unspecified, in which case we build the chord from one of its keyword args instead (notes, factors, intervals)

        one of: notes, factors, or intervals can be specified if no positional args are given for *name.
        finally, one of: bass or inversion can be specified.
          bass refers to a specific bass note, inversion refers to 1st/2nd/3rd inversion etc.
          if neither are given, this is just a chord in root position."""


class ChordVoicing(Chord):
    """a Chord built on a specific note of a specific pitch, whose members are OctaveNotes.
    unlike its parent classes, a ChordVoicing can have repeats of the same Note at multiple pitches"""
    def __init__(self, notes=None, octave=None, factors=None, intervals=None, bass=None, inversion=None, ):

major_triad = {1:0, 3:0, 5:0}
minor_triad = {1:0, 3:-1, 5:0}

def _parse_chord_name():
    # the hard one: given a chord name,
    pass
