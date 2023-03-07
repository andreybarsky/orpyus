import muse.notes as notes
from muse.notes import Note
from muse.intervals import *
from muse.util import log, test, precision_recall
from muse.parsing import valid_note_names, is_valid_note_name, parse_out_note_names
from collections import defaultdict

import pdb

# TBI: idea for complex chord detection:
# if no perfect matches, attempt leave-one-out chord detection
# find the nearest chord to the target (the one that one was left out from)
# get the DEGREE of the interval that was left out
# and compute a name for the absence in that degree between nearest and target chord

# all accepted aliases for chord names - common suffix is FIRST, this is the one chosen by automatic chord parsing
chord_names = defaultdict(lambda: [' (unknown chord)'],
    # normal triads
    {(Maj3, Per5): ['', 'major', 'maj', 'maj3', 'major triad', 'M', 'Ma'],
    (Min3, Per5): ['m', 'minor', 'min', 'min3', 'minor triad', '-'],

    # dyads
    (Per5, ): ['5', '5th', 'fifth', 'ind', '(no 3)', '(no3)', 'power chord', 'power', 'pow'],
    # are these real??
    (Maj3, ): ['(no5)'],
    (Min3, ): ['m(no5)'],

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
    (Min3, Dim5, Dim7): ['dim7', 'diminished seventh', 'diminished 7th', 'diminished 7', '°', '°7', 'o', 'o7', 'o', 'o7', '7b5', '7♭5', 'b7b5', 'b7♭5',],
    (Maj3, Aug5, Min7): ['aug7', 'augmented seventh', 'augmented 7th', 'augmented 7', '+7', '7#5', '#7#5', '#5#7', '7♯5', '♯7♯5', '♯5♯7'],
    (Min3, Per5, Maj7): ['mmaj7', '-Δ7', '-M7'], # but additional aliases, see below

    # ninths
    (Maj3, Per5, Maj9): ['add9', 'added ninth', 'added 9th', 'added 9', 'major add9'],
    (Min3, Per5, Maj9): ['madd9', 'minor added ninth', 'minor added 9th', 'minor added 9', 'm add9', 'minor add9'],
    (Maj3, Per5, Maj7, Maj9): ['maj9', 'major ninth', 'major 9th', 'M9'],
    (Min3, Per5, Min7, Maj9): ['m9', 'min9', 'minor ninth', 'minor 9th'],
    (Maj3, Per5, Min7, Maj9): ['9', 'dom9', 'dominant ninth', 'dominant 9th', 'd9'],
    (Maj3, Per5, Min7, Min9): ['dmin9', 'dominant minor ninth', 'dominant minor 9th'],

    # elevenths
    (Maj3, Per5, Maj7, Maj9, Per11): ['maj11', 'major eleventh', 'major 11th', 'M11'],
    (Min3, Per5, Min7, Maj9, Per11): ['m11', 'min11', 'minor eleventh', 'minor 11th'],
    (Maj3, Per5, Min7, Maj9, Per11): ['11', 'dom11', 'dominant eleventh', 'dominant 11th', 'd11'],
    (Maj3, Per5, Min7, Maj9, Aug11): ['9#11', '9♯11', 'dom#11', 'dominant sharp eleventh', 'dominant sharp 11th', 'd#11'],
    (Maj3, Per5, Maj7, Maj9, Aug11): ['maj9#11', 'maj9♯11', 'maj#11', 'major sharp eleventh', 'major sharp 11th', 'M#11'],
    })

# minor/major 7 has multiple ways to be written, because the dash could be a dash or a slash or a space or nothing,
# e.g. m/maj7, m-maj7, minor major 7, minmaj7...
# so we just cover all our bases here:
for mm7_name in ['minor-major seventh', 'minor-major 7th', 'minor-major7', 'min-maj7', 'm-maj7', 'm-M7', 'm-m7']:
    chord_names[(Min3, Per5, Maj7)].append(mm7_name)
    for sub_char in ['/', ' ', '']:
        chord_names[(Min3, Per5, Maj7)].append(mm7_name.replace('-', sub_char))

# chords arranged vaguely in order of rarity, for auto chord detection/searching:
common_chord_suffixes = ['', 'm']
uncommon_chord_suffixes = ['5', 'sus2', 'sus4', '7', 'maj7', 'm7']
rare_chord_suffixes = ['9', 'm9', 'maj9', 'add9', 'madd9', 'dim7', 'hdim7']
very_rare_chord_suffixes = [v[0] for v in list(chord_names.values()) if v[0] not in (common_chord_suffixes + uncommon_chord_suffixes + rare_chord_suffixes)]

##### procedurally generate weird altered chords:
legendary_chord_suffixes = [] # the only thing rarer than 'very rare'
# add sus2 and sus4 variants to all sixths, sevenths, and eighths
sus_chord_names = {}
# and add add4s to all triads and tetrads:
add4_chord_names = {}
# add add11s to all 6th/7th chords:
add11_tetrad_names = {}
for intervals, names in chord_names.items():
    # sus2/4 chords
    if len(intervals) >= 3: # only for tetrads and higher
        # replace maj3s with aug3s to make sus4s:
        if intervals[0] == Maj3:
            sus_intervals = tuple([Aug3] + list(intervals[1:]))
            altered_names = [f'{name}sus4' if ' ' not in name else f'{name} sus4' for name in names]
            # sus_tetrad_names[sus_intervals] = altered_names
            # legendary_chord_suffixes.append(altered_names[0])
        elif intervals[0] == Min3:
            sus_intervals = tuple([Dim3] + list(intervals[1:]))
            altered_names = [f'{name}sus2' if ' ' not in name else f'{name} sus2' for name in names]
        # add to altered chord dict:
        sus_chord_names[sus_intervals] = altered_names
        # append legendary chord list:
        legendary_chord_suffixes.append(altered_names[0])
    # add4/11 chords
    if len(intervals) in [2,3]: # for triads only
        # add4s:
        if len(intervals) == 2 and Aug3 not in intervals: # a sus4 can't be an add4
            add4_intervals = tuple([intervals[0]] + [Per4] + list(intervals[1:]))
            altered_names = [f'{name}add4' if ' ' not in name else f'{name} add4' for name in names]
            # but note that these are also equivalent to add11s
            # (we reserve the add11 extended interval for chords with 6ths/7ths)
            altered_names.extend([f'{name}add11' if ' ' not in name else f'{name} add11' for name in names])
            add4_chord_names[add4_intervals] = altered_names
            very_rare_chord_suffixes.append(altered_names[0])
        # add11s
        elif len(intervals) == 3 and intervals[-1] != Maj9: # add9s can't be add11s
             add11_intervals = tuple(list(intervals) + [Per11])
             altered_names = [f'{name}add11' if ' ' not in name else f'{name} add11' for name in names]
             add11_tetrad_names[add11_intervals] = altered_names
             legendary_chord_suffixes.append(altered_names[0])
chord_names.update(sus_chord_names)
chord_names.update(add4_chord_names)
chord_names.update(add11_tetrad_names)
chord_types = common_chord_suffixes + uncommon_chord_suffixes + rare_chord_suffixes + very_rare_chord_suffixes + legendary_chord_suffixes

# inverse dict mapping all accepted chord quality names to lists of their intervals:
chord_intervals = {}
for intervals, names in chord_names.items():
    for name in names:
        chord_intervals[name] = intervals

# relative minors/majors of all chromatic notes:
relative_minors = {c.name : (c - 3).name for c in notes.chromatic_scale}
relative_minors.update({c.sharp_name: (c-3).sharp_name for c in notes.chromatic_scale})
relative_minors.update({c.flat_name: (c-3).flat_name for c in notes.chromatic_scale})

relative_majors = {value:key for key,value in relative_minors.items()}

# some chord/key tonics correspond to a preference for sharps or flats:
sharp_tonic_names = ['G', 'D', 'A', 'E', 'B']
flat_tonic_names = ['F', 'Bb', 'Eb', 'Ab', 'Db']
neutral_tonic_names = ['C', 'Gb'] # no sharp/flat preference, fall back on default

sharp_major_tonics = [Note(t) for t in sharp_tonic_names]
flat_major_tonics = [Note(t) for t in flat_tonic_names]
neutral_major_tonics = [Note(t) for t in neutral_tonic_names]

sharp_minor_tonics = [Note(relative_minors[t]) for t in sharp_tonic_names]
flat_minor_tonics = [Note(relative_minors[t]) for t in flat_tonic_names]
neutral_minor_tonics = [Note(relative_minors[t]) for t in neutral_tonic_names]


class Chord:
    def __init__(self, arg1, arg2=None, root=None, prefer_sharps=None):
        """a set of Notes, defined by some theoretical name like C#m7.
        arg1 can be one of:
            1) a single Note (or string that can be cast as a Note) to use as the tonic.
                (plus an optional arg2, see below)
            2) an iterable of Notes, the first of which is the root/tonic
                (though we can pass an optional root arg, see below)
            3) a string naming a chord, like 'Dm' 'C#7' or 'Gbsus4',
                or a string of note names like 'CEG#A'

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

        # accessing self.factors after init should give us the tonic too:
        factor_intervals_including_tonic = [(1, Interval(0))] + [(f, i) for f,i in self.factor_intervals.items() if i is not None]
        self.factors = {f: (self.tonic + i.value) for f, i in factor_intervals_including_tonic}

        # determine chord suffix: ('m', 'dim', 'mmaj7', etc.)
        detected_suffix = self._detect_suffix_from_intervals(self.fundamental_intervals)
        if detected_suffix is None:
            import pdb; pdb.set_trace()
        self.suffix = detected_suffix if detected_suffix is not None else ' (unknown chord)'



        # now we name the chord:
        root_str = f'/{self.root.name}' if self.root != self.tonic else ''
        self.name = self.tonic.name + self.suffix + root_str
        # this does not include detail about the inversion, though the self.__str__ method does
        log(f'Detected chord: {self.name}')
        log(f'  consisting of: {self.notes}')

        # set quality flags based on chord factors,
        # as well as a overriding quality: 'dominant' overrides 'major', etc.
        self._set_quality()

        # figure out if we should prefer sharps or flats by the tonic:
        prefer_sharps = self._detect_sharp_preference(default=False if prefer_sharps is None else prefer_sharps)
        self._set_sharp_preference(prefer_sharps)

        # set some additional interesting attributes: ### (these are properties now)
        # self.consonance = self.get_consonance()
        # self.rarity = self.get_rarity()

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
                        root = Note(root)
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
            # otherwise: we use the detect_chords method to find the most likely
            # chord these notes correspond to (probably an inversion)
            else:
                # get the most likely chord, provided it has perfect recall and precision

                # matches = matching_chords(chord_notes, score=True)
                match = most_likely_chord(chord_notes, perfect_only=True)

                # if we got a result, accept it:
                if match is not None:
                    print(f'  Best match: {match}')
                    # if its tonic doesn't match, then the notelist we've been given is an inversion
                    # and the matching chord's tonic is the true tonic of this chord
                    if match.tonic != tonic:
                        root = tonic
                    else:
                        root = match.tonic
                    # in either case, we use the matching chord's tonic and intervals
                    tonic = match.tonic
                    intervals = match.intervals
                # otherwise, if no perfect mathc: mystery chord! just leave tonic and intervals assigned as-is
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

            # try and determine chord quality from provided name and allocate appropriate intervals:
            quality = name[quality_idx:].strip()
            if quality in chord_intervals:
                intervals = chord_intervals[quality]
            # otherwise: parsing the string as a chord tonic and a suffix has failed,
            # but we can try one more thing: parsing it as a string of note names
            else:
                log(f'Reading {quality} as a chord quality failed, so instead we will try to read {name} as a series of notes')
                try:
                    note_names = parse_out_note_names(name)
                    note_list = [Note(n) for n in note_names]
                    # and call recursively:
                    return self._parse_input(note_list, None, root=note_list[0])
                except:
                    raise ValueError(f'Could not understand {quality} as a chord quality or {name} as a series of notes')

        # make sure to cast root to Note instead of OctaveNote:
        root = Note(root.chroma)
        return tonic, intervals, root

    #### init / arg-parsing subroutines:
    @staticmethod
    def _detect_unique_and_repeated_intervals(intervals):
        unique_intervals = []
        repeated_intervals = []

        # loop through intervals and establish factor-degree uniques:
        for i, this_interval in enumerate(intervals):
            is_unique = True
            for existing_unique in unique_intervals:
                # compare in such a way that extendedinterval aren't equal to their compounds:
                if this_interval.factor_value == existing_unique.factor_value:
                    is_unique = False
                    break
            if is_unique:
                unique_intervals.append(this_interval)

            is_unique = True
            # compare to other intervals in the chord to determine repetition:
            other_intervals = [other_interval for j, other_interval in enumerate(intervals) if j != i] + [Unison]
            for other_interval in other_intervals:
                if this_interval.factor_value == other_interval.factor_value: # enharmonic equivalence
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
            if i.degree == 5 or i.valid_fifth:
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
            if third.degree == 3 or third.valid_third:
                factors[3] = IntervalDegree(third.value, 3)
            else:
                print(f"Irregular triad chord ({intervals}): {third} is not a valid third")
                this_degree = third.degree if third.degree is not None else third.expected_degree
                factors[this_degree] = IntervalDegree(third.value, this_degree)

            if fifth.degree == 5 or fifth.valid_fifth:
                factors[5] = IntervalDegree(fifth.value, 5)
            elif fifth.degree == 4 or fifth.valid_degree(4):
                # special case: add4 occurs before a per5 (but we don't allow this to be a 7th, so the chord ends here)
                factors[4] = IntervalDegree(fifth.value, 4)
                log(f'Detected an odd case: add4 chord, with intervals: \n{intervals}')
                assert num_notes == 4, "chords longer than tetrads should have be 11ths, not add4"
                fifth = intervals[2]
                assert fifth.valid_fifth, "detected an add4 chord without a perfect 5th"
                factors[5] = IntervalDegree(fifth.value, 5)
            else:
                print(f"Irregular triad chord ({intervals}): {fifth} is not a valid fifth/fourth")
                this_degree = fifth.degree if fifth.degree is not None else fifth.expected_degree
                factors[this_degree] = IntervalDegree(fifth.value, this_degree)

            if num_notes == 4:
                # this could be a sixth, seventh, or an add9
                # detect add9 first:
                i = intervals[2]
                if i.degree == 9 or i.valid_degree(9):
                    factors[9] = ExtendedInterval(i.value, 9)
                # common sevenths are more likely than sixths:
                elif i.degree == 7 or i.common_seventh:
                    factors[7] = IntervalDegree(i.value, 7)
                # but major sixths are more likely than dim7s:
                elif i.degree == 6 or i.valid_degree(6):
                    factors[6] = IntervalDegree(i.value, 6)
                # ...which we catch here:
                elif i.valid_seventh:
                    factors[7] = IntervalDegree(i.value, 7)

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

    @staticmethod
    def _detect_suffix_from_intervals(intervals):
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

    def _detect_sharp_preference(self, default=False): #tonic, quality='major', default=False):
        """detect if a chord should prefer sharp or flat labelling
        depending on its tonic and quality"""
        # if isinstance(tonic, str):
        #     tonic = Note(str)
        # assert isinstance(tonic, Note)
        # tonic_chord = Chord(tonic)

        # if quality in chord_names[(Maj3, Per5)]: # aliases for 'major':
        if self.major:
            if self.tonic in sharp_major_tonics:
                return True
            elif self.tonic in flat_major_tonics:
                return False
            else:
                return default
        # elif quality in chord_names[(Min3, Per5)]: # aliases for 'minor'
        elif self.minor:
            if self.tonic in sharp_minor_tonics:
                return True
            elif self.tonic in flat_minor_tonics:
                return False
            else:
                return default
        else:
            return default

    def _set_sharp_preference(self, prefer_sharps):
        """set the sharp preference of all notes inside this Chord,
        including the tonic, root, and constituent factors"""
        self.tonic._set_sharp_preference(prefer_sharps)
        self.root._set_sharp_preference(prefer_sharps)
        for n in self.notes:
            n._set_sharp_preference(prefer_sharps)
        for n in self.factors.values():
            n._set_sharp_preference(prefer_sharps)

        # reset name of chord to reflect preference:
        root_str = f'/{self.root.name}' if self.inverted else ''
        self.name = self.tonic.name + self.suffix + root_str


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

    @property
    def sharp_notes(self):
        """returns notes inside self, all with sharp preference"""
        return [Note(n.chroma, prefer_sharps=True) for n in self.notes]

    @property
    def flat_notes(self):
        """returns notes inside self, all with flat preference"""
        return [Note(n.chroma, prefer_sharps=False) for n in self.notes]

    def pairwise_consonance(self):
        pairwise = {}

        # include tonic as well in matrix:
        factors = [1] + [f for f, i in self.factor_intervals.items() if not isinstance(i, NullInterval)]
        intervals = [IntervalDegree(0)] + [i for f, i in self.factor_intervals.items() if not isinstance(i, NullInterval)]

        for xfactor, xinterval in zip(factors, intervals):
            for yfactor, yinterval in zip(factors, intervals):
                if xfactor != yfactor: # do not compare factors to themselves
                    if yfactor > xfactor:
                        # interval subtraction is directional: xinterval is the root
                        distance = yinterval - xinterval
                    else:
                        distance = xinterval - yinterval
                    pairwise[(self.factors[xfactor], self.factors[yfactor])] = distance.consonance

        return pairwise

    @property
    def consonance(self):
        """returns the weighted average consonance rating of this chord's intervals"""
        # establish the chord's overall consonance rating
        # by creating a matrix of the fundamental intervals in the chord
        # and averaging all of their consonances with one another

        pairwise = self.pairwise_consonance()

        # weighted average,
        count, total = 0, 0
        for pair, consonance in pairwise.items():
            if pair[0] == self.tonic:
                # count intervals where the tonic is root as triple:
                total += 3*consonance
                count += 3
            elif pair[1] == self.tonic:
                # and intervals containing the tonic as double:
                total += 2*consonance
                count += 2
                # total += consonance
                # count += 1
            else:
                total += consonance
                count += 1
        # final result:
        return round(total / count, 2)

    @property
    def rarity(self):
        """returns the (somewhat subjective) rarity of this chord as an integer,
        where 1=common, 2=uncommon, 3=rare, 4=very_rare, 5=legendary"""
        rarity_lists = [None, common_chord_suffixes, uncommon_chord_suffixes, rare_chord_suffixes, very_rare_chord_suffixes, legendary_chord_suffixes]
        for i in range(1, 6):
            if self.suffix in rarity_lists[i]:
                return i

    @property
    def relative_minor(self):
        # assert not self.minor, f'{self} is already minor, and therefore has no relative minor'
        assert self.major, f'{self} is not major, and therefore has no relative minor'
        rm_tonic = relative_minors[self.tonic.name]
        return Chord(rm_tonic, 'minor')

    @property
    def relative_major(self):
        # assert not self.major, f'{self} is already major, and therefore has no relative major'
        assert self.minor, f'{self} is not minor, and therefore has no relative major'
        rm_tonic = relative_majors[self.tonic.name]
        return Chord(rm_tonic)

    @property
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
        """Compares thoeretical equivalence across Chords,
        i.e. whether they have the same notes corresponding to the same factors"""
        return self.notes == other.notes

    # enharmonic equality:
    def __and__(self, other):
        """Compares enharmonic equivalence across Chords,
        i.e. whether they contain the exact same notes (but not necessarily in the same order)"""
        assert isinstance(other, Chord), 'Chords can only be enharmonically compared to other Chords'
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
        (and not values) of its notes, and encodes inversions differently to tonics"""
        hash_str = '/'.join([str(n.position) for n in self.inverted_notes])
        return hash(hash_str)

    @property
    def inverted_notes(self):
        """if this is an inverted chord, return the notes in their inverted order (from root),
        otherwise return them in the usual order (from tonic)"""
        if self.inverted:
            assert self.root in self.notes, f"Inversion error: specified root {self.root} not in {self.notes}"
            root_place = [i for i, n in enumerate(self.notes) if n == self.root][0]
            # so we rearrange the notes from ordering [0,1,2] to e.g. [1,2,0]:
            note_idxs = [(root_place + i) % len(self) for i in range(len(self))]
            note_list = [self.notes[i] for i in note_idxs]
        else:
            note_list = self.notes
        return note_list

    def __str__(self):
        note_list = self.inverted_notes
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

    @property
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
        print(self.properties)


# chord constructor from tonic and stacked intervals:
def StackedChord(tonic, stack):
    """Initialise a chord by a series of intervals each relative to the previous interval.
    e.g. StackedChord('C', Min3, Maj3) returns C major"""
    log(f'Building Chord from stacked intervals: {intervals}')
    tonic_intervals = intervals_from_tonic(stack)
    c = Chord(tonic, tonic_intervals)
    log(f'Relative to tonic, those are: {tonic_intervals}, which we call: {c.name}')
    return c


# automatic chord detection routine:
def matching_chords(notelist, score=False, allow_inversions=False):
    """given an iterable of Note or OctaveNote objects,
    determine the chords that those notes could belong to.

    returns an ordered dict with chords as keys,
    and (recall, precision) tuples as values for those chords.

    chords are returned in the order: perfect matches, partial matches, precise matches,
    where perfect matches have recall and precision = 1, partial matches have recall=1, and precise matches have precision=1
    (note that, for chord matching, recall is a more desirable characteristic than precision, despite the name)
    """

    # parse notelist's items, casting to Note if necessary, and find list of unique ones:
    unique_notes = []

    if isinstance(notelist, str):
        notelist = parse_out_note_names(notelist)

    for n in notelist:
        if isinstance(n, Note):
            note = Note(position=n.position)
        elif isinstance(n, int):
            note = Note(position=n)
        elif isinstance(n, str):
            note = Note(n)
        if note not in unique_notes:
            unique_notes.append(note)
    unique_notes = list(set(unique_notes))

    perfect_matches = {}
    precise_matches = {}
    partial_matches = {}

    for tonic in notes.chromatic_scale:
        for quality in chord_types:
            candidate = Chord(tonic, quality)

            # get precision and recall which are the two most important metrics to sort by
            precision, recall = precision_recall(unique_notes, candidate)
            # but also use a third, subjective value by which to tiebreak
            likelihood_score = 1.0

            ### we evaluate subjective likelihood value based on whatever I want:

            # less likely if tonic is not the first note in the notelist
            if candidate.tonic != notelist[0] and notelist[0] in candidate.notes:
                likelihood_score -= .2
                # initialise an inverted chord that we pass as match if it fits perfectly
                inversion = Chord(candidate.tonic, candidate.suffix, root=notelist[0])
            elif notelist[0] not in candidate.notes:
                # less lkely if the the notelist and candidate don't share a tonic:
                likelihood_score -= .1
                inversion = None
            else:
                inversion = None

            # non-major chords are slightly less likely:
            if not candidate.major:
                likelihood_score -= .1

            # less likely for rarer chord types
            if candidate.suffix in uncommon_chord_suffixes:
                likelihood_score -= .2
            elif candidate.suffix in rare_chord_suffixes:
                likelihood_score -= .3
            elif candidate.suffix in very_rare_chord_suffixes:
                likelihood_score -= .5
            elif candidate.suffix in legendary_chord_suffixes:
                likelihood_score -= .7

            # which dict does this chord candidate go to?
            if precision == 1 and recall == 1:
                target_dict = perfect_matches
            elif recall == 1:
                target_dict = partial_matches
            elif precision == 1:
                target_dict = precise_matches
            else:
                target_dict = None

            # add candidate to chosen dict:
            if target_dict is not None:
                ### troubleshooting
                if candidate in target_dict.keys():
                    print(f"Trying to add {candidate} to target_dict but it's already there")
                    for key in target_dict.keys():
                        if hash(key) == hash(candidate):
                            print(key)
                            import pdb; pdb.set_trace()
                ###

                target_dict[candidate] = (round(recall,1), round(precision,1), round(likelihood_score,1))

                if allow_inversions and (inversion is not None):
                    # add this inversion as well as the non-inverted chord, but make the inversion more likely
                    ### troubleshooting
                    if inversion in target_dict.keys():
                        print(f" And trying to add {inversion} to target_dict but it's already there")
                        for key in target_dict.keys():
                            if hash(key) == hash(inversion):
                                print(key)
                                import pdb; pdb.set_trace()
                    ### troubleshooting
                    target_dict[inversion] = (round(recall,1), round(precision,1), round(likelihood_score + .2, 1))

    # sort matches by their distinguishing values:
    # i.e. sort perfect matches by likelihood:
    perfect_match_list = sorted(perfect_matches.keys(), key=lambda x: perfect_matches[x][2], reverse=True)
    # but sort perfect recall items by precision (then by likelihood)
    partial_match_list = sorted(partial_matches.keys(), key=lambda x: (partial_matches[x][1], partial_matches[x][2]), reverse=True)
    # and sort perfect precision items by recall (then by likelihood)
    precise_match_list = sorted(precise_matches.keys(), key=lambda x: (precise_matches[x][0], precise_matches[x][2]), reverse=True)

    if score:
        # return chords and their (prec, rec, likelihood) scores
        perfect_matches = {name: perfect_matches[name] for name in perfect_match_list}
        partial_matches = {name: partial_matches[name] for name in partial_match_list}
        precise_matches = {name: precise_matches[name] for name in precise_match_list}

        # return concatenation of 3 groups:
        all_matches = perfect_matches
        all_matches.update(partial_matches)
        all_matches.update(precise_matches)
        return all_matches
    else:
        # just return the chords themselves

        return perfect_match_list + partial_match_list + precise_match_list

def most_likely_chord(notelist, score=False, perfect_only=False, allow_inversions=True):
    """makes a best guess at an unknown chord from a list of Note objects
    (or of objects that can be cast to Notes) and returns it.
    if score=True, also returns a tuple of that chord's (precision, recall, likelihood) values
    if perfect_only=True, only returns a match if its precision and recall are both 1"""
    # dict of matches and their (prec, rec) scores:
    matches = matching_chords(notelist, score=True, allow_inversions=allow_inversions)

    # match is the top match, or None if none were found
    match = list(matches.keys())[0] if len(matches) > 0 else None
    recall, precision, likelihood = matches[match]

    if score:
        if match is not None:
            if (not perfect_only) or (precision==1 and recall == 1):
                return match, (recall, precision, likelihood)
        else:
            return None, (0., 0., 0.)
    else:
        if (not perfect_only) or (precision==1 and recall == 1):
            return match
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

    test(most_likely_chord(['C', 'E', 'A']), Chord('Am/C'))
