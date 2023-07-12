from .intervals import *
# from scales import interval_scale_names, key_name_intervals
from .util import rotate_list, reverse_dict, unpack_and_reverse_dict, numeral_subscript, reduce_aliases, auto_split, check_all, log
from .chords import Factors, AbstractChord, chord_names_by_rarity, chord_names_to_intervals, chord_names_to_factors
from .qualities import ChordModifier, Quality
from .parsing import num_suffixes, numerals_roman, is_alteration, offset_accidentals
from . import notes, _settings
from math import floor, ceil
import re




# ScaleFactors are the types of Factors that apply to Scale objects:
class ScaleFactors(Factors):
    def __init__(self, *args, chromatic=None, **kwargs):
        if chromatic is not None:
            # store any chromatic factors explicitly initialised along with this object:
            self.chromatic = ScaleFactors(chromatic)
        else:
            # pull out implicit chromatic intervals that are demarcated with square brackets:
            if len(args) == 1 and type(args[0]) is str:
                inp_string = args[0]
                inp_factor_list, chromatic = self._parse_out_chromatic_factors(inp_string)
                # recast as tuple for parent class init:
                args = (inp_factor_list,)
                # recast chromatics as ScaleFactors object:
                if len(chromatic) > 0:
                    self.chromatic = ScaleFactors(chromatic)
                else:
                    self.chromatic = None
            else:
                self.chromatic = None



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

        # sanity check to avoid producing scales with duplicate intervals:
        # (e.g. the scale 'major #3' which has two factors both on the P4 interval)
        scale_intervals = self.to_intervals()
        if len(scale_intervals) != len(set(scale_intervals)):
            raise ValueError(f'ScaleFactors object ({self}) contains a repeated interval on multiple factors: {self.as_intervals.repeated()}')

    def _parse_out_chromatic_factors(self, inp_string):
        """Given a single input string of the form: '1, b2, [b3], 3' etc.
        search that string for elements enclosed within square brackets, and
        separate them out into a new list"""
        if '[' in inp_string and ']' in inp_string:
            bracket_matches_list = re.findall(r'\[([^]]+)\]', inp_string)
            output_string = re.sub(r'\[[^]]+\]', '', inp_string) # replace brackets and their contents with emptystring
            output_string = re.sub(r',\s*,', ',', output_string).strip()  # remove empty spaces and trailing whitespace
            output_list = [f for f in auto_split(output_string, allow='#♯𝄪b♭𝄫/') if f != ''] # strip out leftover emptystrings if any remain
            return output_list, bracket_matches_list
        else:
            return auto_split(inp_string, allow='#♯𝄪b♭𝄫/'), []

    def to_intervals(self, chromatic=False, as_dict=False):
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

        if chromatic and self.chromatic is not None:
            # add chromatic intervals into the list as well and sort the resulting total
            iv_temp = factor_intervals[0]
            chromatic_intervals = [iv_temp.from_degree(d, offset=o, max_degree=iv_temp.max_degree) for d, o in self.chromatic.items()]
            factor_intervals = sorted(factor_intervals + chromatic_intervals)

        if not as_dict:
            return IntervalList(factor_intervals)
        elif as_dict:
            unique_keys = set([iv.degree for iv in factor_intervals])
            if len(unique_keys) != len(factor_intervals):
                raise ValueError(f'Cannot return ScaleFactors object as interval dict because it contains duplicate degrees: {chromatic_intervals} in {factor_intervals}')
            return {iv.degree:iv for iv in factor_intervals}

    def copy(self):
        return self.__class__({k:v for k,v in self.items()}, modifiers=self.modifiers, chromatic=self.chromatic)

    def __eq__(self, other):
        if other.__class__ is self.__class__:
            # ScaleFactors are equal if their factors and chromatic intervals are both the same:
            return (self.items() == other.items()) and (self.chromatic == other.chromatic)
        else:
            return False # not equal to objects of any other type

    # def _hashkey(self):
    #     """the input to the hash function that represents this object"""
    #     factors_part = ','.join([f'{k}:{v}' for k,v in self.items()])
    #     chromatic_part = ',' + ','.join([f'[{k}:{v}]' for k,v in self.chromatic.items()]) if self.chromatic is not None else '[]' # [(k,v) for k,v in self.chromatic.items()) if self.chromatic is not None else None]
    #     return factors_part + chromatic_part

    def __hash__(self):
        return hash(str(self))
        # return hash(self._hashkey())

    def _sharp_preference(self):
        """simple decision function to pick whether we use flats or sharps
        to represent chromatic intervals (which are not on any factor, so have
        no correct answer in this case)"""
        raised_degrees = [1 for k,v in self.items() if v > 0]
        lowered_degrees = [1 for k,v in self.items() if v < 0]
        # prefer sharps if there are more raised than lowered degrees:
        return sum(raised_degrees) > sum(lowered_degrees)

    def __str__(self):
        """differs from Factors.__str__ in needing to represent chromatic factors specially too"""
        if self.chromatic is None:
            return super().__str__()
        else:
            temp_dct = {k:v for k,v in self.items()}
            # add chromatic factors in the half-integer
            temp_dct.update({k+(v*0.5) : 0 for k,v in self.chromatic.items()})
            prefer_sharps = self._sharp_preference()
            factor_strs = []
            clb, crb = _settings.BRACKETS['chromatic_intervals']
            # for f,v in temp_dct.items():
            sorted_tmp_keys = sorted(temp_dct.keys())
            for f in sorted_tmp_keys:
                v = temp_dct[f]
                if type(f) is int: # normal factor
                    factor_str = f'{offset_accidentals[v][0]}{f}'
                    factor_strs.append(factor_str)
                else: # half degree, i.e. chromatic 'factor'
                    # render as sharpened floor of float if prefer sharps, else as flattened ceil:
                    f, v = (floor(f), 1) if prefer_sharps else (ceil(f), -1)
                    factor_str = f'{clb}{offset_accidentals[v][0]}{f}{crb}'
                    factor_strs.append(factor_str)
        lb, rb = self._brackets
        return f'{lb}{", ".join(factor_strs)}{rb}'

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
        mode_intervals = intervals.mode(N, preserve_degrees = (len(self) == 7))
        # (preserve degrees for heptatonic scales,
        # but don't worry about it for pentatonics etc.)
        factors_str = ','.join(mode_intervals.to_factors())
        return ScaleFactors(factors_str)



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
        obj.compound = (obj.degree != obj.extended_degree) # boolean flag
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
        self.factors, self.factor_intervals = self._parse_input( name, intervals, factors, alterations, chromatic_intervals, mode)

        if self.factors.chromatic is not None:
            self.chromatic_intervals = self.factors.chromatic.as_intervals
        else:
            self.chromatic_intervals = IntervalList([])

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

        self.cached_name = None # name retrieval is expensive, so we only do it once and cache it at that time

    ####### internal init subroutines:
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
            factors = canonical_scale_name_factors[canonical_name]

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
                if factors.chromatic is not None:
                    assert chromatic_intervals is None, "conflicting chromatic_intervals to Scale init"
                    chromatic_intervals = factors.chromatic.as_intervals
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
            chromatic_intervals = IntervalList([]) # chromatic_intervals is always an empty list if not set (not None)

        if mode != 1:
            # we want to the mode of whatever's been produced by names/intervals/factors
            assert (type(mode) is int and mode > 0), "Mode arg to Scale init must be a positive integer"
            # so we rotate the unstacked intervals and restack them: (an IntervalList method exists for this)
            new_intervals = intervals.mode(mode)
            # intervals = new_intervals
            # then recompute factors:
            factors = ScaleFactors(', '.join(new_intervals.pad(left=True, right=False).as_factors))
            if len(chromatic_intervals) > 0:
                # currently this intervals var doesn't include the chromatic intervals,
                # which are ALSO shifted by a mode rotation
                # so we shift those explicitly here:
                num_places = mode-1
                # the interval at the num_places index of the original intervals
                # is how far leftward the chromatic intervals must be shifted:
                left_shift = intervals[num_places]
                chromatic_intervals = (chromatic_intervals - left_shift).flatten()
                factors.chromatic = ScaleFactors(chromatic_intervals.as_factors)

        # now factors and intervals have necessarily been set, both including the tonic,
        # including any alterations and modal rotations that needed to be applied
        # so we can produce the factor_intervals; mapping of whole-tone degrees to their intervals:
        factor_intervals = {f:iv for f,iv in zip(factors, intervals)}

        return factors, factor_intervals

    def _parse_scale_name(self, scale_name):
        """takes a string denoting a scale name and returns its canonical form if it exists,
        along with a list of Modifier objects as alterations if any were detected"""
        # step 0: fast exact check, see if the provided name exists as a canonical name or alias:
        scale_name = scale_name.lower() if len(scale_name) > 1 else scale_name # cast to lowercase unless single character (e.g. 'M')
        if scale_name in canonical_scale_name_factors:
            log(f'Fast name check found "{scale_name}" as an existing canonical name')
            return scale_name, []
        elif scale_name in canonical_scale_alias_names:
            canonical_scale_name = canonical_scale_alias_names[scale_name]
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
        if reduced_name in canonical_scale_alias_names:
            canonical_scale_name = canonical_scale_alias_names[reduced_name]
            log(f'Slow name check found reduced name "{reduced_name}" as an existing canonical name')
            return canonical_scale_name, alterations

        wordbag = frozenset(reduced_name_words) # note: frozensets are hashable, unlike regular sets
        if wordbag in wordbag_scale_names:
            canonical_scale_name = wordbag_scale_names[wordbag]
            log(f'Slow name check found reduced name "{reduced_name}" as a rearrangement of canonical name: "{canonical_scale_name}"')
            return canonical_scale_name, alterations
        else:
            raise ValueError(f'{scale_name} re-parsed as {reduced_name_words} but could not find a corresponding scale by that name')

    ###### scale production methods:

    def subscale(self, keep=None, omit=None):
        """Return a subscale derived from this scale's factors,
        specified as either a list of factors to keep or to discard"""
        return self.__class__(factors=self.factors.subscale(keep=keep, omit=omit))

    def mode(self, N, sanitise=True):
        """Returns a new scale that is the Nth mode of this scale.
        (where mode 1 is identical to the existing scale)"""
        non_chromatic_intervals = IntervalList([iv for iv in self.intervals if iv not in self.chromatic_intervals])
        new_intervals = non_chromatic_intervals.mode(N, preserve_degrees = (self.order==7))
        if (len(self) < 7) and (sanitise):
            # scales that are less than heptatonic in length may need explicit sanitisation
            new_intervals = new_intervals.sanitise_degrees()

        # shift chromatic intervals as well:
        num_places = N-1
        # the interval at the num_places index of the original intervals
        # is how far leftward the chromatic intervals must be shifted:
        left_shift = non_chromatic_intervals[num_places]
        new_chromatic_intervals = (self.chromatic_intervals - left_shift).flatten()
        return NewScale(intervals=new_intervals, chromatic_intervals = new_chromatic_intervals)

    def get_pentatonic(self):
        """Returns the pentatonic subscale of this scale.
        For well-defined pentatonics like the major and minor, this is a simple lookup.
        Pentatonics of other scales are derived computationally by producing a subscale
            that minimises intervallic dissonance while preserving the scale's character."""
        # check if a pentatonic scale is defined under this scale's canonical name:
        naive_pentatonic_name = f'{self.name} pentatonic'
        if naive_pentatonic_name in all_scale_name_factors:
            return NewScale(naive_pentatonic_name)
        else:
            return self.compute_best_pentatonic()

    @property
    def pentatonic(self):
        return self.get_pentatonic()

    ##### utility, arithmetic, and magic methods:
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

    def __getitem__(self, i):
        """Retrieves the i'th item from this scale, which is the Interval at ScaleDegree i.
        if i is higher than this scale's max degree, return an appropriate compound interval"""
        if not isinstance(i, ScaleDegree):
            i = ScaleDegree(i, num_degrees = self.order)

        return self.degree_intervals[i]

    # scales hash according to their factors and their chromatic intervals:
    def __hash__(self):
        # return hash(tuple(self.factors, self.chromatic_intervals))
        return hash(str(self))

    ##### property flags:
    def is_diatonic(self):
        """A scale is diatonic if it is a mode of the natural major or minor scales"""
        if not self.is_chromatic():
            for mode in range(1,8):
                major_mode_factors = scale_name_factors[base_scale_mode_names['natural major'][mode][0]]
                if self.factors == major_mode_factors:
                    return True
        return False
    def is_heptatonic(self):
        """A scale is heptatonic if it has exactly 7 notes (including chromatic/passing notes)"""
        return len(self) == 7
    def is_pentatonic(self):
        """A scale is 'pentatonic' if it has exactly 5 notes (including chromatic/passing intervals)"""
        return len(self) == 5
    def is_chromatic(self):
        """A scale is 'chromatic' if it contains any chromatic/passing intervals"""
        return len(self.chromatic_intervals) > 0
    def is_natural(self):
        """A scale is natural if it is the natural major or minor scale"""
        return (self.factors in [all_scale_name_factors['major'], all_scale_name_factors['minor']])

    ### naming/display methods:
    def _determine_common_scale_name(self):
        if self.factors in canonical_scale_factor_names:
            return

    def _determine_rare_scale_name(self):
        """If this scale does not have a registered name, we try to call it an
        alteration of some existing scale"""
        # diatonic case:
        if len(self) == 7:
            # first, try natural major and minor comparisons
            # then the other diatonic modes
            # then the other standard scales
            waves = [['ionian', 'aeolian'], # natural scales
                     [names[0] for mode_idx, names in base_scale_mode_names['natural major'].items() if mode_idx not in [1,6]], # diatonic modes
                     ['harmonic minor', 'melodic minor', 'harmonic major', 'melodic major'], # non-diatonic heptatonic scales
                     chromatic_scale_factor_names.values(),
                     rare_scale_factor_names.values()]
        elif len(self) == 5:
            waves = [pentatonic_scale_factor_names.values(),
                     rare_scale_factor_names.values(),]
        else:
            waves = [chromatic_scale_factor_names.values(),
                     rare_scale_factor_names.values()]

        for comp_name_list in waves:
            for comp_name in comp_name_list:
                if isinstance(comp_name, list):
                    comp_name = comp_name[0]
                # comparison_scale = NewScale(comp_name)
                comparison_factors = all_scale_name_factors[comp_name]
                if len(comparison_factors) == self.factors:
                    difference = self.factors - comparison_factors
                    # difference is a ChordModifier object, which we use if it is exactly 1 alteration:
                    if len(difference) == 1:
                        mod_val = list(difference.summary.values())[0]
                        if abs(mod_val) == 1:
                            difference_str = difference.get_name(check_chord_dicts=False)
                            return f'{comp_name} {difference_str}'
                    elif len(difference) == 0:
                        raise Exception(f"Exact match between rare scale {self.factors} and comparison {comp_name}- this should never happen, why doesn't this exist as a registered scale name?")
        # reached end of loop and did not find a scale that this is an alteration of
        # so instead look for scales that this might be a *mode* of
        for mode_num in range(2, self.order+1):
            try: # modal rotations don't always produce clean results, so abandon an effort if it errors out
                mode_scale = self.mode(mode_num)
                if mode_scale.factors in canonical_scale_factor_names:
                    comparison_scale_name = mode_scale.name
                    # the comp scale is the Nth factor of this scale
                    # which means this scale is the (order-N+1)th factor of the comp scale
                    comparison_mode = (mode_scale.order - (mode_num-1)) + 1
                    num_suf = num_suffixes[comparison_mode]
                    return f'{comparison_scale_name} ({comparison_mode}{num_suf} mode)'
            except:
                pass # don't check this mode
        # reached end of loop and did not find a scale that this is a mode of, so give up
        return 'unknown'

    def get_name(self):
        # check for registered names for this scale's factors:
        if self.cached_name is not None:
            return self.cached_name
        elif not self.is_chromatic():
            if self.factors in canonical_scale_factor_names:
                self.cached_name = canonical_scale_factor_names[self.factors]
                return self.cached_name
        # no registered name for this scale's factors or intervals
        self.cached_name = self._determine_rare_scale_name()
        return self.cached_name
    @property
    def name(self):
        return self.get_name()

    def get_aliases(self):
        if self.name in canonical_scale_name_aliases:
            return canonical_scale_name_aliases[self]
        else:
            return []
    @property
    def aliases(self):
        return self.get_aliases()

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


# 'standard' scales are: natural/melodic/harmonic majors and minors, the most commonly used in pop music
standard_scale_names = {'natural major', 'natural minor', 'harmonic major', 'harmonic minor', 'melodic major', 'melodic minor'}
# 'base' scales are those not obtained by rotations of any other scales:
base_scale_names = {'natural major', 'melodic minor', 'harmonic minor', 'harmonic major'}
# 'natural' scales are just the natural major and minors:
natural_scale_names = {'natural major', 'natural minor'}

# the following dicts map scale factors to the corresponding scale names
# with names as a list, where the first item in the list is taken to be the
# 'canonical' name for that scale, with all others as valid aliases.

heptatonic_scale_factor_names = { # standard scales are defined here, modes and subscales are added later:
    ScaleFactors('1,  2,  3,  4,  5,  6,  7'): ['natural major', 'major'],
    ScaleFactors('1,  2, b3,  4,  5, b6, b7'): ['natural minor', 'minor'],
    ScaleFactors('1,  2,  3,  4,  5, b6,  7'): ['harmonic major'],
    ScaleFactors('1,  2, b3,  4,  5, b6,  7'): ['harmonic minor'],
    ScaleFactors('1,  2,  3,  4,  5, b6, b7'): ['melodic major'],
    ScaleFactors('1,  2, b3,  4,  5,  6,  7'): ['melodic minor', 'jazz minor', 'melodic minor ascending'], # (ascending)
    ScaleFactors('1, b2, b3,  4,  5,  6,  7'): ['neapolitan major', 'phrygian melodic minor'],
    ScaleFactors('1, b2, b3,  4,  5, b6,  7'): ['neapolitan minor', 'phrygian harmonic minor'],
    ScaleFactors('1, b2,  3,  4,  5, b6,  7'): ['double harmonic', 'double harmonic major'],

# while it's true that "melodic minor" can refer to a special scale that uses
# the the natural minor scale when descending, but that out-of-scope for now
    }
heptatonic_scale_name_factors = unpack_and_reverse_dict(heptatonic_scale_factor_names)

# this dict maps base scale names to dicts that map scale degrees to the modes of that base scale
base_scale_mode_names = {
   'natural major': {1: ['ionian', 'bilawal'], 2: ['dorian', 'kafi'], 3: ['phrygian', 'bhairavi'], 4: ['lydian', 'kalyan'],
                     5: ['mixolydian', 'khamaj'], 6: ['aeolian', 'asavari'], 7: ['locrian']},
   'melodic minor': {1: ['athenian'], 2: ['cappadocian', 'phrygian ♯6', 'dorian ♭2'],
                     3: ['asgardian', 'lydian augmented'], 4: ['pontikonisian', 'lydian dominant'],
                     5: ['olympian', 'aeolian dominant', 'mixolydian ♭6'],
                     6: ['sisyphean', 'aeolocrian', 'half-diminished'], 7: ['palamidian', 'altered dominant']},
  'harmonic minor': {1: [], 2: ['locrian ♯6'], 3: ['ionian ♯5'], 4: ['ukrainian dorian', 'ukrainian minor'],
                     5: ['phrygian dominant', 'spanish gypsy', 'egyptian'], 6: ['lydian ♯2', 'maqam mustar'], 7: ['altered diminished']},
  'harmonic major': {1: [], 2: ['blues heptatonic', 'dorian ♭5', 'locrian ♯2♯6'], 3: ['phrygian ♭4', 'altered dominant ♯5'],
                     4: ['lydian minor', 'lydian ♭3', 'melodic minor ♯4'], 5: ['mixolydian ♭2'],
                     6: ['lydian augmented ♯2'], 7: ['locrian 𝄫7']},
'neapolitan minor': {1: [], 2: ['lydian ♯6'], 3: ['mixolydian augmented'], 4: ['romani minor', 'aeolian ♯4'],
                     5: ['locrian dominant'], 6: ['ionian ♯2'], 7: ['ultralocrian', 'altered diminished 𝄫3']},
'neapolitan major': {1: [], 2: ['lydian augmented ♯6'], 3: ['lydian augmented dominant'], 4: ['lydian dominant ♭6'],
                     5: ['major locrian'], 6: ['half-diminished ♭4', 'altered dominant #2'], 7: ['altered dominant 𝄫3']},
'double harmonic':  {1: ['byzantine', 'arabic', 'gypsy major', 'flamenco', 'major phrygian', 'bhairav'],
                     2: ['lydian ♯2 ♯6'], 3: ['ultraphrygian'], 4: ['hungarian minor', 'gypsy minor', 'egyptian minor', 'double harmonic minor'],
                     5: ['oriental'], 6: ['ionian ♯2 ♯5'], 7: ['locrian 𝄫3 𝄫7']},
                 }

pentatonic_scale_factor_names = {
    # natural pentatonics and their modes:
    ScaleFactors('1,  2,  3,  5,  6'): ['major pentatonic', 'natural major pentatonic', 'ryo'], # mode 1
    ScaleFactors('1,  2,  4,  5, b7'): ['egyptian pentatonic'], # mode 2
    ScaleFactors('1, b3,  4, b6, b7'): ['blues minor pentatonic', 'phrygian pentatonic', 'minyo', 'man gong'], # mode 3
    ScaleFactors('1,  2,  4,  5,  6'): ['yo', 'ritsu', 'ritusen'], # mode 4
    ScaleFactors('1, b3,  4,  5, b7'): ['minor pentatonic', 'natural minor pentatonic', 'yo'], # mode 5

    # modes of the hirajoshi / in scale:
    ScaleFactors('1,  2, b3,  5, b6'): ['hirajoshi'], # mode 1
    ScaleFactors('1, b2,  4, b5, b7'): ['iwato', 'sachs hirajoshi'], # mode 2
    ScaleFactors('1,  3,  4,  6,  7'): ['kumoi', 'kumoijoshi'], # mode 3
    ScaleFactors('1, b2,  4,  5, b6'): ['hon kumoi', 'hon kumoijoshi', 'sakura pentatonic', 'in', 'in sen'], # mode 4
    ScaleFactors('1,  3, #4,  5,  7'): ['amritavarshini', 'chinese', 'burrows hirajoshi'], # mode 5

    # modes of the dorian pentatonic:
    ScaleFactors('1,  2, b3,  5,  6'): ['dorian pentatonic'], # mode 1
    ScaleFactors('1, b2,  4,  5, b7'): ['kokinjoshi'], # mode 2
    ScaleFactors('1, b3,  4, b5, b7'): ['minor b5 pentatonic'], # mode 5

    # pentatonics derived from (flattened) 9th chords:
    ScaleFactors('1,  2,  3,  5,  7'): ['blues major pentatonic', 'maj9 pentatonic', 'major 9th pentatonic'],
    ScaleFactors('1,  2,  3,  5, b7'): ['dominant pentatonic', 'dominant 9th pentatonic'],
    ScaleFactors('1,  2, b3,  5, b7'): ['pygmy', 'm9 pentatonic', 'minor 9th pentatonic'],
    ScaleFactors('1,  2, b3,  5,  7'): ['minor-major pentatonic', 'mmaj9 pentatonic'],
    ScaleFactors('1,  2,  3, #5, b7'): ['augmented pentatonic', 'aug9 pentatonic'],
    ScaleFactors('1,  2,  3, #5,  7'): ['augmented major pentatonic', 'augM9 pentatonic'],
    ScaleFactors('1,  2, b3, b5,  6'): ['diminished pentatonic', 'dim9 pentatonic'],
    ScaleFactors('1, b2, b3, b5,  6'): ['diminished minor pentatonic', 'dmin9 pentatonic', ],
    ScaleFactors('1,  2, b3, b5,  b7'): ['half-diminished pentatonic', 'hdim9 pentatonic'],
    ScaleFactors('1, b2, b3, b5,  b7'): ['half-diminished minor pentatonic', 'hdmin9 pentatonic'],
    ScaleFactors('1, #2,  3,  5,  b7'): ['hendrix pentatonic', 'dominant 7#9 pentatonic', '7#9 pentatonic'],
    ScaleFactors('1, b2,  3,  5,  b7'): ['dominant minor pentatonic', 'dominant 7b9 pentatonic', '7b9 pentatonic', ],

    # misc:
    ScaleFactors('1,  2,  4,  5,  7'): ['suspended', 'suspended pentatonic'],
    ScaleFactors('1,  3,  4,  5,  7'): ['okinawan'],
    ScaleFactors('1, b2, b3,  5, b6'): ['balinese'], # 2nd mode of okinawan scale
    ScaleFactors('1,  2,  3,  5, b6'): ['major b6 pentatonic'],

    }

pentatonic_scale_name_factors = unpack_and_reverse_dict(pentatonic_scale_factor_names)

chromatic_scale_factor_names = {
    ScaleFactors('1,  3,  4, [b5], 5,  7'): ['minor blues', 'minor blues hexatonic'],
    ScaleFactors('1,  2, [b3], 3,  5,  6'): ['major blues', 'major blues hexatonic'],
    ScaleFactors('1, 2, 3, 4, 5, 6, [b7],7'): ['bebop dominant'],
    ScaleFactors('1, 2, 3, 4, 5,[b6], 6, 7'): ['bebop', 'bebop major', 'barry harris', 'major 6th diminished'],
    ScaleFactors('1, 2,b3, 4, 5,[b6], 6, 7'): ['bebop minor', 'bebop melodic minor', 'minor 6th diminished'],
    # ScaleFactors('1, b2, [b3], 4, 5, b6, [b7]'): ['in', 'sakura'],
    }
print(f'=== Reversing chromatic scale factors')
chromatic_scale_name_factors = unpack_and_reverse_dict(chromatic_scale_factor_names)

# unusual scales with that ought not to be searched:
rare_scale_factor_names = {
    # 'exotic' heptatonic scales:
    ScaleFactors('1, b2,bb3,  4,  5, b6,bb7'): ['miyako-bushi'],
    ScaleFactors('1, b2,  3, #4,  5, b6,  7'): ['raga purvi'],
    ScaleFactors('1, b2,  3, #4,  5,  6,  7'): ['raga marva'],

    # hexatonic scales:
    ScaleFactors('1,  2,  3, #4, #5, #6'): ['whole tone', 'whole-tone'],

    # octatonic scales:
    ScaleFactors('1,  2, b3,  4, b5, b6,  6,  7'): ['whole-half', 'diminished'],
    ScaleFactors('1, b2, b3, b4, b5,  5,  6, b7'): ['half-whole'],
    ScaleFactors('1,  2,  3,  4,  5,  6, b7, 7'): ['bebop dominant octatonic'],
    ScaleFactors('1,  2,  3,  4,  5, #5,  6, 7'): ['bebop major octatonic', 'major 6th diminished octatonic', 'bebop octatonic', 'barry harris octatonic'],
    ScaleFactors('1,  2, b3,  4,  5, #5,  6, 7'): ['bebop minor octatonic', 'bebop melodic minor octatonic', 'minor 6th diminished octatonic'],

    # natural-melodic-harmonic hybrids:
    ScaleFactors('1, 2, b3,4, 5, b6, [6], b7, [7]'): ['full minor'],
    ScaleFactors('1, 2, 3, 4, 5, [b6], 6, [b7], 7'): ['full major'],
    }

rare_scale_name_factors = unpack_and_reverse_dict(rare_scale_factor_names)

base_mode_factor_names = {}
# loop across base scale modes to build more factor mappings:
for base_name, mode_dict in base_scale_mode_names.items():
    # retrieve the factors of a base scale:
    base_factors = heptatonic_scale_name_factors[base_name]
    # loop across this scale's theoretical modes:
    for mode_num, name_list in mode_dict.items():
        if base_name == 'natural major' and mode_num == 1:
            print(f'   ... Rotating to mode 1 of natural major')
        mode_factors = base_factors.mode(mode_num)
        if base_name == 'natural major' and mode_num == 1:
            print(f'   ...   (Done)')
        base_mode_factor_names[mode_factors] = name_list



registered_scale_name_dicts = [heptatonic_scale_factor_names,
                               chromatic_scale_factor_names,
                               pentatonic_scale_factor_names,
                               base_mode_factor_names,
                               rare_scale_factor_names,
                              ]

# mapping of all canonical scale names to their respective factors:
canonical_scale_factor_names = {}
canonical_scale_name_aliases = {}
for mapping in registered_scale_name_dicts:
    # canonical_scale_factor_names.update({factors: names[0] for factors, names in mapping.items()})
    for factors, names in mapping.items():
        # pick out a canonical name if this factors object has one:
        if factors not in canonical_scale_factor_names:
            canonical_name = names[0]
            # list one canonical name for each factors object:
            # print(f'Registering factors {factors} (id:{id(factors)}) to canonical name: {canonical_name}')
            canonical_scale_factor_names[factors] = canonical_name

            canonical_scale_name_aliases[canonical_name] = []
            this_scale_aliases = names[1:]
        else:
            # this factors object is already registered under another canonical name
            # (e.g. the ionian mode is already registered as 'natural major')
            # so retrieve that canonical mode and use it to add aliases instead
            canonical_name = canonical_scale_factor_names[factors]
            log(f'Tried to register factors {factors} but already exist as: {canonical_scale_factor_names[factors]}, so must instead record new aliases: {names}')
            this_scale_aliases = names
        # append aliases to this canonical name if any exist:
        # print(f'Existing aliases: {canonical_scale_name_aliases[canonical_name]}, extending with: {this_scale_aliases}')
        canonical_scale_name_aliases[canonical_name].extend(this_scale_aliases)

# check for clashing intervals/factors:
canonical_scale_interval_names = {}
for f,n in canonical_scale_factor_names.items():
    fi = f.to_intervals(chromatic=True)
    if fi not in canonical_scale_interval_names:
        canonical_scale_interval_names[fi] = n
    else:
        print(f'Clash between scale {n} with intervals {fi}, already registered to: {canonical_scale_interval_names[fi]}')

# canonical_scale_interval_names = {f.as_intervals:n for f,n in
canonical_scale_name_factors = reverse_dict(canonical_scale_factor_names)
canonical_scale_alias_names = unpack_and_reverse_dict(canonical_scale_name_aliases, include_keys=True)

wordbag_scale_names = {frozenset(name.split(' ')):name for name in canonical_scale_name_factors.keys()}

# string replacements for scale searching:
scale_name_replacements = {
                        'major': ['maj', 'M', 'Δ', ],
                        'minor': ['min', 'm'],
                        'harmonic': ['H', 'h', 'harm', 'har', 'hic'],
                        'melodic': ['melo', 'mel', 'mic'],
                        'pentatonic': ['pent', '5tonic'],
                        'hexatonic': ['hex', '6tonic'],
                        'octatonic': ['oct', '8tonic'],
                        'mixolydian': ['mixo', 'mix'],
                        'dorian': ['dori', 'dor'],
                        'phrygian': ['phrygi', 'phryg'],
                        'lydian': ['lydi', 'lyd'],
                        'locrian': ['locri', 'loc'],
                        'diminished': ['dim',],
                        'dominant': ['dom',],
                        'augmented': ['aug', 'augm'],
                        'suspended': ['sus', 'susp'],
                        # '#': ['sharp', 'sharpened', 'raised'],
                        # 'b': ['flat', 'flattened', 'lowered'],
                        '2nd': ['second'],
                        '3rd': ['third'],
                        '4th': ['fourth'],
                        '5th': ['fifth'],
                        '6th': ['sixth'],
                        '7th': ['seventh'],
                          }
replacement_scale_names = unpack_and_reverse_dict(scale_name_replacements, include_keys=True)

rex_patterns = []
for target, substrings in scale_name_replacements.items():
    for substring in substrings:
        remainder = [char for char in target if char not in substring]
        remainder = ''.join(remainder)
        pattern = f'(?P<{target}>{substring}({remainder})?)'
        rex_patterns.append(pattern)

print(f'Extending canonical scale name mapping to all possible scale names')
all_scale_name_factors = {k:v for k,v in canonical_scale_name_factors.items()}
for alias, canonical_name in canonical_scale_alias_names.items():
    if alias not in all_scale_name_factors:
        alias_factors = canonical_scale_name_factors[canonical_name]
        all_scale_name_factors[alias] = alias_factors



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
