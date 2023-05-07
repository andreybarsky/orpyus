from .intervals import Interval
from .chords import Chord
from .qualities import Major, Minor, Perfect, Diminished, parse_chord_qualifiers, ChordQualifier
from .scales import Scale, scale_name_intervals
from .util import reduce_aliases, auto_split, check_all, reverse_dict, test
from .parsing import roman_numerals, numerals_roman
import pdb



# # scrap this for a more theoretical approach?
# cadence_finality = {(5, 1): 1,   # authentic cadence
#                     (4, 1): 0.9, # plagal cadence
#                     (1, 4): 0.4, # plagal half cadence
#                     (1, 5): 0.5, (2, 5): 0.5, (4, 5): 0.5, (6, 5): 0.5, # half cadences
#                     (5, 6): 0.4, # deceptive cadence
#                     }


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
# “subdominant.” Meeus additionally allows two classes of “substitute” progression:
# rootprogression by third can “substitute” for a fifth-progression in the same direction; and
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

qualifier_marks = {'dim': '°',
                   'hdim': 'ø',
                   'aug': '+',
                   'maj7': 'Δ⁷',
                   '7': '⁷',
                   '9': '⁹'}

roman_degree_chords = {}
# render as an alias dict:
for arabic,roman in numerals_roman.items():
    roman_degree_chords[roman] = (arabic, Major)
    roman_degree_chords[roman.lower()] = (arabic, Minor)
# and the reverse mapping, for SDC.__repr__:
degree_chords_roman = reverse_dict(roman_degree_chords)

progression_aliases = dict(roman_degree_chords)
# kludge: we have to specifically ignore 'dim' when reading roman numerals,
# because it contains a roman numeral ('i')
progression_aliases['dim'] = 'dim'

def parse_roman_numeral(numeral):
    """given a (string) roman numeral, in upper or lower case,
    with a potential chord qualifier at the end,
    parse into a (degree:int, qualifiers:list) tuple"""
    out = reduce_aliases(numeral, progression_aliases)
    assert isinstance(out[0], tuple) # an integer, quality tuple
    deg, quality = out[0]

    qualifiers = []

    # should we should treat the quality (if minor) as a qualifier in its own right?
    if quality.minor:
        quality_qualifier = ChordQualifier('minor')
        qualifiers.append(quality_qualifier)

    if len(out) > 1: # got one or more additional qualifiers as well
        rest = ''.join(out[1:])
        quals = parse_chord_qualifiers(rest)
        qualifiers.extend(quals)

    return deg, quality, qualifiers


class Progression:
    """A theoretical progression between unspecified chords,
    as an ordered collection of AbstractChords,
    initialised as list: e.g. Progression(['I', 'IV', 'iii', 'V'])
    or as string separated by dashes, e.g.: Progression('I-IV-iii-V')"""
    def __init__(self, *numerals, scale=None):
        """accepts one of two input schemes:
        1. 'numerals' input is a list (or demarcated string) of upper/lower-case roman numerals denoting scale chords,
            in which case we try and determine the scale that this progression is in from the cases.
        2. 'numerals' input is a list of integers denoting scale chords, and 'scale' is a Scale object (or string that casts to Scale),
            in which case we allocate major/minor quality to the chords based on the scale provided.
            """

        # unpack tuple arg:
        if len(numerals) == 1:
            numerals = numerals[0]

        if isinstance(numerals, str):
            split_numerals = auto_split(numerals, allow='°øΔ♯♭♮+𝄫𝄪')
            assert len(split_numerals) > 1, f"Expected a string of roman numerals separated by dashes (or other obvious separator), but got: {numerals[0]}"
            numerals = split_numerals
        # is now an iterable of roman numeral strings OR of integers

        if check_all(numerals, 'isinstance', str):
            if scale is None:
                # auto detect scale from numeral case
                degree_tuples = [parse_roman_numeral(n) for n in numerals] # degree, quality, [qualifiers] tuples
                self._detect_scale(degree_tuples)

        elif check_all(numerals, 'isinstance', int):
            assert scale is not None, f'Progression chords given as integers but scale arg not provided'




        # case 1: parse roman numerals:

            assert isinstance(numerals, (list, tuple)), "Expected a list or tuple of numeric degrees for Progression initialisation"
            assert check_all(numerals, 'isinstance', (str)), "Expected input list to Progression to contain a series of roman numeral strings"
            # TBI: allow abstract chords too?
            # TBI: detect if these are abstract chord strings rather than roman numeral strings?

            # parse roman numeral input
            self.roman_degrees = numerals
            degree_tuples = [parse_roman_numeral(n) for n in self.roman_degrees]

        elif isinstance(numerals, (list, tuple)):
            # could be an iterable of integers, or roman numeral strings
            pass # ...
        else:
            assert len(numerals) > 1, f"Progression must contain at least one roman numeral chord, but got: {numerals}"

        self.root_degrees = [d[0] for d in degree_tuples]
        self.chord_qualities = [d[1] for d in degree_tuples]
        self.chord_qualifiers = [d[2] for d in degree_tuples]



        # self.chords = [AbstractChord(qualifiers=qs) for qs in self.chord_qualifiers]

        ######## construct the scale that this progression is built on
        if isinstance(scale, str):
            scale = Scale(scale)
        elif scale is None:
            # if scale is not given, assume major or minor scale depending on parsed roman degrees:
            first_degree, first_quality, _ = degree_tuples[0]
            if (first_quality.major and first_degree in {1,4,5}) or (first_quality.minor and first_degree in {3,6,7}): # is this right? iidim chords in minor scales?
                scale = Scale('major')
            else:
                scale = Scale('minor')
        assert isinstance(scale, Scale)
        self.scale = scale
        ########

        # cast to AbstractChord objects:
        self.chords = [self.scale.chord(d[0], qualifiers=qs) for qs in self.chord_qualifiers]
        # scaledegree, chord pairs:
        self.degree_chords = [(d, self.chords[i]) for i, d in enumerate(self.root_degrees)]

        # construct root movements:
        self.chord_root_intervals_from_tonic = [self.scale.degree_intervals[d] for d in self.root_degrees]
        self.root_movement_degrees = []
        self.root_movement_intervals = []
        for i in range(1, len(self)):
            deg1, deg2 = self.root_degrees[i-1], self.root_degrees[i]
            iv1, iv2 = self.chord_root_intervals_from_tonic[i-1], self.chord_root_intervals_from_tonic[i]

            # these are both degrees in range 1-7 (for diatonic scales at least)
            # and a movement from 7-1, for instance, should be represented as up1, as well as down6
            if deg1 > deg2:
                deg_up = 7-(deg1 - deg2)
                deg_down = deg1 - deg2
                iv_up = 12-(iv1 - iv2)
                iv_down = iv1 - iv2
            elif deg1 < deg2:
                deg_up = deg2 - deg1
                deg_down = 7-(deg2 - deg1)
                iv_up = iv2 - iv1
                iv_down = 12-(iv2 - iv1)
            self.root_movement_degrees.append({'up':deg_up, 'down':deg_down})
            self.root_movement_intervals.append({'up':Interval(iv_up), 'down':Interval(iv_down)})

    def _detect_scale(self, degree_tuples):
        pass

    def __str__(self):
        scale_name = self.scale.name
        if 'natural' in scale_name:
            scale_name = scale_name.replace('natural ', '')
        suffix_list = [c.suffix if c.suffix not in {'m', 'dim'} else '' for c in self.chords]
        roman_chords_list = [f'{self.scale.roman_numeral(d)}{suffix_list[i]}' for i, (d,c) in enumerate(self.degree_chords)]
        # turn suffix qualifiers into superscript marks etc. where possible:
        roman_chords_str = "-".join([''.join(reduce_aliases(r, qualifier_marks)) for r in roman_chords_list])
        return f'Progression:  𝄆 {roman_chords_str} 𝄇  (in {scale_name})'

    def __len__(self):
        return len(self.chords)

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return self.degree_chords == other.degree_chords

class ChordProgression(Progression):
    """Progression subtype defined using specific chords, also acts as container class for Chord objects"""
    def __init__(self, *chords):
        # parse chords arg:
        self.chords = []
        self.chord_count = {}
        self.notes = []
        self.note_count = {}

        self.contains_duplicates = False

        if len(chords) == 1:
            chords = chords[0]

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

    def __eq__(self, other):
        if isinstance(other, Progression):
            return self.chords == other.chords
        else:
            raise TypeError(f'__eq__ only defined between Progressions, not between Progression and: {type(other)}')

    def __str__(self):
        chord_set_str = ','.join(['♬ ' + c.name for c in self.chords])
        return f'𝄆 {chord_set_str} 𝄇'

    def __repr__(self):
        return str(self)

    def detect_key(self):
        ... # TBI
        pass



def unit_test():
    # test numeral parsing:
    a, b, c = parse_roman_numeral('viidim')
    test((a,b,c[0], c[1]), (7, Minor, ChordQualifier('minor'), ChordQualifier('diminished')))


    # test arithmetic operations on ScaleDegree objects:
    # test(ScaleDegree('I') + 3, ScaleDegree('IV'))
    # test(ScaleDegre('V') - 2, ScaleDegree('iii'))
    test(Progression('I-IV-vii-I', scale='major'), Progression(['I', 'IV', 'vii', 'I']))
    test(Progression('ii-iv-i-VI'), Progression(['ii', 'IV', 'i', 'VI'], scale='minor')) # TBI: IV gets parsed as iv here. check for it?


if __name__ == '__main__':
    unit_test()
