import muse.notes as notes
from muse.notes import Note
from muse.intervals import *
from muse.util import log, test, precision_recall
from muse.parsing import valid_note_names, is_valid_note_name
from collections import defaultdict

import pdb

# TBI: should root_interval be changed to root_degree?


# all accepted aliases for chord names - common suffix is FIRST, this is the one chosen by automatic chord parsing
chord_names = defaultdict(lambda: [' (unknown chord)'],
    {(Maj3, Per5): ['', 'major', 'maj', 'maj3', 'major triad', 'M', 'Ma'],
    (Min3, Per5): ['m', 'minor', 'min', 'min3', 'minor triad', '-'],
    (Per5, ): ['5', '5th', 'fifth', 'ind', '(no 3)', '(no3)', 'power chord', 'power', 'pow'],

    # weird triads
    (Dim3, Per5): ['sus2', 'suspended 2nd', 'suspended second', 's2'],
    (Aug3, Per5): ['sus4', 'suspended 4th', 'suspended fourth', 's4'],
    (Maj3, Aug5): ['+', 'aug', 'augmented triad', 'augmented fifth', 'augmented 5th', 'aug5'],    #  #5? ♯5?
    (Min3, Dim5): ['dim', 'o', 'o', 'diminished', 'diminished triad', 'diminished fifth', 'diminished 5th', 'dim5', 'm♭5', 'mb5'],

    # sixths
    (Maj3, Per5, Maj6): ['6', 'maj6', 'M6', 'major sixth', 'major 6th'],
    (Min3, Per5, Maj6): ['m6', 'min6', 'minor sixth', 'minor 6th'],
    # other sixths (dim, aug, etc.) are probably just inversions of more common chords

    # sevenths
    (Maj3, Per5, Min7): ['7', 'dominant seventh', 'dominant 7th', 'dominant 7', 'dom7'],
    (Maj3, Per5, Maj7): ['maj7', 'major seventh', 'major 7th', 'major 7', 'M7', 'Δ7'],
    (Min3, Per5, Min7): ['m7', 'minor seventh', 'minor 7th', 'minor 7', 'min7', '-7'],
    (Min3, Dim5, Min7): ['hdim7', 'ø7', 'ø', 'm7(b5)', 'm7(♭5)', 'm7b5', 'm7♭5', 'half diminished seventh', 'half diminished 7th', 'half diminished 7', 'halfdim7'],
    (Min3, Dim5, Dim7): ['dim7', 'diminished seventh', 'diminished 7th', 'diminished 7', '°', '°7', 'o', 'o7', 'o', 'o7', '7b5', '7♭5'],
    (Maj3, Aug5, Min7): ['aug7', 'augmented seventh', 'augmented 7th', 'augmented 7', '+7', '7#5', '7♯5'],
    (Min3, Per5, Maj7): ['mmaj7', '-Δ7', '-M7'], # but additional aliases, see below

    # ninths
    (Maj3, Per5, Maj9): ['add9', 'added ninth', 'added 9th', 'added 9', 'major add9'],
    (Min3, Per5, Maj9): ['madd9', 'minor added ninth', 'minor added 9th', 'minor added 9', 'm add9', 'minor add9'],
    (Maj3, Per5, Maj7, Maj9): ['maj9', 'major ninth', 'major 9th'],
    (Min3, Per5, Min7, Maj9): ['m9', 'min9', 'minor ninth', 'minor 9th'],
    (Maj3, Per5, Min7, Maj9): ['9', 'dominant ninth', 'dominant 9th', 'd9'],
    (Maj3, Per5, Min7, Min9): ['dmin9', 'dominant minor ninth', 'dominant minor 9th'],
    })


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

# relative minors/majors of all chromatic notes:
relative_minors = {c : (c - 3) for c in notes.chromatic_scale}
relative_minors.update({c.sharp_name: (c-3).sharp_name for c in notes.chromatic_scale})
relative_minors.update({c.flat_name: (c-3).flat_name for c in notes.chromatic_scale})

relative_majors = {value:key for key,value in relative_minors.items()}


# chords arranged vaguely in order of rarity, for auto chord detection/searching:
common_chord_suffixes = ['', 'm', '5']
uncommon_chord_suffixes = ['sus2', 'sus4', '7', 'maj7', 'm7']
rare_chord_suffixes = ['9', 'm9', 'maj9', 'add9', 'madd9', 'dim7', 'hdim7']
very_rare_chord_suffixes = [v[0] for v in list(chord_names.values()) if v[0] not in (common_chord_suffixes + uncommon_chord_suffixes + rare_chord_suffixes)]
chord_types = common_chord_suffixes + uncommon_chord_suffixes + rare_chord_suffixes + very_rare_chord_suffixes

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



def detect_sharp_preference(tonic, quality='major', default=False):
    """detect if a chord should prefer sharp or flat labelling
    depending on its tonic and quality"""
    if isinstance(tonic, str):
        tonic = Note(str)
    assert isinstance(tonic, Note)

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

    # @staticmethod
    # def from_notes(notelist):
    #     candidate = most_likely_chord(notelist)
    #     if candidate.tonic != notelist[0]:
    #         # inversion?
    #         candidate.set_inversion(note=notelist[0])
    #     return candidate

    def __init__(self, arg1, arg2=None, root=None, prefer_sharps=None):
        """a set of Notes, defined by some theoretical name like C#m7.
        arg1 can be one of:
            1) a single Note (or string that can be cast as a Note) to use as the tonic.
                (plus an optional arg2, see below)
            2) an iterable of Notes, the first of which is the tonic
                (plus an optional root, see below)
            3) a string naming a chord, like 'Dm' 'C#7' or 'Gbsus4'

        in case #1, we consult arg2 to determine the other notes.
        arg2 can be a string, in which case we interpret it as the 'quality' of the chord,
        or it can be an iterable of integers or Intervals, in which case we interpret those
          as the intervals of the chord's other notes relative to the tonic.
        if arg2 is not provided, we assume a major triad by default.

        finally, in case #2, we can accept an optional 'root' arg, which can
        create an inverted chord if the root is provided as something other than the tonic.
        root should be an interval (in semitones) that is already present in the chord's intervals,
        or a note (or string that can be cast as note).

        inverted chords can also be created in case 3 by naming the interval directly, e.g.: "Am/C"
        """

        # parse input and determine whether we're dealing with an inversion:
        self.tonic, self.intervals, self.root = self._parse_input(arg1, arg2, root)
        self.inverted = (self.tonic != self.root)
        # (note that, in the case of an inversion, the intervals are from tonic, not root)

        # make sure intervals are in order:
        self.intervals = sorted(self.intervals)

        ### set some basic attributes:
        #extended chords are those that contain an extended intrval:
        self.extended = (True in [i.extended for i in self.intervals])
        self.octave_span = max([i.octave_span for i in self.intervals])

        # formulate unique intervals to determine chord naming
        self.unique_intervals, self.repeated_intervals  = self._detect_unique_and_repeated_intervals(self.intervals)
        # unique is the set of intervals that appear at least once in this chord
        # and repeated is the intervals that appear multiple times in this chord

        ### parse chord factors:
        self.factor_intervals = self._detect_interval_factors(self.unique_intervals)
        self.factors = {f: (self.tonic + i.value) for f, i in self.factor_intervals.items() if i is not None}

        # determine notes in chord:
        self.fundamental_intervals = list(self.factor_intervals.values())  # the fundamental intervals used to determine chord suffix
        self.fundamental_notes = list(self.factors.values())             # the corresponding fundamental notes
        self.notes = [self.tonic] + [self.tonic + i.value for i in self.intervals]      # 'full' list of notes, includes octaves and non-unique notes and so on

        # determine chord suffix: ('m', 'dim', 'mmaj7', etc.)
        detected_suffix = self._detect_suffix_from_intervals(self.fundamental_intervals)
        self.suffix = detected_suffix if detected_suffix is not None else ' (unknown chord)'

        # figure out if we should prefer sharps or flats by the tonic:
        prefer_sharps = detect_sharp_preference(self.tonic, quality=self.suffix, default=False if prefer_sharps is None else prefer_sharps)
        self._set_sharp_preference(prefer_sharps)

        # now we name the chord:
        root_str = f'/{self.root.name}' if self.root != self.tonic else ''
        self.name = self.tonic.name + self.suffix + root_str
        # this does not include detail about the inversion, though the self.__str__ method does
        log(f'Detected chord: {self.name}')
        log(f'  consisting of: {self.notes}')

        # set quality flags based on chord factors,
        # as well as a overriding quality: 'dominant' overrides 'major', etc.
        self._set_quality()

        # # check for inversions, assign root note/interval and re-set name if so:
        # if root is not None:
        #     if isinstance(root, (str, Note)):
        #         self.set_inversion(note=root) # this re-sets name if called
        #     elif isinstance(root, (int, Interval)):
        #         self.set_inversion(interval=root)
        #     if abs(self.root_interval) > 0:
        #         self.inverted = True
        # else:
        #     self.root = self.tonic
        #     self.root_interval = 0
        #     self.inverted = False

    #### main arg-parsing method:
    def _parse_input(self,arg1, arg2, root):
        ###### parse input according to one of 3 separate cases.
        ###### in each, we must set tonic, intervals, and root

        ### case 1: input is Note, or casts to Note
        if isinstance(arg1, Note) or (isinstance(arg1, str) and is_valid_note_name(arg1)):
            # tonic has been given
            log(f'Chord.init case 1: Parsing arg1 ({arg1}) as tonic of Chord')
            if isinstance(arg1, str):
                tonic = Note(arg1)
            else:
                tonic = arg1

            # assert arg2 is not None, "Initialising a Chord using a Tonic requires a second argument (quality:str or degrees:iterable)"
            if arg2 is None:
                log('No arg2 given for Chord initialisation by tonic, so assuming major triad by default')
                intervals = [Maj3, Per5]
            else:
                if isinstance(arg2, str):
                    # quality has been given
                    log(f'Parsing arg2 ({arg2}) as string denoting chord quality')
                    intervals = chord_intervals[arg2]
                elif isinstance(arg2, (list, tuple)):
                    # intervals have been given
                    log(f'Parsing arg2 ({arg2}) as {type(arg2)} of intervals')
                    intervals = [item if isinstance(item, Interval) else Interval(item) for item in arg2]
                else:
                    raise TypeError(f'Expected str, list or tuple for arg2, but got: {type(arg2)}')

            # we have tonic and intervals, now check for inversions (if a root arg has been passed to this method):
            if root is not None:
                if isinstance(root, (str, Note)):
                    # root is a Note, or casts to one
                    if isinstance(root, str):
                        root = Note(str)
                elif isinstance(root, (int, Interval)):
                    # root is an Interval, or casts to one
                    if isinstance(root, int):
                        if root > 12:
                            root = ExtendedInterval(root)
                        else:
                            root = Interval(root)
                    # use root interval to determine root note:
                    root = tonic + root
            else:
                # root defaults to tonic
                root = tonic


        ### case 2: input is a list of Notes, or objects that cast to Notes
        elif isinstance(arg1, (list, tuple)):
            # iterable of notes has been given
            log(f'Chord.init case 2: Parsing arg1 ({arg1}) as {type(arg1)} of Notes')
            chord_notes = [item if isinstance(item, Note) else Note(item) for item in arg1]
            # interpret first note in input as the tonic:
            tonic = chord_notes[0]
            intervals = [c - tonic for c in chord_notes[1:]]

            # now, we determine if this is a chord we can name

            # first we check if those intervals correspond to a known pre-defined chord:
            first_candidate = self._detect_suffix_from_intervals(intervals)
            # if we get a result, we're happy:
            if first_candidate is not None:
                root = tonic
            # otherwise: we use the detect_chords method to find the most likely chord these notes correspond to:
            # (this is also a first stab at detecting inversions)
            else:
                candidates = matching_chords(chord_notes)
                print(f'{len(candidates)} possible candidates found for Chord init via notes: {[c.name for c in candidates]}')
                # if we found any, use the best one:
                if len(candidates) > 0:
                    match = candidates[0]
                    print(f'  Most likely match: {match}')
                    # if its tonic doesn't match, then the notelist we've been given is an inversion
                    # and the matching chord's tonic is the true tonic of this chord
                    if match.tonic != tonic:
                        root = tonic
                    else:
                        root = match.tonic
                    # in either case, we use the matching chord's tonic and intervals
                    tonic = match.tonic
                    intervals = match.intervals
                # otherwise: mystery chord! just leave tonic and intervals assigned as-is
                else:
                    print(f'  Initialising indeterminate chord with notes: {chord_notes}')
                    print(f'    tonic: {tonic} \n  intervals: {[i.value for i in intervals]}')
                    root = tonic


        ### case 3: input is string, simply the name of a chord
        else:
            # name of chord has been given, so we must parse it
            assert isinstance(arg1, str), f"Expected arg1 to be a string but got: {type(arg1)}"
            log(f'Chord.init case 3: Parsing arg1 ({arg1}) as string indicating chord name')
            name = arg1

            if len(name) == 1:
                tonic = Note(name.upper())
                quality_idx = 1
            elif name[1] in ['#', '♯', 'b', '♭']:
                tonic = Note(name[0].upper() + '#') if name[1] in ['#', '♯'] else Note(name[0].upper() + 'b')
                quality_idx = 2 # where we read the rest of the string from
            else:
                tonic = Note(name[0].upper())
                quality_idx = 1

            assert tonic.name in valid_note_names, f'{tonic} is not a valid Chord tonic'

            # we detect inversions by looking for a / in the chordname
            # (but we also need to look out for min/maj chord names, because they can have a confounding slash in them)
            if '/' in name:
                if len(name.split('/')) == 2 and 'min/maj' not in name and 'minor/major' not in name and 'm/m' not in name:
                    # inversion, not a minmaj
                    name, root_name = name.split('/')
                elif len(name.split('/')) == 3:
                    # inversion AND a minmaj
                    n1, n2, root_name = name.split('/')
                    name = n1 + '/' + n2
                else:
                    # just a minmaj, no inversion
                    root_name = None


                if root_name is not None:
                    if len(root_name) == 1:
                        root = Note(root_name.upper())
                        # quality_idx = 1
                    elif root_name[1] in ['#', '♯', 'b', '♭']:
                        root = Note(root_name[0].upper() + '#') if root_name[1] in ['#', '♯'] else Note(root_name[0].upper() + 'b')
                        # quality_idx = 2
                    else:
                        root = Note(root_name[0].upper())
                        # quality_idx = 1
                else:
                    # default to tonic
                    root = tonic
            else:
                root = tonic

            # determine chord quality from provided name and allocate appropriate intervals:
            quality = name[quality_idx:].strip()
            intervals = chord_intervals[quality]

        return tonic, intervals, root

    #### init / arg-parsing subroutines:
    @staticmethod
    def _detect_unique_and_repeated_intervals(intervals):
        unique_intervals = []
        repeated_intervals = []

        for i, this_interval in enumerate(intervals):
            if this_interval not in unique_intervals and this_interval.mod != 0:
                unique_intervals.append(this_interval)

            is_unique = True
            # compare to other intervals in the chord to determine repetition:
            other_intervals = [other_interval for j, other_interval in enumerate(intervals) if j != i] + [Unison]
            for other_interval in other_intervals:
                if this_interval.mod == other_interval.mod: # enharmonic equivalence
                    is_unique = False
            if not is_unique:
                if this_interval not in repeated_intervals:
                    repeated_intervals.append(this_interval)

        return unique_intervals, repeated_intervals

    def _detect_interval_factors(self, intervals):
        """for an iterable of intervals, return the chord factors that we think
        those intervals correspond to, making assumptions about fifths/sevenths/etc"""
        # strip root/tonic just in case it's been given, as well as any octave notes:
        intervals = [i for i in intervals if i.mod != 0]

        num_notes = len(intervals) + 1
        factors = defaultdict(lambda: NullInterval(), {})

        # we don't assume that intervals are sorted in order of ascending value,
        # but we DO assume that they are in factor order: e.g. thirds always before fifths always before sevenths
        if num_notes == 2:
            # this is a dyad
            i = intervals[0]
            if i.degree == 5 or i.valid_fifth():
                factors[5] = IntervalDegree(i.value, 5)
            else:
                log(f"Non-perfect dyad chord: {intervals} doesn't include a fifth")
                this_degree = i.degree if i.degree is not None else i.expected_degree
                factors[this_degree] = i
            # finished
            return factors

        elif num_notes >= 3:
            # this is a triad, assume there is a third and a fifth:
            third, fifth = intervals[0], intervals[1]
            if third.degree == 3 or third.valid_third():
                factors[3] = IntervalDegree(third.value, 3)
            else:
                print(f"Irregular triad chord ({intervals}): {third} is not a valid third")
                this_degree = third.degree if third.degree is not None else third.expected_degree
                factors[this_degree] = IntervalDegree(third.value, this_degree)

            if fifth.degree == 5 or fifth.valid_fifth():
                factors[5] = IntervalDegree(fifth.value, 5)
            else:
                print(f"Irregular triad chord ({intervals}): {fifth} is not a valid fifth")
                this_degree = fifth.degree if fifth.degree is not None else fifth.expected_degree
                factors[this_degree] = IntervalDegree(fifth.value, this_degree)

            if num_notes == 4:
                # this could be a sixth, seventh, or an add9
                # detect add9 first:
                i = intervals[2]
                if i.degree == 9 or i.valid_degree(9):
                    factors[9] = ExtendedInterval(i.value, 9)
                # sevenths are more likely than sixths:
                elif i.degree == 7 or i.valid_seventh():
                    factors[7] = IntervalDegree(i.value, 7)
                elif i.degree == 6 or i.valid_degree(6):
                    factors[6] = IntervalDegree(i.value, 6)
            else:
                # more than 4 notes, we can't make assumptions anymore
                # so just loop through remaining intervals and use expected degrees:
                for i in intervals[2:]:
                    this_degree = i.degree if i.degree is not None else i.expected_degree
                    if this_degree > 7:
                        factors[this_degree] = ExtendedInterval(i.value, this_degree)
                    else:
                        factors[this_degree] = IntervalDegree(i.value, this_degree)

        return factors

    def _detect_suffix_from_intervals(self, intervals):
        """From an iterable of Interval objects, or objects that can be cast as intervals,
        determine the proper chord suffix
        (based on the predetermined chords in global var chord_names)"""
        # cast to tuple of Interval objects:
        intervals = tuple([Interval(i) if not isinstance(i, Interval) else i for i in intervals])
        if intervals in chord_names.keys():
            suffix = chord_names[intervals][0] # common suffix is the FIRST listed alias in chord_names
            return suffix
        else:
            return None

    def _set_sharp_preference(self, prefer_sharps):
        """set the sharp preference of all notes inside this Chord,
        including the tonic, root, and constituent factors"""
        self.tonic._set_sharp_preference(prefer_sharps)
        self.root._set_sharp_preference(prefer_sharps)
        for n in self.notes:
            n._set_sharp_preference(prefer_sharps)
        for n in self.factors.values():
            n._set_sharp_preference(prefer_sharps)

    def _set_quality(self):
        """Uses self.factor_intervals to determine self.quality attribute and related flags"""
        # all bool attribute flags are false unless explicitly made true in the upcoming block:
        self.minor = False    # contains a minor 3rd?
        self.major = False    # contains a major 3rd?
        self.perfect = False  # contains a perfect 5th?

        self.diminished = False # note that diminished chords are also minor chords
        self.augmented = False # and augmented chords are also major chords
        self.dominant = False # and dominant chords are major, but not minor
        self.suspended = False # and suspended chords are indeterminate, being neither major nor minor
        self.fifth_chord = False # and fifth chords are indeterminate, being neither major nor minor

        self.indeterminate = False # is neither major nor minor (P5 chords, sus chords), or is both (m/maj chords)

        if self.factor_intervals[3].quality == 'minor':
            self.quality = 'minor'
            self.minor = True
            # minor third
            if self.factor_intervals[5].quality == 'perfect':
                # minor triad
                self.perfect = True
                if self.factor_intervals[7].quality == 'major':
                    # special case: minor/major chord:
                    self.quality = 'indeterminate'
                    self.major = True
                    self.indeterminate = True
            elif self.factor_intervals[5].quality == 'diminished':
                # dim chord
                self.quality = 'diminished'
                self.diminished = True

        elif self.factor_intervals[3].quality == 'major':
            # major third
            self.quality = 'major'
            self.major = True
            if self.factor_intervals[5].quality == 'perfect':
                # major triad, could still be dominant
                self.perfect = True
                if self.factor_intervals[7].quality == 'minor':
                    self.quality = 'dominant'
                    self.dominant = True
            elif self.factor_intervals[5].quality == 'augmented':
                # aug chord
                self.quality = 'augmented'
                self.augmented = True

        elif self.factor_intervals[3].quality in ['augmented', 'diminished']:
            # sus chord
            self.quality = 'suspended'
            self.indeterminate = True
            self.suspended = True
            if self.factor_intervals[5].quality == 'perfect':
                self.perfect = True

        elif self.factor_intervals[5].quality == 'perfect':
            # fifth chord
            self.quality = 'indeterminate'
            self.perfect = True
            self.fifth_chord = True

        else:
            self.quality = 'indeterminate'
            self.indeterminate = True
            print(f'Unknown chord: {self.factor_intervals}')


    #### utility methods:

    def set_inversion(self, note=None, interval=None):
        """mutates Chord object in-place to an inverted chord,
        rooted on note arg, or on the note corresponding to the interval arg (from tonic),
        assuming intervals as they stand are already relative to tonic"""
        ###TBI
        ...

        if note is not None:
            if isinstance(note, str):
                # cast str to note if necessary
                note = Note(note)
            if isinstance(note, Note):
                self.root = note
                # root_interval = self.root - self.tonic
                # if self.root_interval < 0:
                #     self.root_interval = -self.root_interval

            assert self.root in self.notes, f"Desired root note {self.root} does not exist in chord notes: {self.notes}"

        elif interval is not None:
            if isinstance(interval, int):
                # cast int to interval if needed:
                interval = Interval(interval)
            if isinstance(interval, Interval):
                assert interval in self.intervals, f"Desired root interval {root_interval} does not exist in chord intervals: {self.intervals}"
                # self.root_interval = interval
                self.root = self.tonic + interval
            else:
                raise TypeError(f'Expected an int or interval as root_interval arg for set_inversion, but got: {type(root_interval)}')

        elif note is None and interval is None:
            raise ValueError('Chord.set_inversion method expects either note or interval to be provided, but both are None')

        if self.root != self.tonic:
            self.inverted = True
            root_str = f'/{self.root.name}'
            self.name = self.tonic.name + self.suffix + root_str



    def consonance(self):
        # establish the chord's overall consonance rating
        # by creating a matrix of the fundamental intervals in the chord
        # and averaging all of their consonances with one another
        ... #TBI

    def relative_minor(self):
        # assert not self.minor, f'{self} is already minor, and therefore has no relative minor'
        assert self.major, f'{self} is not major, and therefore has no relative minor'
        rm_tonic = notes.relative_minors[self.tonic]
        return Chord(rm_tonic, 'minor')

    def relative_major(self):
        # assert not self.major, f'{self} is already major, and therefore has no relative major'
        assert self.minor, f'{self} is not minor, and therefore has no relative major'
        rm_tonic = notes.relative_majors[self.tonic]
        return Chord(rm_tonic)

    def relative(self):
        if self.major:
            return self.relative_minor()
        elif self.minor:
            return self.relative_major()
        else:
            raise Exception(f'Chord {self} is neither major or minor, and therefore has no relative')

    def clockwise(self, value=1):
        """fetch the next chord from clockwise around the circle of fifths,
        or if value>1, go clockwise that many steps"""
        from scales import Key
        reference_key = Key(self.tonic) if self.major else Key(self.relative_major().tonic)
        new_co5s_pos = (co5s_positions[reference_key] + value) % 12
        # instantiate new key object: (just in case???)
        new_key = co5s[new_co5s_pos]
        new_key = new_key if self.major else new_key.relative_minor()
        new_chord = Chord(new_key.tonic, new_key.suffix)
        return new_chord

    def counterclockwise(self, value=1):
        return self.clockwise(-value)

    def neighbours(self, distance=1.0):
        """return the chords that are closest to this one, in terms of major/minor relation
        and key distance."""







    def __len__(self):
        return len(self.unique_intervals) + 1

    def __contains__(self, item):
        return item in self.notes

    def __eq__(self, other):
        # assert isinstance(other, Chord), 'Chords can only be compared to other Chords'
        matching_notes = 0
        for note in self.notes:
            if note in other.notes:
                matching_notes += 1
        if matching_notes == len(self.notes) and len(self.notes) == len(other.notes):
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
        """chord hash method is entirely dependent on the positions
        (and not values) of its notes"""
        hash_str = '/'.join([str(n.position) for n in self.notes])
        return hash(hash_str)

    def __str__(self):
        if self.inverted:
            # figure out how to rearrange the notes in order by determining root_place
            # e.g. if Chord is Am/C, Chord.notes is ['A', 'C', 'E'], root is 'C',
            # and then root_place is 1 ... because Chord.notes[1] == 'C'
            root_place = [i for i, n in enumerate(self.notes) if n == self.root][0]
            # so we rearrange the notes from ordering [0,1,2] to e.g. [1,2,0]:
            note_idxs = [(root_place + i) % len(self) for i in range(len(self))]
            note_list = [self.notes[i] for i in note_idxs]
        else:
            note_list = self.notes
        return f'♬ {self.name} {note_list}'

    def __repr__(self):
        return str(self)



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

    def properties(self):
        flags = ', '.join(self._get_flags())
        return f"""
        {str(self)}
        Type:           {type(self)}
        Name:           {self.name}
        Intervals:      {self.intervals}
         (unique):      {self.unique_intervals}
        OctaveSpan:     {self.octave_span}
        Notes:          {self.notes}
         (fundamental): {self.fundamental_notes}
        Factors:        {self.factors}
        Tonic:          {self.tonic}
          (root):       {self.root}
        Suffix:         {self.suffix}
        Quality:        {self.quality}
        SharpPref:      {self.tonic.prefer_sharps}

        Flags:          {flags}
        ID:             {id(self)}"""

    def summary(self):
        print(self.properties())



def StackedChord(tonic, stack):
    """Initialise a chord by a series of intervals each relative to the previous interval.
    e.g. StackedChord('C', Min3, Maj3) returns C major"""
    log(f'Building Chord from stacked intervals: {intervals}')
    tonic_intervals = intervals_from_tonic(stack)
    c = Chord(tonic, tonic_intervals)
    log(f'Relative to tonic, those are: {tonic_intervals}, which we call: {c.name}')
    return c





def rate_chords(notelist):
    """given an iterable of Note or OctaveNote objects,
    determine the chords that those notes could belong to.

    returns an ordered dict with chords as keys,
    and (precision, recall) tuples as values for those chords"""

    ### check for common chords first:
    full_matches = []
    partial_matches = {}

    unique_notes = []
    for n in notelist:
        if isinstance(n, Note):
            unique_notes.append(Note(position=n.position))
        elif isinstance(n, int):
            unique_notes.append(Note(position=n))
        elif isinstance(n, str):
            unique_notes.append(Note(n))
    unique_notes = list(set(unique_notes))

    for tonic in notes.chromatic_scale:
        for quality in chord_types:
            candidate = Chord(tonic, quality)

            precision, recall = precision_recall(notelist, candidate)





    return full_matches, partial_matches

def detect_chords(notelist, threshold=0.7, max=5):
    """return a list of the most likely chords that a notelist could belong to,
    with the very first in the list being a likely first guess"""
    chord_matches, chord_ratings = rate_chords(notelist)
    if len(chord_matches) > 0:
        # common_matches = [ch for ch in chord_matches if (ch.quality in 'major', 'minor') or (ch.fifth_chord)]
        # uncommon_matches = [ch for ch in chord_matches if ch not in common_matches]
        return chord_matches
    else:
        names, ratings = list(chord_ratings.keys()), list(chord_ratings.values())
        ranked_chords = sorted(names, key=lambda n: chord_ratings[n], reverse=True)
        ranked_ratings = sorted(ratings, reverse=True)

        ranked_chords = [c for i, c in enumerate(ranked_chords) if ranked_ratings[i] >= threshold]
        ranked_ratings = [r for i, r in enumerate(ranked_ratings) if r >= threshold]

        # don't clip off chords with the same rating as those left in the list:
        truncated_ratings = ranked_ratings[:max]
        if (len(truncated_ratings) == max) and truncated_ratings[-1] == ranked_ratings[max]:
            final_ratings = [r for i, r in enumerate(ranked_ratings[max:]) if r == truncated_ratings[-1]]
            truncated_ratings.extend(final_ratings)
        truncated_chords = ranked_chords[:len(truncated_ratings)]
        return {c: r for c, r in zip(truncated_chords, truncated_ratings)}

def matching_chords(notelist):
    """returns a list of the chords that are a perfect match for some desired notelist"""
    result = detect_chords(notelist, threshold=1)
    return result

def most_likely_chord(notelist, return_probability = False):
    """makes a best guess at an unknown chord"""
    result = detect_chords(notelist, threshold=0)
    if len(result) > 0:
        if isinstance(result, list):
            # full match, most common chords first
            probability = 1.00
            c = result[0]
        else:
            c = list(result.keys())[0]
            probability = list(result.values())[0]
        if return_probability:
            return c, probability
        else:
            return c
    else:
        # nothing found
        if return_probability:
            return None, 0.0
        else:
            return None



if __name__ == '__main__':
    ### test cases for chord construction:
    test(Chord('C', 'minor'), Chord('Cm'))
    test(Chord('D', [4, 7]), Chord(['D', 'F#', 'A']))
    test(Chord('Em'), Chord('E', 'm'))
    test(Chord('D#sus4'), Chord('d#', 'suspended fourth'))
    test(Chord('Esus2'), Chord('E', 'sus2'))
    test(Chord('Gbdom7'), Chord('Gb', 'dominant 7th'))
    Cn, En, Gn = notes.C, notes.E, notes.G
    test(Chord([Cn, En, Gn]), Chord(['C', 'E', 'G']))
    test(Chord([Cn, En, Gn]), Cn.chord([4,7]))
    test(Chord([Cn, En, Gn]), Cn('major'))
    test(Chord('Cadd9'), Chord('C', [4, 7, 14]))
    test(Chord('Cm/maj7'), Chord('C', 'minor-major 7th'))
    test(Chord('A minor'), StackedChord('A', [Min3, Maj3]))

    test(matching_chords(['C', 'E', 'A']), Chord('Am/C'))
