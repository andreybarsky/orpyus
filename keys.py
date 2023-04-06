
import notes
from notes import Note, OctaveNote, NoteList
from chords import Chord, chord_names, matching_chords, most_likely_chord, relative_minors, relative_majors
from intervals import Interval, IntervalDegree, Min2, Maj2, Min3, Maj3, Per4, Per5, Min6, Maj6, Min7, Maj7
from progressions import ScaleDegree
from qualities import Quality
import scales
# from scales import interval_scale_names, scale_name_intervals, interval_mode_names, mode_name_intervals, mode_lookup, standard_scale_names  #, non_scale_interval_mode_names
import parsing as parsing
from util import log, test, precision_recall

from itertools import cycle
from collections import defaultdict, Counter
from copy import copy
import pdb

# natural notes in order of which are flattened/sharpened in a key signature:
flat_order = ['B', 'E', 'A', 'D', 'G', 'C', 'F']
sharp_order = ['F', 'C', 'G', 'D', 'A', 'E', 'B']



# TBI: valid_chords method should enumerate returned chords by scale degree

class Key:
    # TBI: key signature, sharp/flat detection
    def __init__(self, arg1, quality=None, prefer_sharps=None):
        """Initialise a Key by one of three input cases:
        1) arg1 is the full name of a key, like 'D major' or 'C#m',
            which can include natural modes like 'D dorian'
            or even exotic harmonic/melodic modes like 'D phrygian dominant'

        2) arg1 is the tonic of a key, either as a Note or a string denoting a Note:
            e.g. 'C' or 'D#',
            and either a 'quality' or 'mode' arg in addition.
        'quality' is parsed first, and must be one one of:
            a) a string denoting a scale type, like 'major' or 'minor' or 'harmonic minor'
            b) a string denoting a mode like 'dorian' or 'phrygian dominant'
            c) an iterable of intervals from tonic, such as: [Min2, Min3, Per4, Per5, Maj6, Min7],
                in which case we try to infer the scale's name/quality/mode from that
                (and call it an 'unknown scale' if that fails)

        if 'quality' is None, or refers to a base scale (one that is not a mode),
        we accept the 'mode' arg which should be an integer between 1 and 7 inclusive,
        specifying the degree of the mode of the desired modal scale.

        e.g.: Key('C', 'harmonic minor', mode=3)
        to get the 3rd mode of C harmonic minor"""

        ### parse input:
        self.tonic, self.suffix, self.scale_name, self.intervals, self.mode_id = self._parse_input(arg1, quality)

        self.base_scale, self.mode_degree = self.mode_id

        # a scale is 'standard' if it is not some exotic mode: i.e. natural minor is standard even though it is technically a mode of nat. major
        if self.scale_name in scales.standard_scales:
            self.standard = True
        else:
            self.standard = False

        # and infer quality flags from it:
        self.melodic = 'melodic' in self.base_scale
        self.harmonic = 'harmonic' in self.base_scale
        self.natural = (not self.melodic) and (not self.harmonic)
        # if self.natural:
        #     self.major = (self.suffix == '') # (self.suffix in ['', ' pentatonic', ' blues major'])
        #     self.minor = (self.suffix == 'm')  #(self.suffix in ['m', 'm pentatonic', ' blues minor', ' harmonic minor'])
        # else:
        #     self.major = (self.suffix[:3] == 'maj')
        #     self.minor = (self.suffix[:1] == 'm ')

        if self.intervals[1] == Maj3:
            self.major = True
            self.minor = False
        elif self.intervals[1] == Min3:
            self.major = False
            self.minor = True
        else:
            self.major = self.minor = False

        # figure out if we should prefer sharps or flats
        # by constructing chord over the tonic and querying it:
        naive_tonic_chord = Chord(self.tonic, 'minor' if self.minor else 'major')
        self.prefer_sharps = naive_tonic_chord._detect_sharp_preference(default=False if prefer_sharps is None else prefer_sharps)

        # set tonic to use preferred sharp convention:
        self.tonic = KeyNote(self.tonic.name, key=self)

        # name self accordingly:
        self.name = f'{self.tonic.name} {self.scale_name}'


        # form notes in diatonic scale:
        self.scale = NoteList([self.tonic])
        for i in self.intervals:
            new_note = self.tonic + i
            self.scale.append(new_note)

        log(f'Initialised key: {self} ({self.scale})')

    ### TBI: key signature construction
    ###################################
    @staticmethod
    def _detect_key_signature(scale):

        # haven't figured this out yet
        natural_tonic = self.tonic.name[0]

        # construct key signature:
        scale_note_positions = [notes.note_positions[s.name] for s in self.scale]
        sharp_scale = [parsing.note_names_sharp[s] for s in scale_note_positions]
        flat_scale = [parsing.note_names_flat[s] for s in scale_note_positions]
        for n in parsing.natural_note_names:
            if n not in sharp_scale:
                pass
        self.num_naturals = sum([s in parsing.natural_note_names for s in self.scale])
        self.num_sharps = ...
    ###################################

    @property
    def pentatonic(self):
        if self.major: # and self.natural?
            pent_scale = [self[s] for s in [1,2,3,5,6]]
        elif self.minor: # and self.natural?
            pent_scale = [self[s] for s in [1,3,4,5,7]]
        return pent_scale

    ### TBI: blues pentatonic scales?
    # (Maj2, Per4, Per5, Maj6): [' blues major', ' blues major pentatonic', ' blues'],
    # (Min3, Per4, Min6, Min7): [' blues minor', ' blues minor pentatonic', 'm blues'],

    @staticmethod
    def _parse_input(arg1, quality):
        """Initialise a Key by one of two input cases:
        1) arg1 is the tonic of a key, either as a Note or a string denoting a Note:
            e.g. 'C' or 'D#',
            and either a 'quality' or 'mode' arg in addition.

            'quality' is parsed first, and must be one one of:
                a) a string denoting a scale quality, like 'major' or 'minor' or 'harmonic minor'
                b) a string denoting a mode, like 'dorian' or 'aeolian' or 'phrygian dominant'
                c) an iterable of intervals from tonic, such as: [Min2, Min3, Per4, Per5, Maj6, Min7],
                    in which case we try to infer the scale's name/quality/mode from that
                    (and call it an 'unknown scale' if that fails)

        2) arg1 is the full name of a key, like 'D major' or 'C#m',
            which can include modes like 'D dorian'
            or even exotic harmonic/melodic modes like 'D phrygian dominant'
        """

        #### this method must return: tonic, suffix, scale_name, intervals, and mode_id

        assert isinstance(arg1, Note) or isinstance(arg1, str), "arg1 to Key init method must be a tonic or a string that starts with a tonic"
        ### case 1: arg1 is a tonic note
        if isinstance(arg1, Note) or parsing.is_valid_note_name(arg1):
            log(f'Scale instantiation case 1: we have been passed a tonic note ({arg1})')
            # cast as Note object:
            tonic = arg1 if isinstance(arg1, Note) else Note(arg1)

            if isinstance(quality, str):
                ### case 1a or 1b
                log(f'  Case 1a/b: Quality arg is a string that we take to denote key quality/mode: {quality}')

                if quality not in scales.mode_lookup.keys():
                    raise ValueError(f'{quality} does not seem to be a valid scale quality or mode name')
                mode_id = scales.mode_lookup[quality]
                log(f' Detected mode_id: {mode_id}')

                if quality in scales.scale_name_intervals.keys():
                    intervals_from_tonic = scales.scale_name_intervals[quality]
                    suffix = scales.interval_scale_names[intervals_from_tonic][0]
                    scale_name = scales.interval_scale_names[intervals_from_tonic][-1]
                    log(f' Detected (standard scale) intervals: {intervals_from_tonic}')
                elif quality in scales.mode_name_intervals.keys():
                    intervals_from_tonic = scales.mode_name_intervals[quality]
                    suffix = scales.interval_mode_names[intervals_from_tonic][0]
                    scale_name = scales.interval_mode_names[intervals_from_tonic][-1]
                    log(f' Detected (mode) intervals: {intervals_from_tonic}')

                log(f' Setting suffix as: {suffix}')

                return tonic, suffix, scale_name, intervals_from_tonic, mode_id

            elif isinstance(quality, (list, tuple)):
                ### case 1c: list of intervals passed after tonic; this block will return early
                log(f'  Case 1c: Quality arg passed as iterable of intervals: {quality}')
                # clean list of intervals:
                intervals_from_tonic = quality
                del quality # just in case
                if intervals_from_tonic[0].value == 0:
                    intervals_from_tonic = intervals_from_tonic[1:]
                    log(f'  (removed unison from start)')
                if intervals_from_tonic[-1].value % 12 == 0:
                    intervals_from_tonic = intervals_from_tonic[:-1]
                    log(f'  (removed octave from end)')
                assert len(intervals_from_tonic) == 6, f"""a key initialised by intervals requires exactly 6 intervals after cleaning,
                                                    but got {len(intervals_from_tonic)}: {intervals_from_tonic}"""
                interval_hashkey = tuple(intervals_from_tonic)
                # first search standard keys:
                if interval_hashkey in scales.interval_scale_names.keys():
                    log(f' Detected (standard) scale name: {scales.interval_scale_names[interval_hashkey][-1]}')
                    suffix = scales.interval_scale_names[interval_hashkey][0]
                    log(f' Setting suffix as: {suffix}')
                    scale_name = scales.interval_scale_names[interval_hashkey][-1]

                    mode_id = scales.mode_lookup[suffix]
                    log(f' Detected mode_id: {mode_id}')

                elif interval_hashkey in scales.interval_mode_names.keys():
                    log(f' Detected mode name: {scales.interval_mode_names[interval_hashkey][-1]}')
                    suffix = scales.interval_mode_names[interval_hashkey][0]
                    log(f' Setting suffix as: {suffix}')
                    scale_name = scales.interval_mode_names[interval_hashkey][-1]

                    mode_id = scales.mode_lookup[suffix]
                    log(f' Detected mode_id: {mode_id}')

                else:
                    print(f' +++ Received unusual series of intervals: {interval_hashkey}')
                    print(f' +++ Instantiating unknown key')
                    suffix = ' (unknown)'
                    scale_name = '(unknown scale)'
                    mode_id = None
                return tonic, suffix, scale_name, intervals_from_tonic, mode_id

            elif quality is None:
                log(f'    Case 1a but no quality arg explicitly passed; defaulting to major')
                return Key._parse_input(tonic, 'major')
            else:
                raise Exception(f'quality arg to Key init method is of unexpected type: {type(quality)}')


        ### case 2: arg1 is string but not simply a tonic name
        else:
            log(f'Scale instantiation case 2: we have been passed a string that is not a tonic note: ({arg1})')
            log(f'Trying to read it as a whole key name')
            if parsing.is_valid_note_name(arg1[:2]):
                note_name = arg1[:1]
                rest_idx = 2
            elif parsing.is_valid_note_name(arg1[0]):
                note_name = arg1[0]
                rest_idx = 1
            else:
                raise ValueError(f'Key init method received a string as first arg that does not contain a tonic its first two characters: {arg1}')

            # cast as Note object:
            tonic = Note(note_name)
            # check if space given between tonic and quality, skip if it has:
            if arg1[rest_idx] == ' ':
                rest_idx += 1
            # parse rest of string as quality:
            log(f'Detected tonic: {tonic}')
            if quality is not None:
                log(f'and ignoring quality arg: {quality}')
            quality = arg1[rest_idx:]
            log(f'using auto-detected quality: {quality}')

            mode_id = scales.mode_lookup[quality]
            log(f' Detected mode_id: {mode_id}')

            if quality in scales.scale_name_intervals.keys():
                intervals_from_tonic = scales.scale_name_intervals[quality]
                suffix = scales.interval_scale_names[intervals_from_tonic][0]
                log(f' Detected (standard scale) intervals: {intervals_from_tonic}')
                scale_name = scales.interval_scale_names[intervals_from_tonic][-1]
            elif quality in scales.mode_name_intervals.keys():
                intervals_from_tonic = scales.mode_name_intervals[quality]
                suffix = scales.interval_mode_names[intervals_from_tonic][0]
                log(f' Detected (mode) intervals: {intervals_from_tonic}')
                scale_name = scales.interval_mode_names[intervals_from_tonic][-1]

            log(f' Setting suffix as: {suffix}')

            return tonic, suffix, scale_name, intervals_from_tonic, mode_id

        # # and then determine what we've been given for quality and mode:
        # if isinstance(quality, str):
        #     print(f'  reading second arg (of type str) as quality: {quality}')
        #
        #     # we have been passed quality, which can be a scale quality like 'major' or 'harmonic minor'
        #     # so first we check whether it is in our list of scale names:
        #



        # if isinstance(name, str):
        #     # catch a specific exemption:
        #     if 'harmonic' in name or 'melodic' in name:
        #         raise ValueError("Keys of quality 'melodic' or 'harmonic' must have major or minor specified explicitly")


        # # see if we can parse the first argument as a whole key name:
        # if isinstance(name, str) and name in whole_key_name_intervals.keys():
        #     log(f'Initialising scale from whole key name: {name}')
        #     tonic, intervals = whole_key_name_intervals[name]
        #     # (we ignore the quality arg in this case)
        #
        # else:
        #
        #     # get tonic from name argument:
        #     if isinstance(name, Note):
        #         log(f'Initialising scale from Note: {name}')
        #         tonic = name
        #         if isinstance(name, OctaveNote):
        #             log(f'OctaveNote was passed to Key for init but we ignore its octave attr, since Keys are abstract')
        #     elif isinstance(name, str):
        #         log(f'Initialising scale from string denoting tonic: {name}')
        #         tonic = Note(name)
        #     else:
        #         raise TypeError(f'Expected to initialise Key with tonic argument of type Note, Note, or str, but got: {type(name)}')
        #     # and get intervals from quality argument
        #     intervals = key_name_intervals[quality]
        # return tonic, intervals

    def build_triad(self, degree: int):
        """Returns the triad chord built on the notes of this scale, with
        specified degree as the chord root"""
        # assumed that only a diatonic scale will call this method
        # scales are 1-indexed which makes it hard to modso we correct here:

        root, third, fifth = self[degree], self[degree+2], self[degree+4]
        # tonic is known so we can get chord quality from intervals:
        intervals = (IntervalDegree((third-root).value, degree=3), IntervalDegree((fifth-root).value, degree=5))
        if intervals in chord_names.keys():
            return Chord(root, chord_names[intervals][0])
        else:
            log(f'Building triad, trying to find an unnamed chord with intervals: {intervals}')
            match = most_likely_chord([root, third, fifth], perfect_only=True, allow_inversions=False)
            print(match.name)

        return KeyChord([root, third, fifth], key=self)

    @property
    def chords(self):
        return [self.build_triad(i) for i in range(1, len(self)+1)]

    @property
    def valid_chords(self):
        # property wrapper for get_valid_chords method with default args
        return self.get_valid_chords()

    def get_valid_chords(self, by='rarity', min_rarity=0.5, min_consonance=0.25, degrees=True):
        """by: one of 'rarity' or 'consonance'.
          determines which metric to rank the chords by.

        degrees: if True, returns a dict mapping scale degrees to dicts of chords built on that degree.
                 if False, returns a single dict of chords.
                 in both cases, the values in the chord dict are the scores by which they are ranked (rarity or consonance)."""
        # initialise output counters:
        if degrees:
            degree_chord_candidates = {d: Counter() for d in range(1, 8)}
        else:
            chord_candidates = Counter()

            # loop through all possible chords and return the ones that are valid in this key:
        for intervals, names in chord_names.items():
            for d, note in enumerate(self.scale):

                candidate_chord = KeyChord(note, intervals, key=self)
                # include only if it exceeds min rarity/consonance requirements:
                if candidate_chord.rarity >= min_rarity and candidate_chord.consonance >= min_consonance:
                    # is it valid? assume it is and disquality it if not
                    valid = True
                    for note in candidate_chord.notes:
                        if note not in self.scale:
                            valid = False
                    # add to our hash if it is:
                    if valid:
                        if degrees:
                            degree_chord_candidates[d+1].update([candidate_chord])
                        else:
                            chord_candidates.update([candidate_chord])

                        # if candidate_chord not in chord_hash:
                        #     chord_hash[candidate_chord] = 1
                        # else:
                        #     chord_hash[candidate_chord] += 1

        # now we sort the output dict/s by rarity or consonance
        if degrees:
            degree_chord_stats = {}
            for d in degree_chord_candidates.keys():
                degree_chords = degree_chord_candidates[d].keys()
                chord_list = list(degree_chords)

                if by=='rarity':
                    # sort by rarity and then by consonance:
                    chord_list = sorted(chord_list, key=lambda c: (-c.rarity, c.consonance), reverse=True)
                elif by=='consonance':
                    # sort by rarity and then by consonance:
                    chord_list = sorted(chord_list, key=lambda c: (c.consonance, -c.rarity), reverse=True)
                else:
                    raise Exception("Key.valid_chords method requires arg 'by' to be one of: 'rarity' or 'consonance'")

                # return chord rarity, consonance tuple as stats:
                chord_stats = [(c, round(1-(c.rarity-1)/4,1), c.consonance) for c in chord_list]
                degree_chord_stats[d] = chord_stats
            return degree_chord_stats

        else:
            # not broken up by degrees, just return one big chord list:
            chord_list = list(chord_candidates.keys())
            if by=='rarity':
                # sort by rarity and then by consonance:
                chord_list = sorted(chord_list, key=lambda c: (-c.rarity, c.consonance), reverse=True)
            elif by=='consonance':
                # sort by rarity and then by consonance:
                chord_list = sorted(chord_list, key=lambda c: (c.consonance, -c.rarity), reverse=True)
            else:
                raise Exception("Key.valid_chords method requires arg 'by' to be one of: 'rarity' or 'consonance'")

            # return chord rarity, consonance tuple as stats:
            chord_stats = [(c, round(1-(c.rarity-1)/4,1), c.consonance) for c in chord_list]
            return chord_stats


    @property
    def relative_minor(self):
        assert not self.minor, f'{self} is already minor, and therefore has no relative minor'
        rm_tonic_name = relative_minors[self.tonic.name]
        return Key(rm_tonic_name, 'minor')

    @property
    def relative_major(self):
        assert not self.major, f'{self} is already major, and therefore has no relative major'
        rm_tonic_name = relative_majors[self.tonic.name]
        return Key(rm_tonic_name)

    def __contains__(self, item):
        """is this Chord or Note part of this key?"""
        if isinstance(item, Note):
            return item in self.scale
        elif isinstance(item, Chord):
            return item in self.chords

    def __getitem__(self, i):
        """Index scale notes by degree (where tonic=1)"""
        # output = []
        # for i in idxs:
        if i == 0:
            raise ValueError('Scales are 1-indexed, with the tonic corresponding to [1]')

        # wrap around if given i greater than the length of the scale:
        if i > len(self):
            i = ((i - 1) % len(self)) + 1

        return self.scale[i-1]
        #     output.append(self.scale[i-1])
        # if len(output) == 1:
        #     return output[0] # if indexed by only a single value, return only a single value
        # else:
        #     return output # else return a list of equal length to indexes

    def __call__(self, i):
        """Index scale chords by degree (where tonic=1)"""
        if i == 0:
            raise ValueError('Scales are 1-indexed, with the tonic corresponding to [1]')
        if i > len(self):
            i = ((i - 1) % len(self)) + 1
        return self.chords[i-1]

    def __str__(self):
        return f'𝄞{self.name}'

    def __repr__(self):
        return str(self)

    def __len__(self):
        return len(self.scale)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        """Keys are equal if they contain the exact same notes"""
        # obviously false if they contain different numbers of notes:
        assert isinstance(other, Key)
        if len(self) != len(other):
            return False
        else:
            log(f'Key equivalence comparison between: {self.name} and {other.name}')
            for i in range(len(self)):
                log(f'Comparing item {i+1}/{len(self)}: {self[i+1]} vs {other[i+1]}')
                if self[i+1] != other[i+1]:
                    return False # break out of loop if we detect a difference
            return True

    def __add__(self, other: int):
        """if other is an integer, move the key clockwise that many steps around the circle of fifths
        but if other is an Interval, transpose it up that many steps"""
        if isinstance(other, Interval):
            new_tonic = self.tonic + other
            return Key(f'{new_tonic.name}{self.suffix}')
        elif isinstance(other, int):
            return self.clockwise(other)
        else:
            raise TypeError('Only integers and intervals can be added to Keys')

    def __sub__(self, other):
        """if other is an integer, move the key counterclockwise that many steps around the circle of fifths
        or if other is an Interval, transpose it down that many steps
        or if other is another Key, get distance along circle of fifths"""

        if isinstance(other, int):
            # counterclockwise movement around Co5s
            return self.counterclockwise(other)
        elif isinstance(other, (int, Interval)):
            # transposition by interval semitones
            new_tonic = self.tonic - other
            return Key(f'{new_tonic.name}{self.suffix}')
        elif isinstance(other, Key):
            # distance from other key along Co5s

            self_reference_key = self if self.major else self.relative_major
            other_reference_key = other if other.major else other.relative_major

            self_pos = co5s_positions[self_reference_key]
            other_pos = co5s_positions[other_reference_key]
            clockwise_distance = (other_pos - self_pos) % 12
            counterclockwise_distance = (self_pos - other_pos) % 12

            distance = float(min([clockwise_distance, counterclockwise_distance]))
            # if one key is major and the other minor, add a half-step of distance:
            if self.major != other.major:
                distance += 0.5

            return min([clockwise_distance, counterclockwise_distance])

    def clockwise(self, value=1):
        """fetch the next key from clockwise around the circle of fifths,
        or if value>1, go clockwise that many steps"""
        reference_key = self if self.major else self.relative_major
        new_co5s_pos = (co5s_positions[reference_key] + value) % 12
        # instantiate new key object: (just in case???)
        new_key = co5s[new_co5s_pos]
        new_key = new_key if self.major else new_key.relative_minor
        pdb.set_trace()
        return Key(new_key.tonic, new_key.suffix)

    def counterclockwise(self, value=1):
        return self.clockwise(-value)



    def __invert__(self):
        """~ operator returns the relative major/minor of a key"""
        if self.major:
            return self.relative_minor
        elif self.minor:
            return self.relative_major
        else:
            return self





class KeyNote(Note):
    def __init__(self, *args, key, **kwargs):
        super().__init__(*args, **kwargs)

        if isinstance(key, Key):
            self.key = key
        elif isinstance(key, str):
            self.key = Key(key)

        # inherit sharp preference from parent key:
        self.prefer_sharps = self.key.prefer_sharps
        self.name = notes.accidental_note_name(self.position, prefer_sharps=self.prefer_sharps)

    def __add__(self, other):
        # transposing a KeyNote stays within the same key:
        result = super().__add__(other)
        return KeyNote(result.name, key=self.key)

    def __sub__(self, other):
        # transposing a KeyNote stays within the same key:
        if isinstance(other, (int, Interval)):
            result = super().__sub__(other)
            return KeyNote(result.name, key=self.key)
        else:
            assert isinstance(other, Note)
            # but subtracting by another note still just returns an interval:
            return super().__sub__(other)

class KeyChord(Chord):
    def __init__(self, *args, key, **kwargs):


        # pointer to the key that this chord is a part of:
        if isinstance(key, Key):
            self.key = key
        elif isinstance(key, str):
            self.key = Key(key)

        super().__init__(*args, **kwargs)

        # inherit sharp preference from parent key:
        self._set_sharp_preference(self.key.prefer_sharps)


    def __add__(self, other):
        # transposing a KeyChord stays within the same key:
        # if isinstance(other, (int, Interval)):
        result = super().__add__(other)
        return KeyChord(result.name, key=self.key)
        # else:
            # return super().__sub__(other)

    def __sub__(self, other):
        # transposing a KeyChord stays within the same key:
        if isinstance(other, (int, Interval)):
            result = super().__sub__(other)
            return KeyChord(result.name, key=self.key)
        else:
            assert isinstance(other, Chord)
            # but subtracting by another chord still just returns an interval:
            return super().__sub__(other)


def matching_keys(target, by='note', input_as='chords', modes=True, score=True, min_recall=0.8, min_precision=0.3, max_results=5):
    """given a target iterable of Chord or Note objects,
    determine the Keys that those could belong to.

    we rank the returned candidate Keys in order of: recall, precision, then a tiebreaker metric
    that we call 'likelihood'. this is a series of fuzzy notions about which keys are more common.
    (major and minor keys are more likely than exotic modes, etc.)

    arguments:
      -by: one of 'note' (default) or 'chord'.
        if by note, we match the notes given in target to the notes of each candidate key.
        if by chord, we match the chords directly to the triad chords of each candidate key.

      -input_as: one of 'chords' (default) or 'notes'.
        if by chords, we assume the target is an iterable of Chord objects, or strings that cast to Chord objects.
        if by notes, we take the target to be an iterable of Note objects instead.
          (note that by=='chord' is incompatible with input_as=='notes')

      -modes: boolean (True by default)
        if True, we search all possible modes of the four foundational 'base' scales.
        if False, we search only the standard scales (which includes a few non-base modes, e.g. natural minor)

      -score: boolean (True by default)
        if True, we return the matching candidate keys as an ordered dict, linking keys to score tuples
          ordered as (recall, precision, likelihood), and ranked in that order, with perfect-recall candidates first.
        if False, we return matching candidate keys in the same order, but as a simple list, without score information.

      -min_recall, min_precision: float (in range 0-1)
        the minimum recall-score and precision-score required for a candidate key to count as a match.
          all returned candidates are still ranked, with perfect matches first, but this allows us to truncate.
      -max_results: int
        the maximum number of results to return. simply truncates the returned object
      """

    # parse the items in target, casting to Chord if necessary, and find list of unique ones:
    # unique_chords = []
    # chord_weights = {}

    # if by=='note':
    #     unique_notes = []
    #     note_weights = {}
    #
    # elif by=='chord':
    #     unique_chords = []
    #     chord_weights = {}
    # else:
    #     raise Exception("matching_keys function must be by='note' or by='chord'")
    # target_items = Counter()

    if input_as=='chords':
        # parse the target iterable, which should be a list/tuple of chord-likes
        assert isinstance(target, (list, tuple)), f"Expected an iterable of Chords but got: {type(target)}"
        chordlist = [Chord(c) for c in target]

        if by=='note':
            # break down the input chordlist into all its constituent notes:
            # straight list of all notes in the chords given
            notelist = []
            for i, chord in enumerate(chordlist):
                notelist.extend(chord.notes)

            # hash the notelist and store their frequencies as weights:
            target_items = Counter(notelist)

            # increase the weight of the tonic note slightly:
            target_tonic = chordlist[0].tonic
            target_items[target_tonic] += 1
        elif by=='chord':
            # search the chord list directly
            target_items = Counter(chordlist)
            # increase the weight of the first chord slightly:
            target_tonic = chordlist[0]
            target_items[target_tonic] += 1

    elif input_as=='notes':
        # notably: incompatible with by=='chords'
        if by=='chord':
            raise Exception(f"matching_keys input_as=='notes' is incompatible with by=='chord'")
        assert by=='note', f"matching_keys got arg input_as=='notes', but is not by=='note'. received by=={by}"

        # could be a list/tuple of note-likes, or else a string that must be parsed out:
        if isinstance(target, str):
            note_names = parse_out_note_names(target)
            notelist = [Note(n) for n in note_names]
        else:
            assert isinstance(target, (list, tuple)), f"Expected an iterable of Notes but got: {type(target)}"
            notelist = [Note(n) for n in target]

        target_items = Counter(notelist)

        # increase the weight of the first note slightly:
        target_tonic = notelist[0]
        target_items[target_tonic] += 1
    else:
        raise Exception(f"'input_as' should be one of: 'notes' or 'chords', but got: {input_as}")

    # for i, c in enumerate(chordlist):
    #     if isinstance(c, Chord):
    #         chord = Chord(c.tonic, c.suffix)
    #     elif isinstance(c, str):
    #         chord = Chord(c)
    #
    #     if i == 0:
    #         target_tonic = chord.tonic
    #
    #     if by=='note':
    #         for j, n in enumerate(chord.notes):
    #             if n not in note_weights.keys():
    #                 note_weights[n] = 1
    #             else:
    #                 note_weights[n] += 1
    #
    #             if i == 0:
    #                 if j == 0:
    #                     # tonic of the first chord gets weighted higher:
    #                     note_weights[n] += 3
    #                 else:
    #                     # other notes in the first chord in the progression get weighted slightly higher:
    #                     note_weights[n] += 2
    #
    #     elif by=='chord':
    #         if chord not in chord_weights.keys():
    #             chord_weights[chord] = 1
    #         else:
    #             # increment weight of this chord for the final ranking:
    #             chord_weights[chord] += 1
    #         if i == 0:
    #             # first chord in the progression also gets weighted higher:
    #             chord_weights[chord] += 2




    # the keys of the hash are also the set of unique member items:
    unique_target_items = list(target_items.keys())

    # build the list of candidates by looping through all possible keys and instantiating them:
    candidates = []
    unique_candidates = set([])
    for tonic in notes.chromatic_scale:
        for quality in scales.standard_scales:
            candidate = Key(tonic.name, quality)
            candidates.append(candidate)

            if candidate not in unique_candidates:
                unique_candidates.add(candidate)
            else:
                print(f'Trying to add key with tonic {tonic} and quality {quality} as {candidate}, but already in unique_candidates')
                pdb.set_trace()
    # if searching modes, use the (non-tonic) modes of base scales as well:
    log('Done with standard scales')
    if modes:
        log('Now doing modes')
        for tonic in notes.chromatic_scale:
            log(f'Modes of tonic {tonic}')
            for base_quality in scales.base_scales:
                log(f'Modes of quality {base_quality}')
                degrees_to_intervals = scales.get_modes(base_quality)
                for degree, intervals in degrees_to_intervals.items():
                    log(f'Mode degree {degree}: {intervals}')
                    log(f'  Called: "{scales.mode_idx_names[base_quality][degree][0]}"')
                    if tuple(intervals) not in scales.interval_scale_names.keys(): # exclude those modes that are already standard scales
                        candidate = Key(f'{tonic.name}', intervals)
                        if candidate not in unique_candidates:
                            unique_candidates.add(candidate)
                        else:
                            print(f'Trying to add key with tonic {tonic} and quality {quality} as {candidate}, but already in unique_candidates')
                            clash = [k for k in unique_candidates if hash(k) == hash(candidate)][0]
                            print(f'as: {clash}')
                            pdb.set_trace()
                        candidates.append(candidate)

    # item_weights = chord_weights if by=='chord' else note_weights

    # start comparing candidates to the target and looking for matches
    perfect_matches = {}
    precise_matches = {}
    partial_matches = {}
    for candidate in candidates:
        log(f'Checking candidate: {candidate}')

        # copy the weights dict so we can weight the candidate's tonic as slightly higher:
        this_cand_weights = copy(target_items)

        if by=='note':
            # up-weight the candidate scale tonic note:
            candidate_tonic = candidate.tonic
            candidate_items = candidate.scale
        if by=='chord':
            # up-weight the candidate scale tonic chord:
            candidate_tonic = candidate.chords[0]
            candidate_items = candidate.get_valid_chords(degrees=False)

        # up-weight:
        this_cand_weights.update([candidate_tonic])

        # calculate precision and recall (the two most important metrics to sort by)
        precision, recall = precision_recall(unique_target_items, candidate_items, weights=this_cand_weights)


        # but also use a third, subjective value by which to tiebreak
        likelihood_score = 1.

        ### we evaluate subjective likelihood value based on whatever I want:

        # perfect likelihood only if the candidate and chordlist share a tonic:
        if candidate_tonic != target_tonic:
            likelihood_score -= .3

        # non-major keys are slightly less likely:
        if not candidate.major:
            likelihood_score -= .1
        # non-standard keys are even less likely:
        if not candidate.standard:
            likelihood_score -= .2

        # less likely for rarer key types
        if candidate.suffix in scales.common_suffixes:
            pass
        elif candidate.suffix in scales.uncommon_suffixes:
            likelihood_score -= .2
        elif candidate.suffix in scales.rare_suffixes:
            likelihood_score -= .3
        else:
            log(f'{candidate} is some weird mode')
            likelihood_score -= .4
            # raise Exception(f'Suffix {candidate.suffix} has no rarity')

        # which dict does this key candidate go to?
        if precision == 1 and recall == 1:
            target_dict = perfect_matches
        elif recall == 1 and precision >= min_precision:
            target_dict = partial_matches
        elif precision == 1 and recall >= min_recall:
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
                        pdb.set_trace()
            ###
            target_dict[candidate] = (round(recall,1), round(precision,1), round(likelihood_score,1))


    # sort matches by their distinguishing values:
    # i.e. perfect matches by likelihood:
    perfect_match_list = sorted(perfect_matches.keys(), key=lambda x: perfect_matches[x][2], reverse=True)
    # but  sort perfect recall items by precision (then by likelihood)
    partial_match_list = sorted(partial_matches.keys(), key=lambda x: (partial_matches[x][1], partial_matches[x][2]), reverse=True)
    # and sort perfect precision items by recall (then by likelihood)
    precise_match_list = sorted(precise_matches.keys(), key=lambda x: (precise_matches[x][0], precise_matches[x][2]), reverse=True)

    if score:
        # return keys and their (prec, rec, likelihood) scores
        perfect_matches = {name: perfect_matches[name] for name in perfect_match_list}
        partial_matches = {name: partial_matches[name] for name in partial_match_list}
        precise_matches = {name: precise_matches[name] for name in precise_match_list}

        # return concatenation of 3 groups:
        all_matches = perfect_matches
        all_matches.update(partial_matches)
        all_matches.update(precise_matches)

        if max_results is None:
            return all_matches
        else:
            # awkward way to truncate a dict:
            trunc_matches = {k : all_matches[k] for k in list(all_matches.keys())[:max_results]}
            return trunc_matches
    else:
        # just return the keys themselves

        return (perfect_match_list + partial_match_list + precise_match_list)[:max_results]

def most_likely_key(notelist, score=False, by='note', modes=True, perfect_only=False):
    """makes a best guess at an unknown key from a list of Note objects
    (or of objects that can be cast to Notes) and returns it.
    if score=True, also returns a tuple of that key's (precision, recall, likelihood) values
    if perfect_only=True, only returns a match if its precision and recall are both 1"""
    # dict of matches and their (prec, rec) scores:
    matches = matching_keys(notelist, modes=modes, by=by, score=True)

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



uncommon_mode_suffixes = [] # modes of melodic/harmonic minor keys
rare_mode_suffixes = [] # modes of melodic/harmonic major keys

# def detect_keys(chordlist, max=5, threshold=0.7):
#     """return a list of the most likely keys that a notelist could belong to,
#     with the very first in the list being a likely first guess"""
#     key_matches, key_ratings = rate_keys(chordlist)
#     if len(key_matches) > 0:
#         return key_matches
#     else:
#         names, ratings = list(key_ratings.keys()), list(key_ratings.values())
#         ranked_keys = sorted(names, key=lambda n: key_ratings[n], reverse=True)
#         ranked_ratings = sorted(ratings, reverse=True)
#
#         ranked_keys = [c for i, c in enumerate(ranked_keys) if ranked_ratings[i] > threshold]
#         ranked_ratings = [r for i, r in enumerate(ranked_ratings) if r > threshold]
#
#         # don't clip off keys with the same rating as those left in the list:
#         truncated_ratings = ranked_ratings[:max]
#         if (len(truncated_ratings) == max) and truncated_ratings[-1] == ranked_ratings[max]:
#             final_ratings = [r for i, r in enumerate(ranked_ratings[max:]) if r == truncated_ratings[-1]]
#             truncated_ratings.extend(final_ratings)
#         truncated_keys = ranked_keys[:len(truncated_ratings)]
#         return {c: r for c, r in zip(truncated_keys, truncated_ratings)}
#
# def most_likely_key(chordlist, return_probability=False):
#     result = detect_keys(chordlist, threshold=0)
#     if isinstance(result, list):
#         # full match, most common chords first
#         probability = 1.00
#         c = result[0]
#     else:
#         c = list(result.keys())[0]
#         probability = list(result.values())[0]
#     if return_probability:
#         return c, probability
#     else:
#         return c




def unit_test():
    # test key init cases:
    # 1a: init by tonic, quality, vs 2: init by whole key name
    test(Key('A', 'minor'), Key('Am'))
    # 1b: init by tonic, mode name
    test(Key('A', 'aeolian'), Key('Am'))
    # 1c: init by tonic, intervals
    test(Key('A', [Maj2, Min3, Per4, Per5, Min6, Min7]), Key('Am'))
    # 2: init by whole key/mode name:
    test(Key('A aeolian'), Key('Am'))

    # test initialisation of exotic mode:
    test(Key('A', [Min2, Maj3, Per4, Per5, Min6, Min7]), Key('A phrygian dominant'))
    test(Key('A', 'athenian'), Key('A melodic minor'))

    # test ignoring of quality arg:
    test(Key('A dorian', 'minor'), Key('A', 'dorian'))

    # test valid chords:
    print('Testing valid_chords')
    print('Valid chords of Am:')
    Am_chords = Key('Am').get_valid_chords(degrees=False)
    print('\n'.join(Am_chords))

    print('Valid chords of D# dorian, by degree:')
    Ddor_chords = Key('D# dorian').valid_chords
    for deg in range(1, 8):
        print(f'Degree {deg}:')
        print('\n'.join(Ddor_chords[deg]))

    # test matching keys:
    print('Testing matching_keys')
    matching_keys(['D', 'A', 'Bm', 'G'], modes=False)
    matching_keys(['Am', 'F5', 'G', 'E'], modes=True)
    matching_keys(['Am', 'F5', 'G', 'E'], by='chord')
    matching_keys(['Am', 'F5', 'G', 'E'], by='note')
    matching_keys(['A', 'F', 'G', 'E'], input_as='notes', by='note')
    matching_keys('AFGEbC', input_as='notes', by='note')
    matching_keys(['A', 'F', 'G', 'E'], input_as='notes', by='chord') # should error



if __name__ == '__main__':
    unit_test()


else:
    # construct circle of fifths:
    circle_of_fifths = {0: Key('C')}
    for i in range(1,12):
        circle_of_fifths[i] = list(circle_of_fifths.values())[-1] + Per5
    co5s = circle_of_fifths

    circle_of_fifths_positions = {k:pos for pos,k in co5s.items()}
    co5s_positions = circle_of_fifths_positions

    minor_co5s = {pos: k.relative_minor for pos,k in co5s.items()}
    minor_co5s_positions = {k: pos for pos,k in minor_co5s.items()}





    # by semitone, not degree
    scale_function_names = {0: "tonic", # 1st
                            2: "supertonic", # 2nd
                            3: "mediant", # 3rd (minor)
                            4: "mediant", # 3rd (major)
                            5: "subdominant", # 4th
                            7: "dominant", # 5th
                            8: "submediant", # 6th (minor)
                            9: "submediant", # 6th (major)
                            10: "subtonic", # 7th (minor)
                            11: "leading tone", # 7th (major)
                            }


    C = Bs = Key('C')
    Cm = Bsm = Key('Cm')

    Db = Cs = Key('Db')
    Csm = Dbm = Key('C#m')

    D = Key('D')
    Dm = Key('Dm')

    Eb = Ds = Key('Eb')
    Ebm = Dsm = Key('Ebm')

    E = Fb = Key('E')
    Em = Fbm = Key('Em')

    F = Es = Key('F')
    Fm = Esm = Key('Fm')

    Gb = Fs = Key('Gb')
    Fsm = Gbm = Key('F#m')

    G = Key('G')
    Gm = Key('Gm')

    Ab = Gs = Key('Ab')
    Gsm = Abm = Key('G#m')

    A = Key('A')
    Am = Key('Am')

    Bb = As = Key('Bb')
    Bbm = Asm = Key('Bbm')

    B = Cb = Key('B')
    Bm = Cbm = Key('Bm')
