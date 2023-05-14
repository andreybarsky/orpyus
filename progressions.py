from .intervals import Interval
from .chords import Chord, AbstractChord
from .qualities import Major, Minor, Perfect, Diminished, parse_chord_qualifiers, ChordQualifier
from .scales import Scale, Subscale, scale_name_intervals
from .util import reduce_aliases, auto_split, check_all, reverse_dict, test
from .parsing import roman_numerals, numerals_roman
import pdb


# IDEA / TO DO: model movements not just of chord roots, but of _every_ note in triad/tetrad chords,
# to capture perfect/imperfect cadence based on bass/soprano voicings of chords etc.





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




scale_functions = { 0: "T", # 1st, tonic
                    2: "ST", # 2nd, supertonic
                    3: "M", # m3, mediant
                    4: "M", # M3, mediant
                    5: "S", # 4th, subdominant
                    7: "D", # 5th, dominant
                    8: "SM", # m6, submediant
                    9: "SM", # M6, submediant
                    10: "ST", # m7, subtonic
                    11: "L", # M7, leading tone
                    }

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
    as an ordered collection of AbstractChords built on specified scale degrees,
    initialised as list: e.g. Progression(['I', 'IV', 'iii', 'V'])
    or as string separated by dashes, e.g.: Progression('I-IV-iii-V')"""
    def __init__(self, *numerals, scale=None, chords=None, ignore_conflicting_case=False, auto_qualify=False):
        """accepts one of three input schemes:
        1. 'numerals' input is a list (or demarcated string) of upper/lower-case roman numerals denoting scale chords,
            with optional 'scale' parameter.
                a. if scale is None, we automatically determine the scale from the case/quality of the chord numerals.
                b. if scale is provided, and 'ignore_conflicting_case' is False, we parse chords according to their case/quality,
                    even if they conflict with the scale given.
                c. if scale is provided, and ignore_conflicting_case is True, we ignore the case/quality of the chord numerals
                    and instantiate chords solely according to their root degree and qualifiers, in the scale given.
                        in either case (?), if 'auto_qualify' is True, we also qualify chords automatically as required by the scale,
                        for example making the 7-chord diminished in major.
        2. 'numerals' input is a list of integers denoting root degrees of chords, and 'scale' is a Scale object (or string that casts to Scale),
            in which case we allocate major/minor quality to the chords based on the scale provided.
        3. 'numerals' input is a list of integers denoting root degrees of chords, and 'chords' is an iterable of AbstractChord objects
            (or strings that cast to AbstractChords), in which case we automatically determine the scale from the qualities of the chords.
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
            # roman numeral strings
            degree_tuples = [parse_roman_numeral(n) for n in numerals] # degree, quality, [qualifiers] tuples
            print(f'Degree tuples: {degree_tuples}')
            if scale is None:
                # build chords as specified from numerals and detect scale afterward
                self.root_degrees = [d[0] for d in degree_tuples]
                self.chord_qualities = [d[1] for d in degree_tuples]
                self.chord_qualifiers = [d[2] for d in degree_tuples]
                self.chords = [AbstractChord('major' if d[1].major_ish else 'minor', qualifiers=d[2]) for d in degree_tuples]

                self.scale = self._detect_scale(degree_tuples)

            else:
                # scale is provided, so we simply instantiate it
                # and, if needed, check degree chords against it
                if isinstance(scale, str):
                    scale = Scale(scale)
                assert type(scale) in [Scale, Subscale]
                self.scale = scale

                if ignore_conflicting_case:
                    # ignore case (but not qualifiers) of roman numeral chords provided
                    # and instantiate them from scale instead:
                    self.root_degrees = [d[0] for d in degree_tuples]
                    self.chord_qualifiers = [d[2] for d in degree_tuples]
                    # auto-qualifies by default (?)
                    self.chords = [self.scale.chord(d[0], qualifiers=d[2]) for d in degree_tuples]
                    # infer chord minor/major qualities from scale:
                    self.chord_qualities = [c.quality for c in self.chords]

                else:
                    # do not ignore case; instantiate chords in given case
                    self.root_degrees = [d[0] for d in degree_tuples]
                    self.chord_qualities = [d[1] for d in degree_tuples]
                    self.chord_qualifiers = [d[2] for d in degree_tuples]
                    if auto_qualify: # TBI: figure out how auto_qualify and ignore_conflicting_case are meant to interact
                        self.chords = [self.scale.chord(d[0], qualifiers=d[2]) for d in degree_tuples]
                    else:
                        self.chords = [AbstractChord('major' if d[1].major_ish else 'minor', qualifiers=d[2]) for d in degree_tuples]


        elif check_all(numerals, 'isinstance', int):
            assert scale is not None, f'Progression chords given as integers but scale arg not provided'
            # TO DO: handle all integer-input cases

        else:
            raise ValueError(f'Progression init ended up with an iterable of mixed types, expected all ints or all strings but got: {numerals}')



        # scaledegree, chord pairs:
        self.degree_chords = [(d, self.chords[i]) for i, d in enumerate(self.root_degrees)]

        # construct root movements:
        self.chord_root_intervals_from_tonic = [self.scale.degree_intervals[d] for d in self.root_degrees]
        # self.root_movement_degrees = []
        # self.root_movement_intervals = []
        self.root_movements = []
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


    # TO DO: replace with a (simpler?)
    def _detect_scale(self, degree_tuples):
        """from a provided list of degree tuples of form: (root_degree, quality, qualifiers)
        determine whether they most likely correspond to a major or minor scale by summing evidence
        and returns the resulting scale as an object"""
        major_evidence, minor_evidence = 0, 0
        for d in degree_tuples:
            root, quality, qualifiers = d
            if root == 1 and quality.major_ish:
                major_evidence += 3
            elif root == 1 and quality.minor_ish:
                minor_evidence += 3
            elif quality.major:
                if root in {4,5}:
                    major_evidence += 1
                elif root in {2,3,6}:
                    minor_evidence += 1
            elif quality.minor:
                if root in {4,5}:
                    minor_evidence += 1
                elif root in {3,6,7}:
                    major_evidence += 1
            elif ChordQualifier('dim') in qualifiers:
                if root == 2:
                    minor_evidence += 2
                elif root == 7:
                    major_evidence += 2
        print(f'For scale chords: {[(r,q,z) for r,q,z in degree_tuples]}')
        print(f'  Evidence for major scale: {major_evidence}')
        print(f'  Evidence for minor scale: {minor_evidence}')
        if major_evidence >= minor_evidence:
            return Scale('natural major')
        else:
            return Scale('natural minor')

    def __str__(self):
        scale_name = self.scale.name
        if 'natural' in scale_name:
            scale_name = scale_name.replace('natural ', '')

        numerals = [numerals_roman[d]  if c.quality.major_ish else numerals_roman[d].lower()  for d,c in self.degree_chords]
        # add suffixes:
        suffix_list = [c.suffix if c.suffix != 'm' else '' for c in self.chords]

        roman_chords_list = [f'{numerals[i]}{suffix_list[i]}' for i in range(len(self))]
        # turn suffix qualifiers into superscript marks etc. where possible:
        roman_chords_str = "-".join([''.join(reduce_aliases(r, qualifier_marks)) for r in roman_chords_list])
        return f'Progression:  𝄆 {roman_chords_str} 𝄇  (in {scale_name})'

    def __len__(self):
        return len(self.chords)

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        """progressions are equal to each other if they have the same chords built on the same degrees"""
        return self.degree_chords == other.degree_chords


class RootMovement:
    """class representing (unsigned) root movement between chords in a progression"""
    def __init__(self, start, end, scale=Scale('major')):
        """'start' and 'end' should both be integers between 1 and 7, denoting the root degrees of the starting and ending scale chords.
            scale is assumed to be major unless otherwise specified,
            which matters only for the intervallic distance (not the scale-degree distance) involved in this movement."""

        if isinstance(scale, str):
            # instantiate Scale object if it is not already instantiated
            scale = Scale(scale)

        assert (start in range(1,8)) and (end in range(1,8)) and (start != end)
        self.start, self.end = start, end
        self.start_iv, self.end_iv = (scale.degree_intervals[d] for d in [self.start, self.end])

        if self.start > self.end:
            # more down than up
            self.up = 7-(self.start - self.end)
            self.down = self.start - self.end
            self.iv_up = 12-(self.start_iv - self.end_iv)
            self.iv_down = self.start_iv - self.end_iv
        elif self.start < self.end:
            # more up than down
            self.up = self.end - self.start
            self.down = 7-(self.end - self.start)
            self.iv_up = self.end_iv - self.start_iv
            self.iv_down = 12-(self.end_iv - self.start_iv)

        self.descending_fifth = self.down == 4
        self.descending_fourth = self.down == 3

        # the 'size' of the movement: 2 to 1 has less magnitude than 5 to 1, but the same as 7 to 1
        self.magnitude = min([self.up, self.down])

        # the following seems to hold true for MAJOR scale harmony:
        self.dominant = self.down in {4,2} or self.up in {3,1} # descending by fifth or third
        self.subdominant = self.down in {3,1} or self.up in {4,2}
        self.primary = 4 in {self.down, self.up}
        self.substitute = not self.primary

        self.function = ('primary ' if self.primary else 'substitute ') + ('dominant' if self.dominant else 'subdominant')
        self.start_function = scale_functions[self.start_iv]
        self.end_function = scale_functions[self.end_iv]

        self.resolved = (self.end == 1)
        self.hanging = self.end_function in {"D", "L"}

        self.authentic_cadence = (self.start == 5 and self.end == 1)
        self.half_cadence = (self.start in {1, 2, 4, 6}) and (self.end == 5)
        self.plagal_cadence = (self.start == 4 and self.end == 1)
        self.plagal_half_cadence = (self.start in {1, 2, 5, 6}) and (self.end == 4)
        # self.plagal_half_cadence = (self.start == 1 and self.end == 4)

    def __str__(self):
        return(f'Root movement from {self.start} to {self.end} \nUp:{self.up} Down:{self.down} \n({self.function})')

    def __repr__(self):
        return str(self)


# # scrap this for a more theoretical approach?
# cadence_finality = {(5, 1): 1,   # authentic cadence
#                     (4, 1): 0.9, # plagal cadence
#                     (1, 4): 0.4, # plagal half cadence
#                     (1, 5): 0.5, (2, 5): 0.5, (4, 5): 0.5, (6, 5): 0.5, # half cadences
#                     (5, 6): 0.4, # deceptive cadence
#                     }

# root motion by fifth is primary: descending-fifth motion represents the
# prototypical “dominant” progression, while ascending-fifth motion is prototypically
# “subdominant.” Meeus additionally allows two classes of “substitute” progression:
# rootprogression by third can “substitute” for a fifth-progression in the same direction; and
# root-progression by step can “substitute” for a fifth-progression in the opposite direction

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
    test(Progression('I-IV-vii°-I', scale='major'), Progression(['I', 'IV', 'viidim', 'I']))
    test(Progression('ii-iv-i-vi', ignore_conflicting_case=True), Progression(['ii', 'iv', 'i', 'VI'], scale='minor')) # TBI: IV gets parsed as iv here. check for it?


if __name__ == '__main__':
    unit_test()
