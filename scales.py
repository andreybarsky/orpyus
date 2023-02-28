import pdb

import notes
from notes import Note, Note
from chords import Chord, chord_names, detect_sharp_preference
from util import log, test
from itertools import cycle
from collections import defaultdict
from intervals import *

# all accepted aliases for scale qualities - default suffix is listed first
key_names = defaultdict(lambda: ' (unknown key)',
   {(Maj2, Maj3, Per4, Per5, Maj6, Maj7): ['', 'maj', 'M', ' major'],
    (Maj2, Min3, Per4, Per5, Min6, Min7): ['m', 'min', ' natural minor', ' minor',],

    (Maj2, Maj3, Per4, Per5, Min6, Maj7): [' harmonic major', 'M harmonic', 'maj harmonic'],
    (Maj2, Min3, Per4, Per5, Min6, Maj7): [' harmonic minor', 'm harmonic'],
    (Maj2, Min3, Per4, Per5, Maj6, Maj7): [' melodic minor', 'm melodic'], # TBI? melodic minor descending uses the natural minor scale

    (Maj2, Maj3, Per5, Maj6): [' pentatonic', ' major pentatonic', 'maj pentatonic', ' pentatonic major'],
    (Min3, Per4, Per5, Min7): ['m pentatonic', ' minor pentatonic', ' pentatonic minor'],

    (Maj2, Per4, Per5, Maj6): [' blues major', ' blues major pentatonic', ' blues'],
    (Min3, Per4, Min6, Min7): [' blues minor', ' blues minor pentatonic', 'm blues'],

    (Min2, Maj2, Min3, Per4, Dim5, Per5, Min6, Maj6, Min7, Maj7): [' chromatic'],
    })

## dict mapping all accepted key quality names to lists of their intervals:
key_intervals = {}
# dict mapping valid whole names of keys to a tuple: (tonic, intervals)
whole_key_name_intervals = {}

for intervals, names in key_names.items():
    for key_name_alias in names:
        key_intervals[key_name_alias] = intervals
        # strip leading spaces for determining quality from string argument:
        # e.g. allow both ' minor' and 'minor',
        # so that we can parse both Key('C minor') and Key('C', 'minor')
        if len(key_name_alias) > 0 and key_name_alias[0] == ' ':
            key_intervals[key_name_alias[1:]] = intervals

        # build up whole-key-names (like 'C# minor')
        for c in notes.notes:
            # parse both flat and sharp note names:
            whole_name_strings = [f'{c.sharp_name}{key_name_alias}', f'{c.flat_name}{key_name_alias}']
            if len(key_name_alias) > 0 and key_name_alias[0] == ' ':
                whole_name_strings.append(f'{c.sharp_name}{key_name_alias[1:]}')
                whole_name_strings.append(f'{c.flat_name}{key_name_alias[1:]}')

            for whole_key_name in whole_name_strings:
                whole_key_name_intervals[whole_key_name] = (c, intervals)

# notes in order of which are flattened/sharpened in a key signature:
flat_order = ['B', 'E', 'A', 'D', 'G', 'C', 'F']
sharp_order = ['F', 'C', 'G', 'D', 'A', 'E', 'B']

# keys arranged vaguely in order of rarity, for auto key detection/searching:
common_key_suffixes = ['', 'm']
uncommon_key_suffixes = [' harmonic minor', 'pentatonic', 'm pentatonic']
rare_key_suffixes = [' harmonic major', ' melodic minor', ' blues major', ' blues minor']

class KeyNote(Note):
    def __init__(self, *args, key, **kwargs):
        super().__init__(*args, **kwargs)

        if isinstance(key, Key):
            self.key = key
        elif isinstance(key, str):
            self.key = Key(key)

        # inherit sharp preference from parent key:
        self.prefer_sharps = self.key.prefer_sharps
        self.name = notes.specific_note_name(self.position, prefer_sharps=self.prefer_sharps)

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
        super().__init__(*args, **kwargs)

        if isinstance(key, Key):
            self.key = key
        elif isinstance(key, str):
            self.key = Key(key)

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
    # TBI: modes??
    # TBI: key signature, sharp/flat detection
    def __init__(self, name, quality=None, prefer_sharps=None):
        """Initialise a Key from a name like 'D major' or 'C#m',
        or by passing a Note, Note, or string that can be cast to Note,
            (which we interpet as the key's tonic) and specifiying a quality
            like 'major', 'minor', 'harmonic', etc."""
        ### parse name:

        if quality is None: # assume major by default if quality is not given
            quality = 'major'

        # see if we can parse the first argument as a whole key name:
        if isinstance(name, str) and name in whole_key_name_intervals.keys():
            log(f'Initialising scale from whole key name: {name}')
            self.tonic, self.intervals = whole_key_name_intervals[name]
            # (we ignore the quality arg in this case)

        else:
            # get tonic from name argument:
            if isinstance(name, Note):
                log(f'Initialising scale from Note: {name}')
                self.tonic = name
            elif isinstance(name, Note):
                log(f'Initialising scale from Note: {name}')
                self.tonic = name.note
            elif isinstance(name, str):
                log(f'Initialising scale from string denoting tonic: {name}')
                self.tonic = Note(name)
            else:
                raise TypeError(f'Expected to initialise Key with tonic argument of type Note, Note, or str, but got: {type(name)}')
            # and get intervals from quality argument
            self.intervals = key_intervals[quality]

        # get common suffix from inverted dict:
        self.suffix = key_names[self.intervals][0]
        # and infer quality:
        self.major = (self.suffix in ['', ' pentatonic', ' blues major'])
        self.minor = (self.suffix in ['m', 'm pentatonic', ' blues minor', ' harmonic minor'])


        # figure out if we should prefer sharps or flats:
        self.prefer_sharps = detect_sharp_preference(self.tonic, self.suffix, default=True if prefer_sharps is None else prefer_sharps)

        # set tonic to use preferred sharp convention:
        self.tonic = KeyNote(self.tonic.name, key=self)

        # and name self accordingly:
        self.name = f'{self.tonic.name}{self.suffix}'

        # form notes in scale:
        self.scale = [self.tonic]
        for i in self.intervals:
            new_note = self.tonic + i
            self.scale.append(new_note)
        # what kind of scale are we?
        if len(self) == 7:
            self.type = 'diatonic'
        elif len(self) == 5:
            self.type = 'pentatonic'
        elif len(self) == 11:
            self.type = 'chromatic'
        else:
            self.type = f'{len(self)}-tonic' #  ???

        # build up chords within scale:
        self.chords = [self.build_triad(i) for i in range(1, len(self)+1)]
        log('Initialised key: {self} ({self.scale})')

    def build_triad(self, degree: int):
        """Returns the triad chord built on the notes of this scale, with
        specified degree as the chord root"""
        # assumed that only a diatonic scale will call this method
        # scales are 1-indexed which makes it hard to modso we correct here:

        root, third, fifth = self[degree], self[degree+2], self[degree+4]
        return KeyChord([root, third, fifth], key=self)

    def get_valid_chords(self):
        # loop through all possible chords and return the ones that are valid in this key:
        chord_hash = {}

        for intervals, names in chord_names.items():
            for note in self.scale:
                this_chord = KeyChord(note, intervals, key=self)
                # is it valid? assume it is and disquality it if not
                valid = True
                for note in this_chord.notes:
                    if note not in self.scale:
                        valid = False
                # add to our hash if it is:
                if valid:
                    if this_chord not in chord_hash:
                        chord_hash[this_chord] = 1
                    else:
                        chord_hash[this_chord] += 1

        return list(chord_hash.keys())

    def __contains__(self, item):
        """is this Chord or Note part of this key?"""
        if self.type == 'chromatic':
            return True # chromatic scale contains everything
        elif isinstance(item, Note):
            return item in self.scale
        elif isinstance(item, Chord):
            return item in self.chords

    def __getitem__(self, i):
        """Index scale notes by degree (where tonic=1)"""
        if i == 0:
            raise ValueError('Scales are 1-indexed, with the tonic corresponding to [1]')

        # wrap around if given i greater than the length of the scale:
        if i > len(self):
            i = ((i - 1) % len(self)) + 1

        return self.scale[i-1]

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
            assert self.type == other.type == 'diatonic'

            self_reference_key = self if self.major else self.relative_major()
            other_reference_key = other if other.major else other.relative_major()

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
        reference_key = self if self.major else self.relative_major()
        new_co5s_pos = (co5s_positions[reference_key] + value) % 12
        # instantiate new key object: (just in case???)
        new_key = co5s[new_co5s_pos]
        new_key = new_key if self.major else new_key.relative_minor()
        return Key(new_key.tonic, new_key.suffix)

    def counterclockwise(self, value=1):
        return self.clockwise(-value)

    def relative_minor(self):
        assert not self.minor, f'{self} is already minor, and therefore has no relative minor'
        rm_tonic = notes.relative_minors[self.tonic]
        return Key(rm_tonic, 'minor')

    def relative_major(self):
        assert not self.major, f'{self} is already major, and therefore has no relative major'
        rm_tonic = notes.relative_majors[self.tonic]
        return Key(rm_tonic)


def rate_keys(chordlist):
    """given an iterable of Chord objects,
    determine the keys that those chords could belong to"""

    ### check for common chords first:
    full_matches = []
    partial_matches = {}

    unique_chords = []
    for c in chordlist:
        if isinstance(c, Chord):
            unique_chords.append(c)
        elif isinstance(c, str):
            unique_chords.append(Chord(c))

    unique_chords = list(set(unique_chords))

    for tonic in notes.notes:
        for quality in common_key_suffixes + uncommon_key_suffixes + rare_key_suffixes:
            candidate = Key(tonic, quality)
            belongs = 0
            for chord in unique_chords:
                if chord in candidate.chords:
                    belongs += 1
            rating = belongs / len(unique_chords)
            # rating is 1 if every note in the notelist appears in the candidate chord

            if rating == 1 and len(candidate) == len(unique_chords):
                # one-to-one mapping, perfect match
                full_matches.append(candidate)
            else:
                if rating == 1 and len(candidate) > len(unique_chords):
                    # good match, but chord has some extra things in it
                    # penalise rating based on the difference in length
                    # (intersection over union?)
                    if len(candidate) > len(unique_chords):
                        specificity_penalty = len(unique_chords) / len(candidate)
                        rating *= specificity_penalty

                elif len(candidate) != len(unique_chords):
                    precision_penalty = 1 / abs(len(candidate) - len(unique_chords))
                    rating *= precision_penalty
                    # if len(candidate) > len(unique_notes):
                    #     # print('Candidate is longer than notelist')
                    # elif len(unique_notes) > len(candidate):
                    #     print('Notelist is longer than candidate')

                # uncommon chord types are inherently less likely:
                if candidate.suffix in uncommon_key_suffixes:
                    rating *= 0.99
                elif candidate.suffix in rare_key_suffixes:
                    rating *= 0.98

                partial_matches[candidate] = round(rating, 2)

    return full_matches, partial_matches

def detect_keys(chordlist, max=5, threshold=0.7):
    """return a list of the most likely keys that a notelist could belong to,
    with the very first in the list being a likely first guess"""
    key_matches, key_ratings = rate_keys(chordlist)
    if len(key_matches) > 0:
        return key_matches
    else:
        names, ratings = list(key_ratings.keys()), list(key_ratings.values())
        ranked_keys = sorted(names, key=lambda n: key_ratings[n], reverse=True)
        ranked_ratings = sorted(ratings, reverse=True)

        ranked_keys = [c for i, c in enumerate(ranked_keys) if ranked_ratings[i] > threshold]
        ranked_ratings = [r for i, r in enumerate(ranked_ratings) if r > threshold]

        # don't clip off keys with the same rating as those left in the list:
        truncated_ratings = ranked_ratings[:max]
        if (len(truncated_ratings) == max) and truncated_ratings[-1] == ranked_ratings[max]:
            final_ratings = [r for i, r in enumerate(ranked_ratings[max:]) if r == truncated_ratings[-1]]
            truncated_ratings.extend(final_ratings)
        truncated_keys = ranked_keys[:len(truncated_ratings)]
        return {c: r for c, r in zip(truncated_keys, truncated_ratings)}

def most_likely_key(chordlist, return_probability=False):
    result = detect_keys(chordlist, threshold=0)
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


# construct circle of fifths:
circle_of_fifths = {0: Key('C')}
for i in range(1,12):
    circle_of_fifths[i] = list(circle_of_fifths.values())[-1] + PerfectFifth
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
