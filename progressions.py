from intervals import *
from chords import Chord

roman_numerals = {'I':   1,
                  'II':  2,
                  'III': 3,
                  'IV':  4,
                  'V':   5,
                  'VI':  6,
                  'VII': 7}

class Progression:
    """A theoretical progression between unspecified chords,
    initialised as e.g. Progression('I', 'IV', 'iii', 'V')"""
    def __init__(self, degrees):
        self.intervals = []

        assert isinstance(degrees, (list, tuple)), "Expected a list or tuple of numeric degrees for Progression initialisation"

        ### determine progression quality from degree of the first chord:
        first_degree= degrees[0]
        if isinstance(root, str):
            if first_degree == first_degreeupper():
                self.quality = 'major'
            elif root == root.lower():
                self.quality = 'minor'
            else:
                raise ValueError(f'unexpected string passed to Progression init: {root}')
            first_degree_int = roman_numeral[first_degree.upper()]
        elif isinstance(first_degree, int):
            if root > 0:
                self.quality = 'major'
            elif root < 0:
                self.quality = 'minor'
            else:
                raise ValueError('Progression cannot include 0th degrees (no such thing)')
            first_degree_int = first_degree

        first_interval = Interval.from_degree(first_degree_int, quality=self.quality)

        self.intervals.append(first_interval)

        ### TBI: this whole block below needs work

        ### determine intervals from root
        for deg in degrees[1:]:
            if isinstance(deg, str):
                deg_int = roman_numerals[deg.upper()]
                deg_quality = 'minor' if deg == deg.lower() else 'major'
            elif isinstance(deg, int):
                deg_int = abs(deg)
                deg_quality = 'minor' if deg < 0 else 'major'
                if deg not in range(1,8):
                    raise ValueError(f'invalid progression degree: {deg}')

            # handle diminished scale-chords and overwrite deg quality for diatonic major-scale 7ths and minor-scale 2nds
            if (self.quality == 'major' and deg_int == 7) or (self.quality == 'minor' and deg_int == 2):
                if deg_quality == 'minor':
                    deg_quality = 'diminished'

            # elif isinstance(deg, int):
            #     # we interpret positive numbers as major degrees
            #     # and negative numbers as minor degrees
            #     deg_int = deg
            #     if self.quality == 'major' and deg_int == 7:
            #         if deg.lower() == deg:
            #             deg_quality = 'diminished'
            #         elif deg.upper() == deg:
            #             deg_quality = 'major'
            #     elif self.quality == 'minor' and deg_int == 2:
            #         if deg.lower() == deg:
            #             deg_quality = 'diminished'
            #         elif deg.upper() == deg:
            #             deg_quality = 'major'

            deg_interval = Interval.from_degree(deg_int, quality=deg_quality)
            self.intervals.append(deg_interval)

class ChordProgression(Progression):
    """Progression subtype defined using specific chords, also acts as container class for Chord objects"""
    def __init__(self, chords):
        # parse chords arg:
        self.chords = []
        self.chord_count = {}
        self.notes = []
        self.note_count = {}

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

                self.notes.extend(c.notes)
                for ch in c.notes:
                    if ch not in self.note_count.keys():
                        self.note_count[ch] = 1
                    else:
                        self.note_count[ch] += 1
            else:
                self.contains_duplicates = True
                self.chords.append(c)
                self.chord_count[c] += 1

        self.note_set = set(self.notes)

        #### tonic is just first chord's tonic for now:
        #### progressions that start on a non-tonic are TBI
        # self.tonic =

        ### determine chord intervals for back-compatibility with Progression parent class:
        # self.
        self.intervals = []
        # for chord in self.chords

    def __contains__(self, item):
        if isinstance(item, Chord):
            # efficient lookup by checking hash table keys:
            return item in self.chord_count.keys()
        elif isinstance(item, Note):
            return item in self.note_set

    def __str__(self):
        chord_set_str = ','.join(['♬ ' + c.name for c in self.chords])
        return f'𝄆 {chord_set_str} 𝄇'

    def __repr__(self):
        return str(self)

    def detect_key(self):
        ... # TBI
        pass



#
# class NoteSet:
#     """a chord voicing as a (sorted) set of Notes"""
#     def __init__(self, notes):
#         # loop through notes arg and validate/instantiate:
#         notes = [item if isinstance(item, Note) else Note(item) for item in notes]
#
#         self.notes = set(sorted(notes))
