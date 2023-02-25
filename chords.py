
import notes
from notes import Chroma, Note
from intervals import *
from collections import defaultdict

from util import log, test
import pdb





# all accepted aliases for chord names - common suffix is FIRST, this is the one chosen by automatic chord parsing
chord_names = defaultdict(lambda: [' (unknown chord)'],
    {(Maj3, Per5): ['', 'major', 'maj', 'major triad', 'M', 'Ma'],
    (Min3, Per5): ['m', 'minor', 'min', 'minor triad', '-'],
    (Per5, ): ['5', '5th', 'fifth'], # does octave belong here??

    # weird triads
    (Maj2, Per5): ['sus2', 'suspended 2nd', 'suspended second', 's2'],
    (Per4, Per5): ['sus4', 'suspended 4th', 'suspended fourth', 's4'],
    (Maj3, Aug5): ['+', 'augmented triad', 'augmented fifth', 'augmented 5th', 'aug'],
    (Min3, Dim5): ['dim', 'o', 'o', 'diminished', 'diminished triad', 'diminished fifth', 'diminished 5th'],

    # sixths
    (Maj3, Per5, Maj6): ['6', 'maj6', 'M6', 'major sixth', 'major 6th'],
    (Min3, Per5, Min6): ['m6', 'min6', 'minor sixth', 'minor 6th'],

    # sevenths
    (Maj3, Per5, Min7): ['7', 'dominant seventh', 'dominant 7th', 'dominant 7', 'dom7'],
    (Maj3, Per5, Maj7): ['maj7', 'major seventh', 'major 7th', 'major 7', 'M7', 'Δ7'],
    (Min3, Per5, Min7): ['m7', 'minor seventh', 'minor 7th', 'minor 7', 'min7', '-7'],
    (Min3, Dim5, Min7): ['dim7', 'diminished seventh', 'diminished 7th', 'diminished 7', 'o7', 'o7', '7b5', '7♭5'],
    (Maj3, Aug5, Min7): ['aug7', 'augmented seventh', 'augmented 7th', 'augmented 7', '+7', '7#5', '7♯5'],
    (Min3, Per5, Maj7): ['mmaj7', '-Δ7', '-M7'], # but additional aliases, see below

    # ninths (can we even detect these from the intervals encoded in a Chord object?
    (Maj3, Per5, Maj9): ['add9', 'added ninth', 'added 9th', 'added 9'],
    (Maj3, Per5, Maj7, Maj9): ['maj9', 'major ninth', 'major 9th'],
    (Min3, Per5, Min7, Maj9): ['min9', 'minor ninth', 'minor 9th'],
    (Maj3, Per5, Min7, Maj9): ['9', 'dominant ninth', 'dominant 9th', 'd9'],
    (Maj3, Per5, Min7, Min9): ['dmin9', 'dominant minor ninth', 'dominant minor 9th'],
    })

# common_chords = {key:value for i,(key,value) in enumerate(chord_names.items()) if i < 2}
# uncommon_chords = {key:value for i,(key,value) in enumerate(chord_names.items()) if i >= 2}


# minor/major 7 has multiple ways to be written, because the dash could be a dash or a slash or a space or nothing,
# e.g. m/maj7, m-maj7, minor major 7, minmaj7...
# so we just cover all our bases here:
for mm7_name in ['minor-major seventh', 'minor-major 7th', 'minor-major7', 'min-maj7', 'm-maj7', 'm-M7', 'm-m7']:
    chord_names[(Min3, Per5, Maj7)].append(mm7_name)
    for sub_char in ['/', ' ', '']:
        chord_names[(Min3, Per5, Maj7)].append(mm7_name.replace('-', sub_char))

# inverse dict mapping all accepted chord quality names to lists of their intervals:
chord_intervals = {}
for intervals, names in chord_names.items():
    for name in names:
        chord_intervals[name] = intervals

# some tonics correspond to a preference for sharps or flats:
# (applies to diatonic keys only?)
sharp_tonic_names = ['G', 'D', 'A', 'E', 'B']
flat_tonic_names = ['F', 'Bb', 'Eb', 'Ab', 'Db']
neutral_tonic_names = ['C', 'Gb'] # no sharp/flat preference, fall back on default

sharp_major_tonics = [Chroma(t) for t in sharp_tonic_names]
flat_major_tonics = [Chroma(t) for t in flat_tonic_names]
neutral_major_tonics = [Chroma(t) for t in neutral_tonic_names]

sharp_minor_tonics = [notes.relative_minors[Chroma(t)] for t in sharp_tonic_names]
flat_minor_tonics = [notes.relative_minors[Chroma(t)] for t in flat_tonic_names]
neutral_minor_tonics = [notes.relative_minors[Chroma(t)] for t in neutral_tonic_names]




def detect_sharp_preference(tonic, quality='major', default=True):
    """detect if a chord should prefer sharp or flat labelling
    depending on its tonic and quality"""
    if isinstance(tonic, str):
        tonic = Chroma(str)
    assert isinstance(tonic, Chroma)

    if quality in chord_names[(Maj3, Per5)]: # aliases for 'major':
        if tonic in sharp_major_tonics:
            return True
        elif tonic in flat_major_tonics:
            return False
        else:
            return default
    elif quality in chord_names[(Min3, Per5)]: # aliases for 'minor'
        if tonic in sharp_minor_tonics:
            return True
        elif tonic in flat_minor_tonics:
            return False
        else:
            return default
    else:
        return default

class Chord:
    ### to do: inversions?
    def __init__(self, arg1, arg2=None, prefer_sharps=None):
        """a set of Chromas, defined by some theoretical name like C#m7.
        arg1 can be one of:
            1) a single Chroma (or string that can be cast as a Chroma) to use as the tonic.
            2) an iterable of Chromas, the first of which is the tonic
            3) a string naming a chord, like 'Dm' 'C#7' or 'Gbsus4'

        in case #1, we consult arg2 to determine the other notes.
        arg2 can be a string, in which case we interpret it as the 'quality' of the chord,
        or it can be an iterable of integers or Intervals, in which case we interpret those
          as the intervals of the chord's other chromas relative to the tonic.
        if arg2 is not provided, we assume a major triad by default.

        quality must one of:
            'major', 'maj', 'M' (default)
            'minor', 'min', 'm'
            'fifth', '5th', '5'
            'suspended second', 'suspended 2nd', 'sus2'
            'suspended fourth', 'suspended 4th', 'sus4'
            'major seventh', 'major 7th', 'maj7', 'M7'
            'minor seventh', 'minor 7th', 'min7', 'm7'
            'dominant seventh', 'dominant 7th', 'dom7', 'd7'

        positions must be an iterable of integers or Intervals.
        """

        ### parse input:
        # case 1:
        if isinstance(arg1, Chroma) or (isinstance(arg1, str) and Chroma.is_valid_chroma_name(arg1)):
            # tonic has been given
            log(f'Parsing arg1 ({arg1}) as tonic of Chord')
            if isinstance(arg1, str):
                self.tonic = Chroma(arg1)
            else:
                self.tonic = arg1

            # assert arg2 is not None, "Initialising a Chord using a Tonic requires a second argument (quality:str or degrees:iterable)"
            if arg2 is None:
                log('No arg2 given for Chord initialisation by tonic, so assuming major triad by default')
                self.intervals = [Maj3, Per5]
            else:
                if isinstance(arg2, str):
                    # quality has been given
                    log(f'Parsing arg2 ({arg2}) as string denoting chord quality')
                    self.intervals = chord_intervals[arg2]
                elif isinstance(arg2, (list, tuple)):
                    # intervals have been given
                    log(f'Parsing arg2 ({arg2}) as {type(arg2)} of intervals')
                    self.intervals = [item if isinstance(item, Interval) else Interval(item) for item in arg2]
                else:
                    raise TypeError(f'Expected str, list or tuple for arg2, but got: {type(arg2)}')

        # case 2:
        elif isinstance(arg1, (list, tuple)):
            # iterable of chromas has been given
            log(f'Parsing arg1 ({arg1}) as {type(arg1)} of Chromas')
            chromas = [item if isinstance(item, Chroma) else Chroma(item) for item in arg1]
            self.tonic = chromas[0]

            self.intervals = [c - self.tonic for c in chromas[1:]]

        # case 3:
        else:
            # name of chord has been given, so we must parse it
            assert isinstance(arg1, str), f"Expected arg1 to be a string but got: {type(arg1)}"
            log(f'Parsing arg1 ({arg1}) as string indicating chord name')
            name = arg1
            if len(name) == 1:
                self.tonic = Chroma(name.upper())
                quality_idx = 1
            elif name[1] in ['#', '♯', 'b', '♭']:
                self.tonic = Chroma(name[0].upper() + '#') if name[1] in ['#', '♯'] else Chroma(name[0].upper() + 'b')
                quality_idx = 2 # where we read the rest of the string from
            else:
                self.tonic = Chroma(name[0].upper())
                quality_idx = 1

            assert self.tonic.name in notes.valid_note_names, f'{self.tonic} is not a valid Chord tonic'

            quality = name[quality_idx:].strip()
            self.intervals = chord_intervals[quality]

        # tonic and intervals have been assigned
        # make sure intervals are in order:
        self.intervals = sorted(self.intervals)

        # formulate unique intervals to determine chord naming
        self.unique_intervals = []
        self.repeated_intervals = []
        for i, this_interval in enumerate(self.intervals):
            if this_interval not in self.unique_intervals and this_interval.mod != 0:
                self.unique_intervals.append(this_interval)

            is_unique = True
            other_intervals = [other_interval for j, other_interval in enumerate(self.intervals) if j != i] + [Unison]
            for other_interval in other_intervals:
                if this_interval & other_interval: # enharmonic equivalence
                    is_unique = False
            if not is_unique:
                self.repeated_intervals.append(this_interval)


        # figure out the proper/common name for its quality (m, dim7, etc.)
        suffix = chord_names[tuple(self.unique_intervals)][0]
        self.suffix = suffix

        # figure out if we should prefer sharps or flats by the tonic:
        self.prefer_sharps = detect_sharp_preference(self.tonic, quality=self.suffix, default=True if prefer_sharps is None else prefer_sharps)
        # set tonic chroma to use preferred sharp convention:
        self.tonic._set_sharp_preference(self.prefer_sharps)

        # now we name the chord:
        self.name = self.tonic.name + suffix
        log(f'Detected chord: {self.name}')

        # assume non-inverted for now:
        # but inversions are TBI
        self.root = self.tonic

        self.chromas = ([self.tonic] + [self.tonic + i for i in self.intervals])
        log(f'  consisting of: {self.chromas}')

        # determine quality:
        # chord qualities (major, minor, augmented, suspended, indeterminate):

        if Maj3 in self.intervals and Per5 in self.intervals:
            self.quality = 'major'
        elif Min3 in self.intervals and Per5 in self.intervals:
            self.quality = 'minor'
        elif Maj2 in self.intervals or Per4 in self.intervals:
            self.quality = 'suspended'
        elif Dim5 in self.intervals and 'diminished' in [i.quality for i in self.intervals]:
            self.quality = 'diminished'
        elif Aug4 in self.intervals and 'augmented' in [i.quality for i in self.intervals]:
            self.quality = 'augmented'
        else:
            self.quality = 'indeterminate'

        self.minor = (self.quality == 'minor')
        self.major = (self.quality == 'major')
        self.suspended = (self.quality == 'suspended')
        self.diminished = (self.quality == 'diminished')
        self.augmented = (self.quality == 'augmented')
        self.indeterminate = (self.quality == 'indeterminate')
        self.dominant = (Maj3 in self.intervals and Per5 in self.intervals and Min7 in self.intervals)

        # extended chords contain a ninth or higher:
        self.extended = False
        for interval in self.intervals:
            if interval > 12:
                self.extended = True



    def __eq__(self, other):
        # assert isinstance(other, Chord), 'Chords can only be compared to other Chords'
        matching_notes = 0
        for note in self.chromas:
            if note in other.chromas:
                matching_notes += 1
        if matching_notes == len(self.chromas) and len(self.chromas) == len(other.chromas):
            return True
        else:
            return False

    def __add__(self, other):
        """Chord transposition, shift upwards by # semitones"""
        assert isinstance(other, (int, Interval)), "Only integers and Intervals can be added to Chords"
        new_tonic = self.tonic + other
        # new_intervals = [i + other for i in self.intervals]
        return Chord(new_tonic, self.intervals)

    def __sub__(self, other):
        """Chord transposition, shift downwards by # semitones"""
        assert isinstance(other, (int, Interval)), "Only integers and Intervals can be subtracted from Chords"
        new_tonic = self.tonic - other
        # new_intervals = [i + other for i in self.intervals]
        return Chord(new_tonic, self.intervals)

    def __hash__(self):
        return hash(str(self))

    def __str__(self):
        return f'♬ {self.name} {self.chromas}'

    def __repr__(self):
        return str(self)

    def relative_minor(self):
        assert not self.minor, f'{self} is already minor, and therefore has no relative minor'
        rm_tonic = notes.relative_minors[self.tonic]
        return Chord(rm_tonic, 'minor')

    def relative_major(self):
        assert not self.major, f'{self} is already major, and therefore has no relative major'
        rm_tonic = notes.relative_majors[self.tonic]
        return Chord(rm_tonic)

    def _set_sharp_preference(self, preference):
        """modify sharp preference in place"""
        self.prefer_sharps = preference
        self.tonic._set_sharp_preference(preference)
        self.name = self.tonic.name + self.suffix
        for c in self.chromas:
            c._set_sharp_preference(preference)



def StackedChord(tonic, intervals):
    """Initialise a chord by a series of intervals each relative to the previous interval.
    e.g. StackedChord('C', Min3, Maj3) returns C major"""
    log(f'Building Chord from stacked intervals: {intervals}')
    intervals_from_tonic = [intervals[0]]
    for i in intervals[1:]:
        intervals_from_tonic.append(intervals_from_tonic[-1] + i)
    c = Chord(tonic, intervals_from_tonic)
    log(f'Relative to tonic, those are: {intervals_from_tonic}, which we call: {c.name}')
    return c

class Progression:
    """container class for Chord objects"""
    def __init__(self, chords):
        # parse chords arg:
        self.chords = []
        self.chord_count = {}
        self.chromas = []
        self.chroma_count = {}

        self.contains_duplicates = False

        for item in chords:
            if isinstance(item, Chord): # already a Chord object
                c = item
            elif isinstance(item, str): # string that we try to cast to Chord
                c = Chord(item)
            elif isinstance(item, (list, tuple)): # pair of parameters that we try to cast to Chord
                c = Chord(*item)
            else:
                raise ValueError(f'Expected iterable to contain Chords, or items that can be cast as Chords, but got: {type(item)}')

            if c not in self.chord_count.keys():
                self.chords.append(c)
                self.chord_count[c] = 1

                self.chromas.extend(c.chromas)
                for ch in c.chromas:
                    if ch not in self.chroma_count.keys():
                        self.chroma_count[ch] = 1
                    else:
                        self.chroma_count[ch] += 1
            else:
                self.contains_duplicates = True
                self.chords.append(c)
                self.chord_count[c] += 1

        self.chroma_set = set(self.chromas)

    def __contains__(self, item):
        if isinstance(item, Chord):
            # efficient lookup by checking hash table keys:
            return item in self.chord_count.keys()
        elif isinstance(item, Chroma):
            return item in self.chroma_set

    def __str__(self):
        chord_set_str = ','.join([c.name for c in self.chords])
        return f'Progression: |{chord_set_str}|'

    def __repr__(self):
        return str(self)

    def detect_key(self):
        ... # TBI
        pass

class NoteSet:
    """a chord voicing as a (sorted) set of Notes"""
    def __init__(self, notes):
        # loop through notes arg and validate/instantiate:
        notes = [item if isinstance(item, Note) else Note(item) for item in notes]

        self.notes = set(sorted(notes))


if __name__ == '__main__':
    ### test cases for chord construction:
    test(Chord('C', 'minor'), Chord('Cm'))
    test(Chord('D', [4, 7]), Chord('D'))
    test(Chord('Em'), Chord('E', 'm'))
    test(Chord('D#sus4'), Chord('d#', 'suspended fourth'))
    test(Chord('Esus2'), Chord('E', 'sus2'))
    test(Chord('Gbdom7'), Chord('Gb', 'dominant 7th'))
    from notes import C, E, G
    test(Chord([C, E, G]), Chord(['C', 'E', 'G']))
    test(Chord([C, E, G]), C.chord(4,7))
    test(Chord([C, E, G]), C.major())
    test(Chord('Cadd9'), Chord('C', [4, 7, 14]))
    test(Chord('Cm/maj7'), Chord('C', 'minor-major 7th'))
    test(Chord('A minor'), StackedChord('A', [Min3, Maj3]))

    x = ChordSet(['Amin', 'Bmaj', 'Cmaj', 'Dmin'])
