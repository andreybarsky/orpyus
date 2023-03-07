import muse.notes as notes
from muse.notes import Note, OctaveNote
from muse.chords import Chord, chord_names, matching_chords, most_likely_chord, relative_minors, relative_majors
from muse.intervals import Interval, IntervalDegree, Min2, Maj2, Min3, Maj3, Per4, Per5, Min6, Maj6, Min7, Maj7
from muse.modes import interval_key_names, key_name_intervals, whole_key_name_intervals, mode_lookup, interval_mode_names, non_scale_interval_mode_names
import muse.parsing as parsing

from muse.util import log, test, precision_recall
from itertools import cycle
from collections import defaultdict
import pdb


# notes in order of which are flattened/sharpened in a key signature:
flat_order = ['B', 'E', 'A', 'D', 'G', 'C', 'F']
sharp_order = ['F', 'C', 'G', 'D', 'A', 'E', 'B']

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

class Key:

    # TBI: key signature, sharp/flat detection
    def __init__(self, arg1, quality=None, mode=None, prefer_sharps=None):
        """Initialise a Key by one of three input cases:
        1) arg1 is the full name of a key, like 'D major' or 'C#m',
            which can include modes like 'D dorian'
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
        self.tonic, self.suffix, self.intervals, self.mode_id = self._parse_input(arg1, quality, mode)

        # # get common suffix from first alias in key_names dict,
        # self.suffix = interval_key_names[self.intervals][0]

        # and infer quality flags from it:
        self.melodic = 'melodic' in self.suffix
        self.harmonic = 'harmonic' in self.suffix
        self.natural = (not self.melodic) and (not self.harmonic)
        if self.natural:
            self.major = (self.suffix == '') # (self.suffix in ['', ' pentatonic', ' blues major'])
            self.minor = (self.suffix == 'm')  #(self.suffix in ['m', 'm pentatonic', ' blues minor', ' harmonic minor'])
        else:
            self.major = (self.suffix[:3] == 'maj')
            self.minor = (self.suffix[:1] == 'm ')

        # figure out if we should prefer sharps or flats
        # by constructing chord over the tonic and querying it:
        naive_tonic_chord = Chord(self.tonic, 'major' if self.major else 'minor')
        self.prefer_sharps = naive_tonic_chord._detect_sharp_preference(default=False if prefer_sharps is None else prefer_sharps)

        # set tonic to use preferred sharp convention:
        self.tonic = KeyNote(self.tonic.name, key=self)

        # and name self accordingly:
        self.name = f'{self.tonic.name}{self.suffix}'

        # form notes in diatonic scale:
        self.scale = [self.tonic]
        for i in self.intervals:
            new_note = self.tonic + i
            self.scale.append(new_note)

        log('Initialised key: {self} ({self.scale})')

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
    def _parse_input(arg1, quality, mode):
        """Initialise a Key by one of two input cases:
        1) arg1 is the tonic of a key, either as a Note or a string denoting a Note:
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
        to get the 3rd mode of C harmonic minor

        2) arg1 is the full name of a key, like 'D major' or 'C#m',
            which can include modes like 'D dorian'
            or even exotic harmonic/melodic modes like 'D phrygian dominant'


        """

        #### this method must return: tonic, suffix, intervals, and mode_id

        ### case 1: arg1 is a tonic note, so we record it:
        if isinstance(arg1, Note) or isinstance(arg1, str) and parsing.is_valid_note_name(arg1):
            tonic = arg1 if isinstance(arg1, Note) else Note(arg1)

            # and then determine what we've been given for quality and mode:
            if isinstance(quality, str):
                # we have been passed quality, which can be a scale quality like 'major' or 'harmonic minor'
                # so first we check whether it is in our list of scale names:
                if quality in key_name_intervals.keys():
                    # get the appropriate scale intervals:
                    intervals = key_name_intervals[quality]
                    # and find the common scale suffix:
                    suffix = interval_key_names[intervals]
                elif quality in mode_name_intervals.keys():
                    intervals = 


        if isinstance(name, str):
            # catch a specific exemption:
            if 'harmonic' in name or 'melodic' in name:
                raise ValueError("Keys of quality 'melodic' or 'harmonic' must have major or minor specified explicitly")

        if quality is None: # assume major by default if quality is not given
            quality = 'major'

        # see if we can parse the first argument as a whole key name:
        if isinstance(name, str) and name in whole_key_name_intervals.keys():
            log(f'Initialising scale from whole key name: {name}')
            tonic, intervals = whole_key_name_intervals[name]
            # (we ignore the quality arg in this case)

        else:

            # get tonic from name argument:
            if isinstance(name, Note):
                log(f'Initialising scale from Note: {name}')
                tonic = name
                if isinstance(name, OctaveNote):
                    log(f'OctaveNote was passed to Key for init but we ignore its octave attr, since Keys are abstract')
            elif isinstance(name, str):
                log(f'Initialising scale from string denoting tonic: {name}')
                tonic = Note(name)
            else:
                raise TypeError(f'Expected to initialise Key with tonic argument of type Note, Note, or str, but got: {type(name)}')
            # and get intervals from quality argument
            intervals = key_name_intervals[quality]
        return tonic, intervals

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
        # loop through all possible chords and return the ones that are valid in this key:
        chord_hash = {}

        for intervals, names in chord_names.items():
            for note in self.scale:
                candidate_chord = KeyChord(note, intervals, key=self)
                # is it valid? assume it is and disquality it if not
                valid = True
                for note in candidate_chord.notes:
                    if note not in self.scale:
                        valid = False
                # add to our hash if it is:
                if valid:
                    if candidate_chord not in chord_hash:
                        chord_hash[candidate_chord] = 1
                    else:
                        chord_hash[candidate_chord] += 1

        chord_list = list(chord_hash.keys())

        # sort by rarity and then by consonance:
        chord_list = sorted(chord_list, key=lambda c: (-c.rarity, c.consonance), reverse=True)
        # return chord rarity, consonance tuple as stats:
        chord_stats = [(c, round(1-(c.rarity-1)/4,1), c.consonance) for c in chord_list]
        return chord_stats

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
        import pdb; pdb.set_trace()
        return Key(new_key.tonic, new_key.suffix)

    def counterclockwise(self, value=1):
        return self.clockwise(-value)

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


# def rate_keys(chordlist):
#     """given an iterable of Chord objects,
#     determine the keys that those chords could belong to"""
#
#     ### check for common chords first:
#     full_matches = []
#     partial_matches = {}
#
#     unique_chords = []
#     for c in chordlist:
#         if isinstance(c, Chord):
#             unique_chords.append(c)
#         elif isinstance(c, str):
#             unique_chords.append(Chord(c))
#
#     unique_chords = list(set(unique_chords))
#
#     for tonic in notes.notes:
#         for quality in common_key_suffixes + uncommon_key_suffixes + rare_key_suffixes:
#             candidate = Key(tonic, quality)
#             belongs = 0
#             for chord in unique_chords:
#                 if chord in candidate.chords:
#                     belongs += 1
#             rating = belongs / len(unique_chords)
#             # rating is 1 if every note in the notelist appears in the candidate chord
#
#             if rating == 1 and len(candidate) == len(unique_chords):
#                 # one-to-one mapping, perfect match
#                 full_matches.append(candidate)
#             else:
#                 if rating == 1 and len(candidate) > len(unique_chords):
#                     # good match, but chord has some extra things in it
#                     # penalise rating based on the difference in length
#                     # (intersection over union?)
#                     if len(candidate) > len(unique_chords):
#                         specificity_penalty = len(unique_chords) / len(candidate)
#                         rating *= specificity_penalty
#
#                 elif len(candidate) != len(unique_chords):
#                     precision_penalty = 1 / abs(len(candidate) - len(unique_chords))
#                     rating *= precision_penalty
#                     # if len(candidate) > len(unique_notes):
#                     #     # print('Candidate is longer than notelist')
#                     # elif len(unique_notes) > len(candidate):
#                     #     print('Notelist is longer than candidate')
#
#                 # uncommon chord types are inherently less likely:
#                 if candidate.suffix in uncommon_key_suffixes:
#                     rating *= 0.99
#                 elif candidate.suffix in rare_key_suffixes:
#                     rating *= 0.98
#
#                 partial_matches[candidate] = round(rating, 2)
#
#     return full_matches, partial_matches


# largely copy-pasted from chords.matching_chords:

#################### TBI (or completed)
...
def matching_keys(chordlist, by='note', score=False):
    """given an iterable of Chord objects,
    determine the Keys that those chords could belong to.

    returns an ordered dict with Keys as keys,
    and (precision, recall) tuples as values for those keys"""

    # parse the items in chordlist, casting to Chord if necessary, and find list of unique ones:
    # unique_chords = []
    # chord_weights = {}

    if by=='note':
        unique_notes = []
        note_weights = {}

    elif by=='chord':
        unique_chords = []
        chord_weights = {}
    else:
        raise Exception("matching_keys function must be by='note' or by='chord'")


    for i, c in enumerate(chordlist):
        if isinstance(c, Chord):
            chord = Chord(c.tonic, c.suffix)
        elif isinstance(c, str):
            chord = Chord(c)

        if by=='note':
            for n in chord.notes:
                if n not in note_weights.keys():
                    note_weights[n] = 1
                else:
                    note_weights[n] += 1
                if i == 0:
                    # notes in the first chord in the progression get weighted higher:
                    note_weights[n] += 2

        elif by=='chord':
            if chord not in chord_weights.keys():
                chord_weights[chord] = 1
            else:
                # increment weight of this chord for the final ranking:
                chord_weights[chord] += 1
            if i == 0:
                # first chord in the progression also gets weighted higher:
                chord_weights[chord] += 2



    perfect_matches = {}
    precise_matches = {}
    partial_matches = {}

    unique_target_items = list(chord_weights.keys()) if by=='chord' else list(note_weights.keys())


    # loop through all possible keys, instantiate them, and compare their members:
    for tonic in notes.chromatic_scale:
        for quality in key_types:

            candidate = Key(f'{tonic.name}{quality}')
            candidate_modes = candidate.modes()

            # get precision and recall which are the two most important metrics to sort by
            precision, recall = precision_recall(unique_chords, candidate)
            # but also use a third, subjective value by which to tiebreak
            likelihood_score = 1.

            ### we evaluate subjective likelihood value based on whatever I want:

            # non-major keys are slightly less likely:
            if not candidate.major:
                likelihood_score -= .1

            # less likely for rarer key types
            if candidate.suffix in uncommon_key_suffixes:
                likelihood_score -= .3
            elif candidate.suffix in rare_key_suffixes:
                likelihood_score -= .6

            # which dict does this key candidate go to?
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

                target_dict[candidate] = (round(precision,1), round(recall,1), round(likelihood_score,1))

                #### instead of inversions: modes?
                # if inversion is not None:
                #     # add this inversion as well as the non-inverted key, but make the inversion more likely
                #     ### troubleshooting
                #     if inversion in target_dict.keys():
                #         print(f" And trying to add {inversion} to target_dict but it's already there")
                #         for key in target_dict.keys():
                #             if hash(key) == hash(inversion):
                #                 print(key)
                #                 import pdb; pdb.set_trace()
                #     ### troubleshooting
                #     target_dict[inversion] = (round(precision,1), round(recall,1), round(likelihood_score + .2, 1))

    # sort matches by their distinguishing values:
    # i.e. perfect matches by likelihood:
    perfect_match_list = sorted(perfect_matches.keys(), key=lambda x: perfect_matches[x][2], reverse=True)
    # but  sort perfect recall items by precision (then by likelihood)
    partial_match_list = sorted(partial_matches.keys(), key=lambda x: (partial_matches[x][0], partial_matches[x][2]), reverse=True)
    # and sort perfect precision items by recall (then by likelihood)
    precise_match_list = sorted(precise_matches.keys(), key=lambda x: (precise_matches[x][1], precise_matches[x][2]), reverse=True)

    if score:
        # return keys and their (prec, rec, likelihood) scores
        perfect_matches = {name: perfect_matches[name] for name in perfect_match_list}
        partial_matches = {name: partial_matches[name] for name in partial_match_list}
        precise_matches = {name: precise_matches[name] for name in precise_match_list}

        # return concatenation of 3 groups:
        all_matches = perfect_matches
        all_matches.update(partial_matches)
        all_matches.update(precise_matches)
        return all_matches
    else:
        # just return the keys themselves

        return perfect_match_list + partial_match_list + precise_match_list

def most_likely_key(notelist, score=False, perfect_only=False):
    """makes a best guess at an unknown key from a list of Note objects
    (or of objects that can be cast to Notes) and returns it.
    if score=True, also returns a tuple of that key's (precision, recall, likelihood) values
    if perfect_only=True, only returns a match if its precision and recall are both 1"""
    # dict of matches and their (prec, rec) scores:
    matches = matching_keys(notelist, score=True)

    # match is the top match, or None if none were found
    match = list(matches.keys())[0] if len(matches) > 0 else None
    precision, recall, likelihood = matches[match]

    if score:
        if match is not None:
            if (not perfect_only) or (precision==1 and recall == 1):
                return match, (precision, recall, likelihood)
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


# construct circle of fifths:
circle_of_fifths = {0: Key('C')}
for i in range(1,12):
    circle_of_fifths[i] = list(circle_of_fifths.values())[-1] + Per5
co5s = circle_of_fifths

circle_of_fifths_positions = {value:key for key,value in co5s.items()}
co5s_positions = circle_of_fifths_positions





# by semitone, not degree
scale_semitone_names = {0: "tonic", # 1st
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


C = Key('C')
Cm = Key('Cm')

Db = Cs = Key('Db')
Csm = Dbm = Key('C#m')

D = Key('D')
Dm = Key('Dm')

Eb = Ds = Key('Eb')
Ebm = Dsm = Key('Ebm')

E = Key('E')
Em = Key('Em')

F = Key('F')
Fm = Key('Fm')

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
Bm = Key('Bm')
