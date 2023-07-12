from .intervals import *
# from scales import interval_scale_names, key_name_intervals
from .util import rotate_list, reverse_dict, unpack_and_reverse_dict, numeral_subscript, reduce_aliases, check_all, log
from .chords import Factors, AbstractChord, chord_names_by_rarity, chord_names_to_intervals, chord_names_to_factors
from .qualities import ChordModifier, Quality
from .parsing import num_suffixes, numerals_roman, is_alteration
from . import notes, _settings


# 'standard' scales are: natural/melodic/harmonic majors and minors, the most commonly used in pop music
standard_scale_names = {'natural major', 'natural minor', 'harmonic major', 'harmonic minor', 'melodic major', 'melodic minor'}
# 'base' scales are those not obtained by rotations of any other scales:
base_scale_names = {'natural major', 'melodic minor', 'harmonic minor', 'harmonic major'}
# 'natural' scales are just the natural major and minors:
natural_scale_names = {'natural major', 'natural minor'}

# this dict maps base scale names to dicts that map scale degrees to the modes of that base scale
base_scale_mode_names = {
  'natural major': {1: ['ionian', 'major'], 2: ['dorian'], 3: ['phrygian'], 4: ['lydian'],
                    5: ['mixolydian'], 6: ['natural minor', 'aeolian', 'minor'], 7: ['locrian']},
  'melodic minor': {1: ['athenian', 'melodic minor ascending', 'jazz minor'], 2: ['cappadocian', 'phrygian ♯6', 'dorian ♭2'],
                    3: ['asgardian', 'lydian augmented'], 4: ['pontikonisian', 'lydian dominant'],
                    5: ['melodic major', 'olympian', 'aeolian dominant', 'mixolydian ♭6'],
                    6: ['sisyphean', 'aeolocrian', 'half-diminished'], 7: ['palamidian', 'altered dominant']},
 'harmonic minor': {1: [], 2: ['locrian ♯6'], 3: ['ionian ♯5'], 4: ['ukrainian dorian'],
                    5: ['phrygian dominant'], 6: ['lydian ♯2'], 7: ['altered diminished']},
 'harmonic major': {1: [], 2: ['blues heptatonic', 'dorian ♭5', 'locrian ♯2♯6'], 3: ['phrygian ♭4', 'altered dominant ♯5'],
                    4: ['lydian minor', 'lydian ♭3', 'melodic minor ♯4'], 5: ['mixolydian ♭2'],
                    6: ['lydian augmented ♯2'], 7: ['locrian 𝄫7']}
                 }

# dict keying mode names to (base_scale_name, base_scale_mode) tuples:
mode_name_identities = {mode_name: (base_name, mode_num)
                        for base_name, mode_dict in base_scale_mode_names.items()
                        for mode_num, name_list in mode_dict.items()
                        for mode_name in name_list
                        }

# ScaleFactors are the types of Factors that apply to Scale objects:
class ScaleFactors(Factors):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, strip_octave=True, auto_increment_clashes=True, **kwargs)
        # one extra post-processing check over the default Factors init:
        # detect if the 8th factor has been defined as natural, in which case we
        #   strip and ignore it (because every diatonic scale has an implied 8th
        #                      degree that is enharmonic to the 1st),
        # but if the 8th factor is flattened or sharpened, interpret this as
        #   some kind of non-diatonic scale that will require IrregularIntervals
        if (8 in self) and self[8] == 0:
            del self[8]
        # now if there remain any 8th or higher factors, we sanity-check by ensuring
        # that there are enough degrees to fill out a scale of the appropriate size:
        highest_degree_in_scale = max(self.keys())
        if highest_degree_in_scale >= 8:
            assert len(self) >= 8, f'ScaleFactors object defined with a factor of 8 or greater but does not contain enough degrees to fill that scale'
        self.max_degree = highest_degree_in_scale

    def to_intervals(self, as_dict=False):
        """translates these Factors into an IntervalList,
          or, if as_dict, into a factor_intervals dict mapping degrees to intervals.
        in addition, detects if these Factors represent a non-heptatonic scale
          (e.g. the octatonic bebop scale) and returns IrregularIntervals if necessary. """
        if len(self) <= 7:
            # ordinary case: diatonic/heptatonic scale, or maybe a pentatonic which we treat as subscale
            factor_intervals = [Interval.from_degree(d, offset=o) for d,o in self.items()]
        else:
            # more than 7 notes in scale, so we must initialise appropriate IrregularIntervals:
            factor_intervals = [IrregularInterval.from_degree(d, offset=o, max_degree=len(self)) for d,o in self.items()]

        if not as_dict:
            return IntervalList(factor_intervals)
            # return IntervalList([Interval.from_degree(d, offset=o) for d, o in self.items()]).sorted()
        elif as_dict:
            return {iv.degree:iv for iv in factor_intervals}
            # return {d:Interval.from_degree(d, offset=o) for d, o in self.items()}

    def subscale(self, keep=None, omit=None):
        """return a new ScaleFactors object that either keeps a specified list of factors,
        or keeps all but a specified list of omitted factors"""
        if keep is not None:
            assert omit is None and type(keep) in [list, tuple]
            new_factors = ScaleFactors({k:v for k,v in self.items() if k in keep})
        elif omit is not None:
            if type(omit) is int: # recast single integer omission into list
                omit = [omit]
            assert keep is None and type(omit) in [list, tuple]
            new_factors = ScaleFactors({k:v for k,v in self.items() if k not in omit})
        return new_factors

    def mode(self, N):
        """returns the ScaleFactors corresponding to the Nth mode of this object"""
        intervals = self.to_intervals()
        mode_intervals = intervals.mode(N)
        factors_str = ','.join(mode_intervals.to_factors())
        return ScaleFactors(factors_str)

# this dict maps scale intervals (in canonical, stripped form) to all accepted aliases
# at first just for the standard scales, but it gets filled out later

factor_scale_names = { # standard scales are defined here, modes and subscales are added later:
                    ScaleFactors('1,  2,  3,  4,  5,  6,  7'): 'natural major',
                    ScaleFactors('1,  2, b3,  4,  5, b6, b7'): 'natural minor',
                    ScaleFactors('1,  2,  3,  4,  5, b6,  7'): 'harmonic major',
                    ScaleFactors('1,  2, b3,  4,  5, b6,  7'): 'harmonic minor',
                    ScaleFactors('1,  2,  3,  4,  5, b6, b7'): 'melodic major',
                    ScaleFactors('1,  2, b3,  4,  5,  6,  7'): 'melodic minor', # (ascending)
    # while it's true that "melodic minor" can refer to a special scale that uses
    # the the natural minor scale when descending, but that out-of-scope for now
                    }
scale_name_factors = reverse_dict(factor_scale_names)
# we recognise scale names by breaking them down into words and checking if all words are present,
# i.e. so that "major pentatonic" and "pentatonic major" return the same thing.
# this is implemented by keying tuples of the constituent words of a scale name, sorted alphabetically ('wordbags'):
wordbag_scale_names = {frozenset(name.split(' ')):name for name in scale_name_factors.keys()}

# string replacements for scale searching:
scale_name_replacements = {
                        'major': ['maj', 'M', 'Δ', ],
                        'minor': ['min', 'm'],
                        'harmonic': ['H', 'h', 'harm', 'har', 'hic'],
                        'melodic': ['melo', 'mel', 'mic'],
                        'pentatonic': ['pent', '5tonic'],
                        'hexatonic': ['hex', '6tonic'],
                        'mixolydian': ['mixo', 'mix'],
                        'dorian': ['dori', 'dor'],
                        'phrygian': ['phrygi', 'phryg'],
                        'lydian': ['lydi', 'lyd'],
                        'locrian': ['locri', 'loc'],
                        'diminished': ['dim'],
                        'dominant': ['dom'],
                        'augmented': ['aug'],
                          }
replacement_scale_names = unpack_and_reverse_dict(scale_name_replacements, include_keys=True)

# mapping whole-name replacements for scales: (gets filled later)
alias_scale_names = {}

# define modes and their substitutions:
# for base_factors, base_name in factor_scale_names.items():
#     if base_name in base_scale_names: # exclude non-base (standard) scales: natural minor, melodic major
        # mode_dict = base_scale_mode_names[base_name]

# interval_scale_names = {
#     IntervalList(M2, M3, P4, P5, M6, M7): ['', 'maj', 'M', 'major', 'natural major' ],
#     IntervalList(M2, m3, P4, P5, m6, m7): ['m', 'min', 'minor', 'natural minor' ],
#
#     IntervalList(M2, M3, P4, P5, m6, M7): ['harmonic major', 'M harmonic', 'major harmonic', 'maj harmonic', 'harmonic major'],
#     IntervalList(M2, m3, P4, P5, m6, M7): ['harmonic minor', 'm harmonic', 'minor harmonic', 'min harmonic', 'harmonic minor'],
#     IntervalList(M2, M3, P4, P5, m6, m7): ['melodic major', 'M melodic', 'major melodic', 'melodic major', 'maj melodic', 'melodic major'],
#     IntervalList(M2, m3, P4, P5, M6, M7): ['melodic minor', 'm melodic', 'minor melodic', 'min melodic', 'jazz minor', 'melodic minor ascending','melodic minor'], # note: ascending only
#     # "melodic minor" can refer to using the the natural minor scale when descending, but that is TBI
#     }
# scale_name_intervals = unpack_and_reverse_dict(interval_scale_names)
# standard_scale_suffixes = list([names[0] for names in interval_standard_scale_names.values()])




################################################################################


# usage convention for scale factors and scale degrees:
# a 'ScaleFactor' is an integer that is always either in the range 1-7,
# or enharmonic to the range 1-7 (i.e. the 8th factor is always an octave over the 1st)
# while a 'ScaleDegree' is an integer that is always continuous in its own range,
# so that e.g. the major pentatonic scale has factors (1,2,3,5,6) but degrees (1,2,3,4,5)
class ScaleDegree(int):
    """class representing the degrees of a scale with associated mod-operations"""
    def __new__(cls, degree, num_degrees=7):
        extended_degree = degree
        # note about negative degrees: they are technically well-defined,
        # but look odd due to the 1-indexing of positive degrees.
        # e.g. the degree that is two notes below tonic has degree-value 6,
        # but extended-degree-value -1
        if (degree > num_degrees) or (degree < 1):
            degree = ((degree -1 ) % num_degrees) + 1
        obj = int.__new__(cls, degree) # int() on a degree returns the flat (non-compound) degree as int
        obj.degree = int(degree) # should always be identical to int(self)
        obj.num_degrees = num_degrees # i.e. scale size
        obj.extended_degree = extended_degree
        obj.octave = ((obj.extended_degree - obj.degree)/obj.num_degrees)+1
        return obj

    # mathematical operations on scale degrees preserve extended degree and scale size:
    def __add__(self, other):
        assert not isinstance(other, Interval), "ScaleDegrees cannot be added to intervals"
        return ScaleDegree(self.extended_degree + int(other), num_degrees=self.num_degrees)
    def __sub__(self, other):
        assert not isinstance(other, Interval), "ScaleDegrees cannot be added to intervals"
        return ScaleDegree(self.extended_degree - int(other), num_degrees=self.num_degrees)
    def __abs__(self):
        """flatten compound degree into a simple one,
        i.e. abs(ScaleDegree(10)) == ScaleDegree(3)"""
        # similar behaviour to int(self), but returns a new ScaleDegree instead of an int
        return ScaleDegree(self.degree, num_degrees=self.num_degrees)
    def __pow__(self, octave):
        """octave transposition: a ScaleDegree multipled by x raises it into the xth octave
        i.e. ScaleDegree(3)**2 == ScaleDegree(10)"""
        assert type(octave) is int, "ScaleDegrees can only be multipled (octave transposition) by integers"
        if octave >= 1:
            return ScaleDegree(self.extended_degree+(self.num_degrees*(octave-1)),  num_degrees=self.num_degrees)
        elif octave <= -1:
            return ScaleDegree(self.extended_degree-(self.num_degrees*(octave-1)),  num_degrees=self.num_degrees)
        elif octave == 0: # the tonic is the identity, so any degree ** 0 returns the tonic
            return ScaleDegree(1, num_degrees=self.num_degrees)
    # scale degrees hash as integers for lookup purposes:
    def __hash__(self):
        return hash(int(self))

    def __str__(self):
        # ScaleDegree shows as integer char combined with caret above:
        degree_str = f'{self.degree}\u0311'
        if self.extended_degree != self.degree:
            # clarify that this is a compound degree:
            degree_str += f'({self.extended_degree})'
        if self.num_degrees != 7:
            # with an added subscript for non-diatonic (irregular) scale degrees
            degree_str += numeral_subscript(self.num_degrees) # i.e. would be '8' for regular scale degrees
        return degree_str

    def __repr__(self):
        return str(self)




### Scale class that spans diatonic scales, subscales, blues scales, octatonic scales and all the rest:

# scales are primarily defined from factors; this is how we declare them initially

class NewScale:
    def __init__(self, name=None, intervals=None, factors=None, alterations=None, chromatic_intervals=None, mode=1):
        # check for intervals or factors being fed as first arg:
        name, intervals, factors = self._reparse_args(name, intervals, factors)

        # .factors is a Factors object that explains which diatonic degrees are present in the scale
        # .factor_intervals is a dict mapping from integer factors to the corresponding intervals
        # and .chromatic_intervals is a plain list of the chromatic (or 'passing') intervals, like blues notes
        self.factors, self.factor_intervals, self.chromatic_intervals = self._parse_input( name, intervals, factors, alterations, chromatic_intervals, mode)

        assert self.chromatic_intervals is not None

        ### TBI: test NewScale init with odd factors:
        # NewScale('1,2,3,4,5,b6,bb7,b8,8').factor_intervals (seems to work)

        # now we figure out how many degrees this scale has, and allocate degree_intervals accordingly:
        self.num_degrees = len(self.factors)
        self.degrees = [ScaleDegree(d, num_degrees = self.num_degrees) for d in range(1, self.num_degrees+1)]
        self.degree_intervals = {d: self.factor_intervals[f] for d,f in zip(self.degrees, self.factors)}
        self.interval_degrees = reverse_dict(self.degree_intervals)
        self.interval_factors = reverse_dict(self.factor_intervals)

        # the .intervals attribute includes both factor ('diatonic') and chromatic ('passing') intervals:
        self.intervals = IntervalList(list(self.factor_intervals.values()) + self.chromatic_intervals).sorted()


    ### internal init subroutines:
    def _reparse_args(self, name, intervals, factors):
        """detect if intervals or factors have been given as first arg instead of name,
        and return corrected (name, intervals, factors) tuple"""
        if isinstance(name, (list, tuple)):
            # interpret first-argument list as an intervals input, not a name input
            intervals = name
            name = None
        elif (isinstance(name, str) and name[0].isnumeric()) or isinstance(name, (Factors, dict)):
            # interpret a string starting on a numeral as a Factor arg:
            factors = name
            name = None
        elif (name == '') or (name is None and intervals is None and factors is None):
            # if name is emptystring or if no init args have been given at all,
            # in which case we just return the major scale
            name = 'natural major'
        return name, intervals, factors

    def _parse_input(self, name, intervals, factors, alterations, chromatic_intervals, mode):
        if name is not None:
            assert intervals is None and factors is None and alterations is None
            canonical_name, alterations = self._parse_scale_name(name)
            factors = scale_name_factors[canonical_name]

        if intervals is not None:
            assert factors is None
            if not isinstance(intervals, IntervalList):
                intervals = IntervalList(intervals)
            # sanitise intervals so that they start with a root but do not end with an octave:
            intervals = intervals.strip().pad()
            # detect if we need to re-cast to irregular intervals:
            if len(intervals) > 7:
                # initialise IrregularIntervals with a max_degree of whatever was given:
                intervals = IntervalList([IrregularInterval(intervals[i].value, i+1, len(intervals)) for i in range(len(intervals))])

            factors = ScaleFactors(', '.join(intervals.pad().as_factors))

        elif factors is not None:
            if not isinstance(factors, ScaleFactors):
                orig_factors = factors
                factors = ScaleFactors(factors)
            # compute intervals from factors: (if we don't need to do so later)
            if alterations is None or len(alterations) == 0:
                intervals = factors.to_intervals()
        else:
            raise Exception('Scale init must be given one of: name, intervals, or factors')

        if alterations is not None and len(alterations) > 0:
            # if any alterations have been provided (or parsed out),
            # apply them here to the Factors object:
            for alteration in alterations:
                if not isinstance(alteration, ChordModifier):
                    alteration = ChordModifier(alteration)
                factors = factors + alteration
            # then recompute intervals:
            intervals = factors.to_intervals()

        # chromatic intervals are specifically those intervals that are NOT on scale factors:
        if chromatic_intervals is not None:
            if not isinstance(chromatic_intervals, IntervalList):
                chromatic_intervals = IntervalList(chromatic_intervals)
        else:
            chromatic_intervals = []

        if mode != 1:
            # we want to the mode of whatever's been produced by names/intervals/factors
            assert (type(mode) is int and mode > 0), "Mode arg to Scale init must be a positive integer"
            # so we rotate the unstacked intervals and restack them: (an IntervalList method exists for this)
            new_intervals = intervals.mode(mode)

            # currently this intervals var doesn't include the chromatic intervals,
            # which are ALSO shifted by a mode rotation
            # so we shift those explicitly here:
            num_places = mode-1
            # the interval at the num_places index of the original intervals
            # is how far leftward the chromatic intervals must be shifted:
            left_shift = intervals[num_places]
            chromatic_intervals = (chromatic_intervals - left_shift).flatten()
            intervals = new_intervals
            # then recompute factors:
            factors = ScaleFactors(', '.join(intervals.pad(left=True, right=False).as_factors))

        # now factors and intervals have necessarily been set, both including the tonic,
        # including any alterations and modal rotations that needed to be applied
        # so we can produce the factor_intervals; mapping of whole-tone degrees to their intervals:
        factor_intervals = {f:iv for f,iv in zip(factors, intervals)}

        return factors, factor_intervals, chromatic_intervals

    def _parse_scale_name(self, scale_name):
        """takes a string denoting a scale name and returns its canonical form if it exists"""
        # step 0: fast exact check, see if the provided name exists as a canonical name or alias:
        if scale_name in scale_name_factors:
            log(f'Fast name check found "{scale_name}" as an existing canonical name')
            return scale_name, []
        elif scale_name in alias_scale_names:
            canonical_scale_name = alias_scale_names[scale_name]
            log(f'Fast name check found "{scale_name}" as an existing alias for canonical name {canonical_scale_name}')
            return canonical_scale_name, []

        # step 1: re-cast replacements (e.g. 'nat' into 'natural', 'min' into 'major')
        reduced_name_words = reduce_aliases(scale_name, replacement_scale_names, chunk=True)
        log(f'Scale name "{scale_name}" recursively re-parsed as: {reduced_name_words}')

        # join and split on whitespace in case no replacements were made but an alteration exists:
        reduced_name_words = ' '.join(reduced_name_words).split(' ')

        # a scale name's 'wordbag' is the (frozen) set of the words in its name:
        # check for alterations:
        alterations = [word for word in reduced_name_words if is_alteration(word)]
        if len(alterations) > 0:
            # if there are any alterations, then the name becomes
            # all the words that AREN'T alterations:
            reduced_name_words = [word for word in reduced_name_words if not is_alteration(word)]
            log(f'Parsed out explicit alterations: {alterations}')


        # search for exact matches in aliases:
        reduced_name = ' '.join(reduced_name_words)
        if reduced_name in alias_scale_names:
            canonical_scale_name = alias_scale_names[reduced_name]
            log(f'Slow name check found reduced name "{reduced_name}" as an existing canonical name')
            return canonical_scale_name, alterations

        wordbag = frozenset(reduced_name_words) # note: frozensets are hashable, unlike regular sets
        if wordbag in wordbag_scale_names:
            canonical_scale_name = wordbag_scale_names[wordbag]
            log(f'Slow name check found reduced name "{reduced_name}" as a rearrangement of canonical name: "{canonical_scale_name}"')
            return canonical_scale_name, alterations
        else:
            raise ValueError(f'{scale_name} re-parsed as {reduced_name_words} but could not find a corresponding scale by that name')

    ### scale production methods:
    def subscale(self, keep=None, omit=None):
        """Return a subscale derived from this scale's factors,
        specified as either a list of factors to keep or to discard"""
        return self.__class__(factors=self.factors.subscale(keep=keep, omit=omit))

    def mode(self, N):
        """Returns a new scale that is the Nth mode of this scale.
        (where mode 1 is identical to the existing scale)"""
        non_chromatic_intervals = IntervalList([iv for iv in self.intervals if iv not in self.chromatic_intervals])
        new_intervals = non_chromatic_intervals.mode(mode)
        # shift chromatic intervals as well:
        num_places = mode-1
        # the interval at the num_places index of the original intervals
        # is how far leftward the chromatic intervals must be shifted:
        left_shift = non_chromatic_intervals[num_places]
        new_chromatic_intervals = (self.chromatic_intervals - left_shift).flatten()
        return NewScale(intervals=new_intervals, chromatic_intervals = new_chromatic_intervals)



    ### utility, arithmetic, and magic methods:
    def __len__(self):
        """A scale's length is the number of intervals it has before the octave,
        so that all diatonic scales have length 7, and all pentatonic scales
        have length 5, and chromatic passing notes add 1 to this count"""
        return len(self.intervals)
    @property
    def len(self):
        return len(self)
    @property
    def order(self):
        """A scale's order is the number of factors/degrees it has, not counting
        chromatic intervals. So the blues scale has order 5, even though it contains
        a 6th passing note"""
        return len(self.factors)

    ### property flags:
    def is_heptatonic(self):
        """A scale is heptatonic if it has 7 notes (including chromatic/passing notes)"""
        return len(self) == 7
    def is_diatonic(self):
        """A scale is diatonic if it is a mode of the natural major or minor scales"""
        for mode in range(1,8):
            major_mode_factors = scale_name_factors[base_scale_mode_names['natural major'][mode][0]]
            if self.factors == major_mode_factors:
                return True
        return False

    ### naming/display methods:
    def _determine_exotic_scale_name(self):
        """If this scale does not have a registered name, we try to call it an
        alteration of some existing scale"""
        # diatonic case:
        if len(self) == 7:
            # first, try natural major and minor comparisons:
            first_wave = ['ionian', 'aeolian']
            # second, try the other diatonic modes:
            second_wave = [names[0] for mode_idx, names in base_scale_mode_names['natural major'].items() if mode_idx not in [1,6]]
            # third, try the other standard scales:
            third_wave = ['harmonic minor', 'melodic minor', 'harmonic major', 'melodic major']
            for comp_name_list in [first_wave, second_wave, third_wave]:
                for comp_name in comp_name_list:
                    # comparison_scale = NewScale(comp_name)
                    comparison_factors = scale_name_factors[comp_name]
                    difference = self.factors - comparison_factors
                    # difference is a ChordModifier object, which we use if it is exactly 1 alteration:
                    if len(difference) == 1:
                        mod_val = list(difference.summary.values())[0]
                        if abs(mod_val) == 1:
                            difference_str = difference.get_name(check_chord_dicts=False)
                            return f'{comp_name} {difference_str}'
                    elif len(difference) == 0:
                        raise Exception(f"Exact match between exotic scale {self.factors} and comparison {comp_name}- this should never happen, why doesn't this exist as a registered scale name?")
            # reached end of loop and did not find a name:
            return 'Unknown'
        # pentatonic case:
        elif len(self) == 5:
            raise Exception('TBI')

    @property
    def name(self):
        if self.factors in factor_scale_names:
            return factor_scale_names[self.factors]
        else:
            return self._determine_exotic_scale_name()

    def _factors_str(self):
        """returns a string corresponding to this scale's factors.
        identical to str(self.factors) for scales without chromatic intervals,
        but wraps chromatic intervals in brackets if they exist"""
        if len(self.chromatic_intervals) == 0:
            return str(self.factors)
        else:
            factors_lst = []
            for iv in self.intervals:
                f = iv.factor_name
                if iv in self.chromatic_intervals:
                    lb, rb = self._chromatic_brackets
                    f = f'{lb}{f}{rb}'
                factors_lst.append(f)
            lb, rb = ScaleFactors._brackets
            factors_joined = ','.join(factors_lst)
            return f'{lb}{factors_joined}{rb}'

    def __str__(self):
        return f'{self._marker}{self.name} scale: {self._factors_str()}'

    def __repr__(self):
        return str(self)

    _marker = _settings.MARKERS['Scale']
    _chromatic_brackets = _settings.BRACKETS['chromatic_intervals']

pentatonic_factor_scale_names = {

}


# build modes and scale alias mappings for flexible init-by-string:
scale_name_aliases = {sn: [] for sn in standard_scale_names}
for base_name, mode_dict in base_scale_mode_names.items():
    # base_scale = NewScale(base_name)
    base_factors = scale_name_factors[base_name]
    for mode_num, name_list in mode_dict.items():
        # figure out what to name this mode
        # base names always take priority (i.e. 'natural major' over 'ionian'):
        if mode_num == 1:
            canonical_mode_name = base_name
        else: #
            # otherwise, use the first name listed in this mode's name list
            canonical_mode_name = name_list[0]

        # start empty list of aliases if one does not already exist:
        if canonical_mode_name not in scale_name_aliases:
            scale_name_aliases[canonical_mode_name] = []
        # all names in each mode list are valid aliases:
        for name in name_list:
            scale_name_aliases[canonical_mode_name].append(name)

        # mode_intervals = base_intervals.mode(mode_num)
        if mode_num != 1:
            mode_factors = base_factors.mode(mode_num)
            if mode_factors in factor_scale_names:
                # catch if this mode already exists in registered scale names
                # (e.g. aeolian mode as natural minor)
                print(f'Found a clash between mode {mode_num} of {base_name} and pre-registered scale {factor_scale_names[mode_factors]}')
                existing_name = factor_scale_names[mode_factors]
                scale_name_aliases[existing_name].extend(name_list)
                print(f'Extended aliases to: {scale_name_aliases[existing_name]}')
            else:
                # add new entry to definitive factor-name mapping
                factor_scale_names[mode_factors] = canonical_mode_name
                print(f'Added entry to definitive factor-name mapping: {factor_scale_names[mode_factors]}')

# build reverse mapping:
alias_scale_names = unpack_and_reverse_dict(scale_name_aliases, include_keys=True)
scale_name_factors = reverse_dict(factor_scale_names)
# scale name factors should inclde all aliases as well:
for alias, canonical_name in alias_scale_names.items():
    assert canonical_name in scale_name_factors
    scale_factors = scale_name_factors[canonical_name]
    if alias == canonical_name:
        print(f'Duplicated alias: {alias}')
    else:
        scale_name_factors[alias] = scale_factors




exotic_scale_name_factors = {

}
### bebop scale nonsense:
raw_bebop_intervals = [P1, M2, M3, P4, P5, m6, M6, M7]
bebop_degree_intervals = {d: IrregularInterval(raw_bebop_intervals[d-1].value, d, 8) for d in range(1,9)}
bebop_intervals = list(bebop_degree_intervals.values())

whole_tone_degree_intervals = {d: IrregularInterval(2*(d-1), d, 6, 12) for d in range(1,7)}
whole_tone_intervals = list(whole_tone_degree_intervals.values())

#
#
# ######################
# # important output: reverse dict that maps all scale/mode names to their intervals:
# mode_name_intervals = unpack_and_reverse_dict(interval_mode_names)
# ######################
#
# # initialise empty caches:
# cached_consonances = {}
# cached_pentatonics = {}
#
# # pre-initialised scales for efficient import by other modules instead of re-init:
# NaturalMajor = MajorScale = Scale('major')
# Dorian = DorianScale = Scale('dorian')
# Phrygian = PhrygianScale = Scale('phrygian')
# Lydian = LydianScale = Scale('lydian')
# Mixolydian = MixolydianScale = Scale('mixolydian')
# NaturalMinor = MinorScale = Aeolian = AeolianScale = Scale('minor')
# Locrian = LocrianScale = Scale('locrian')
#
# HarmonicMinor = HarmonicMinorScale = Scale('harmonic minor')
# HarmonicMajor = HarmonicMajorScale = Scale('harmonic major')
# MelodicMinor = MelodicMinorScale = Scale('melodic minor')
# MelodicMajor = MelodicMajorScale = Scale('melodic major')
#
# BebopScale = Scale('major', chromatic_intervals = [m6])
# WholeToneScale = Scale(...)
#
# # dict mapping parallel major/minor scales:
# parallel_scales = {NaturalMajor: NaturalMinor,
#                    HarmonicMajor: HarmonicMinor,
#                    MelodicMajor: MelodicMinor}
# # parallel scales are symmetric:
# parallel_scales.update(reverse_dict(parallel_scales))
#
# # special 'full minor' scale that includes notes of natural, melodic and harmonic minors:
# FullMinor = FullMinorScale = Scale('minor', chromatic_intervals=[M6, M7], alias='full minor')
# # and full major equivalent for symmetry:
# FullMajor = FullMajorScale = Scale('major', chromatic_intervals=[m6, m7], alias='full major')
#
# MajorPentatonic = MajorPentatonicScale = MajorPent = MajPent = Subscale('major pentatonic')
# MinorPentatonic = MinorPentatonicScale = MinorPent = MinPent = Subscale('minor pentatonic')
#
# common_scales = [MajorScale, Dorian, Phrygian, Lydian, Mixolydian, Aeolian, Locrian, HarmonicMajor, HarmonicMinor, MelodicMajor, MelodicMinor]
# common_subscales = list(subscales_to_aliases.keys())
#
# # cached scale attributes for performance:
# if _settings.PRE_CACHE_SCALES:
#     cached_consonances.update({c: c.consonance for c in (common_scales + common_subscales)})
#     cached_pentatonics.update({c: c.pentatonic for c in common_scales})