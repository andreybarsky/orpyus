# from intervals import *
from chords import Chord
from qualities import Major, Minor, Perfect, Diminished, parse_chord_qualifiers
from scales import ScaleDegree, Scale, scale_name_intervals
from util import reduce_aliases, reverse_dict, test
from parsing import roman_numerals, numerals_roman




# # scrap this for a more theoretical approach?
# cadence_finality = {(5, 1): 1,   # authentic cadence
#                     (4, 1): 0.9, # plagal cadence
#                     (1, 4): 0.4, # plagal half cadence
#                     (1, 5): 0.5, (2, 5): 0.5, (4, 5): 0.5, (6, 5): 0.5, # half cadences
#                     (5, 6): 0.4, # deceptive cadence
#                     }


### TBI: seventh-chord ScaleDegrees that automatically use min/maj/dom/dim 7th modifiers

### TBI: progression completion feature that incorporates T-S-D-T progression logic:
# I is tonic
# V and viio are dominant
# ii and IV are subdominant
# vi is pre-subdominant
# syntactic progressions go from tonic to subdominant to dominant to tonic
# the first subdominant in a T-S-D-T progression can optionally be preceded by a pre-subdominant
# "It is allowable to move between functionally identical chords only
#   when the root of the first chord lies a third above the root of the
#   second." (i.e. IV-ii, viio-V)
# "Dominant chords can also progress to vi as part of a 'deceptive' progression."

# c.f. root-motion theory (Meeus):
# root motion by fifth is primary: descending-fifth motion represents the
# prototypical “dominant” progression, while ascending-fifth motion is prototypically
# “subdominant.” Meeus additionally allows two classes of “substitute” progression: rootprogression by third can “substitute” for a fifth-progression in the same direction; and
# root-progression by step can “substitute” for a fifth-progression in the opposite direction



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


roman_degree_chords = {}
# render as an alias dict:
for arabic,roman in numerals_roman.items():
    roman_degree_chords[roman] = (arabic, Major)
    roman_degree_chords[roman.lower()] = (arabic, Minor)
# and the reverse mapping, for SDC.__repr__:
degree_chords_roman = reverse_dict(roman_degree_chords)

def parse_roman_numeral(numeral):
    """given a (string) roman numeral, in upper or lower case,
    with a potential chord qualifier at the end,
    parse into a (degree:int, qualifiers:list) tuple"""
    out = reduce_aliases(numeral, roman_degree_chords)
    assert isinstance(out[0], tuple) # an integer, quality tuple
    deg, quality = out[0]
    # we should treat the quality (if minor) as a qualifier in its own right:
    qualifiers = []
    if quality.minor:
        quality_qualifier = ChordQualifier('minor')
        qualifiers.append(quality_qualifier)

    if len(out) > 1: # got one or more additional qualifiers as well
        quals = parse_chord_qualifiers(out[1:])
        qualifiers.extend(quals)

    return deg, quality, qualifiers



class ScaleDegreeChord(ScaleDegree):
    """A hypothetical (triad) chord whose root exists as the degree of some hypothetical diatonic major/minor scale"""
    def __init__(self, name, scale=None):
        """name is a case-sensitive roman numeral that describes the scale degree,
        uppercase for major or lowercase for minor,
        with a potential qualifier like 7, #5, 0, etc. - should be a valid chord suffix

        OR an explicit [degree, quality, (optional) modifier] iterable"""

        # if isinstance(name, str):
        #     # parse input string:
        self.degree, self.quality, self.qualifiers = self._parse_input(name)

        if scale is not None:
            self.scale = Scale(scale)
        else:
            self.scale = None
        # else:
        #     assert isinstance(name, (list, tuple)), f'Input to ScaleDegree expected to be string or iterable but got: {type(name)}'
        #     # just take degree/quality/modifier directly
        #     if len(name) == 2:
        #         self.degree, self.quality = name
        #         self.qualifiers = []
        #     elif len(name) == 3:
        #         self.degree, self.quality, self.qualifiers = name
        #     else:
        #         raise Exception(f'Invalid tuple provided to ScaleDegree init: {name}')

        # if isinstance(self.quality, str):
        #     # cast to quality object if it is not already one:
        #     self.quality = Quality(self.quality)

        # determine tonic quality:
        if (self.quality.minor and self.degree in [1, 4, 5]) or (self.quality.major and self.degree not in [1, 4, 5]):
            self.key_quality = Minor
        else:
            self.key_quality = Major


    def _parse_input(self, name):
        """parses degree, descriptor, and quality from input arg"""

        # accept re-casting:
        if isinstance(name, ScaleDegreeChord):
            return name.degree, name.quality, name.qualifiers

        elif isinstance(name, (list, tuple)):
            # just take degree/quality/modifier directly
            if len(name) == 2:
                degree, quality = name
                qualifiers = []
            elif len(name) == 3:
                degree, quality, qualifiers = name
            else:
                raise Exception(f'Invalid tuple provided to ScaleDegree init: {name}')
            return degree, quality, qualifiers


        elif isinstance(name, str):
            # this is a roman numeral, possibly with some qualifier/s afterward
            degree, quality, qualifiers = parse_roman_numeral(name)
            return degree, quality, qualifiers

        else:
            raise TypeError(f'ScaleDegreeChord expected input to be a str or tuple but got: {type(name)}')

        # # look for roman numerals by checking the first 3/2/1 chars of name:
        # degree_int = None
        # num_chars_to_check = min([3, len(name)])
        # for i in range(num_chars_to_check, 0, -1):
        #     potential_name = name[:i]
        #     print(f'Checking name {name} up to index {i}: {potential_name}')
        #     if potential_name.upper() in roman_numerals.keys():
        #         # this is the scale degree
        #         degree_int = roman_numerals[potential_name.upper()]
        #         if potential_name.isupper():
        #             quality = Major
        #         elif potential_name.islower():
        #             quality = Minor
        #         else:
        #             raise Exception(f'Inconsistent case for scale degree input: {potential_name} (should be entirely upper or lower)')
        #         break
        # if degree_int is None:
        #     raise Exception(f'Scale degree input does not appear to contain a valid roman numeral: {name}')
        # if len(name) > i:
        #     # modified
        #     rest = name[i:]
        #     print(f'Detected ScaleDegree modifier: {rest}')
        #     modifier = ChordQuality(rest)
        #     if modifier.diminished:
        #         assert quality.minor, f"Degree {name} is to be diminished, but {name[:i]} is not minor"
        #         quality = Diminished
        # else:
        #     modifier = None
        # return degree_int, quality, modifier

    def __str__(self):
        roman = numerals_roman[self.degree]
        if self.quality.minor:
            roman = roman.lower()
        if self.modifier is not None:
            roman += f' ({self.modifier})'
        return f'ScaleDegree: {roman}'

    def __repr__(self):
        return str(self)

    def __add__(self, other, diminish=True):
        """mod-7 arithmetic on scale chord roots"""
        other = int(other)
        new_degree = (((self.degree + other) -1 ) % 7 ) + 1
        new_quality = self.quality
        if new_degree not in [1,4,5]: # swap quality if needed:
            new_quality = ~self.quality

        new_modifier = None
        if diminish:
            # set default dim modifier on 7 and 2 chords:
            if (new_degree == 7 and self.key_quality.major) or (new_degree == 2 and self.key_quality.minor):
                new_modifier = 'dim'
        return ScaleDegree((new_degree, new_quality, new_modifier))

    def __sub__(self, other, diminish=True):
        if isinstance(other, int):
            # just addition by negative other
            return self.add(-other, diminish=diminish)
        elif isinstance(other, ScaleDegree):
            # subtraction of scaledegrees returns their signed distance
            return self.degree - other.degree

    def __eq__(self, other):
        """scale degrees are equal if they have the same degree and quality"""
        return (self.degree == other.degree) and (self.quality == other.quality)

    @property
    def tonic(self):
        """returns the ScaleDegree associated with the tonic of whatever key/progression this is in"""
        if self.quality.major:
            return ScaleDegree('I')
        elif self.quality.minor:
            return ScaleDegree('i')


class Progression:
    """A theoretical progression between unspecified chords,
    as an ordered collection of ScaleDegrees,
    initialised as list: e.g. Progression(['I', 'IV', 'iii', 'V'])
    or as string separated by dashes, e.g.: Progression('I-IV-iii-V')"""
    def __init__(self, degrees):
        self.intervals = []

        if isinstance(degrees, str):
            degrees = degrees.split('-')
            assert len(degrees) > 1, f"Expected a string of roman numerals separated by dashes, but got: {degrees[0]}"
        assert isinstance(degrees, (list, tuple)), "Expected a list or tuple of numeric degrees for Progression initialisation"

        # cast to ScaleDegree objects:
        degrees = [ScaleDegree(d) for d in degrees]
        self.key_quality = degrees[0].key_quality

        ### determine progression quality from degree of the first chord:
        first_degree= degrees[0]
        if isinstance(root, str):
            if first_degree == first_degree.upper():
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



def unit_test():
    # test arithmetic operations on ScaleDegree objects:
    test(ScaleDegree('I') + 3, ScaleDegree('IV'))
    test(ScaleDegre('V') - 2, ScaleDegree('iii'))

if __name__ == '__main__':
    unit_test()
