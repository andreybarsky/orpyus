from .intervals import *
# from scales import interval_scale_names, key_name_intervals
from .util import ModDict, rotate_list, reverse_dict, reverse_mod_dict, unpack_and_reverse_dict, numeral_subscript, reduce_aliases, check_all, log
from .chords import Factors, AbstractChord, Chord, ChordList, chord_names_by_rarity, chord_names_to_intervals, chord_names_to_factors
from .qualities import ChordModifier, Quality, Maj, Min, Dim, minor_mod, parse_chord_modifiers
from .parsing import num_suffixes, numerals_roman, is_alteration, offset_accidentals, auto_split, contains_accidental, sh, fl
from .display import chord_table
from . import notes, _settings, parsing
from math import floor, ceil
import re




### Scale class that spans diatonic scales, subscales, blues scales, octatonic scales and all the rest:

# scales are primarily defined from factors; this is how we declare them initially

class Scale:
    def __init__(self, name=None, intervals=None, factors=None, alterations=None, chromatic_intervals=None, mode=1):
        # check for intervals or factors being fed as first arg:
        name, intervals, factors = self._reparse_args(name, intervals, factors)

        # .factors is a Factors object that explains which diatonic degrees are present in the scale
        # .factor_intervals is a dict mapping from integer factors to the corresponding intervals
        # and .chromatic_intervals is a plain list of the chromatic (or 'passing') intervals, like blues notes
        self.factors, self.factor_intervals = self._parse_input( name, intervals, factors, alterations, chromatic_intervals, mode)

        # chromatic intervals, if supplied,  get rolled into the self.factors object:
        if self.factors.chromatic is not None:
            self.chromatic_intervals = self.factors.chromatic.as_intervals
        else:
            self.chromatic_intervals = IntervalList([])

        assert self.chromatic_intervals is not None

        # now we figure out how many degrees this scale has, and allocate degree_intervals accordingly:
        self.num_degrees = len(self.factors)
        self.degrees = [ScaleDegree(d, num_degrees = self.num_degrees) for d in range(1, self.num_degrees+1)]
        self.degree_intervals = ModDict({d: self.factor_intervals[f] for d,f in zip(self.degrees, self.factors)}, index=1, raise_values=True)
        self.interval_degrees = reverse_mod_dict(self.degree_intervals, index=0, max_key=11, raise_values=True)
        self.interval_factors = reverse_mod_dict(self.factor_intervals, index=0, max_key=11, raise_values=True)

        self.factor_degrees = ModDict({f:d for f,d in zip(self.factors, self.degrees)}, index=1, raise_values=True)
        self.degree_factors = ModDict({d:f for d,f in zip(self.degrees, self.factors)}, index=1, max_key=self.num_degrees)

        # the .intervals attribute includes both factor ('diatonic') and chromatic ('passing') intervals:
        self.intervals = IntervalList(list(self.factor_intervals.values()) + self.chromatic_intervals).sorted()

        # set quality object: (by re-using AbstractChord method that uses the exact same logic)
        self.quality = AbstractChord._determine_quality(self)

        self.cached_name = None # name retrieval is expensive, so we only do it once and cache it at that time

    ####### internal init subroutines:
    def _reparse_args(self, name, intervals, factors):
        """detect if intervals or factors have been given as first arg instead of name,
        and return corrected (name, intervals, factors) tuple"""
        # first see if we've just been given an existing Scale object:
        if isinstance(name, Scale):
            # if so, strip its factors and move on
            factors = name.factors
            name = None

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
        elif name.__class__.__name__ == 'Key':
            # accept re-casting from Key here too
            # just strip the factors attr from a Key object:
            factors = name.factors
            name = intervals = None
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
            if not intervals._seems_stacked():
                # stack intervals if they've been given as unstacked
                intervals = intervals.stack()
            # sanitise intervals so that they start with a root but do not end with an octave:
            intervals = intervals.strip().pad()

            # detect if we need to re-cast to irregular intervals:
            if len(intervals) > 7:
                # initialise IrregularIntervals with a max_degree of whatever was given:
                intervals = IntervalList([IrregularInterval(intervals[i].value, i+1, len(intervals)) for i in range(len(intervals))])
            else:
                # ensure no double accidentals and max of one interval per degree
                if not intervals.is_sanitised():
                    intervals = intervals.sanitise_degrees()

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
                intervals = factors.to_intervals(chromatic=False)
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
            print(f'Detected chromatic intervals as provided: {chromatic_intervals}')
            if len(chromatic_intervals) > 0:
                import ipdb; ipdb.set_trace()
            if not isinstance(chromatic_intervals, IntervalList):
                chromatic_intervals = IntervalList(chromatic_intervals)
            chromatic_str = ''.join(chromatic_intervals.as_factors)
            # reinitialise factors obj with chromatics:
            factors = ScaleFactors(dict(factors), chromatic=chromatic_str)

        else:
            chromatic_intervals = IntervalList([]) # chromatic_intervals is always an empty list if not set (not None)

        if mode != 1:
            # we want to the mode of whatever's been produced by names/intervals/factors
            assert (type(mode) is int and mode > 0), "Mode arg to Scale init must be a positive integer"
            # reassign factors to the mode of whatever they were:
            # (this handles chromatic factors etc. internally)
            factors = factors.mode(mode)

        # factors.chromatic = ScaleFactors(chromatic_intervals.as_factors)

        # now factors and intervals have necessarily been set, both including the tonic,
        # including any alterations and modal rotations that needed to be applied
        # so we can produce the factor_intervals; mapping of whole-tone degrees to their intervals:
        factor_intervals = ModDict({f:iv for f,iv in zip(factors, intervals)}, index=1, raise_values=True)

        return factors, factor_intervals

    def _parse_scale_name(self, scale_name):
        """takes a string denoting a scale name and returns its canonical form if it exists,
        along with a list of Modifier objects as alterations if any were detected"""
        # step 0: fast exact check, see if the provided name exists as a canonical name or alias:

        # make scale name lowercase:
        if len(scale_name) > 1 and scale_name != scale_name.lower():
            # kludge: most scale names are case-insensitive, but a few important markers are case-sensitive
            # like the accidental natural char 'N'
            # so we intercept these chars before lowercasing and reinstate them afterward:
            case_sensitive_chars = 'N'
            sub_chars = '$' # just case insensitive dummy chars that don't occur in scale names
            # intercept:
            for char,sub in zip(case_sensitive_chars, sub_chars):
                scale_name = scale_name.replace(char,sub)
            scale_name = scale_name.lower()
            # reinstate:
            for char,sub in zip(case_sensitive_chars, sub_chars):
                scale_name = scale_name.replace(sub,char)

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

    @cached_property
    def fractional_interval_degrees(self):
        """returns the mapping of NON-scale intervals to fractional degree numbers.
        covers the full 12-interval span for heptatonic scales, but not guaranteed
        to do so for smaller scales like pentatonics."""
        non_scale_intervals = [Interval(v) for v in range(1,12) if v not in self.interval_degrees]
        fractional_interval_degrees = {}
        for iv in non_scale_intervals:
            if (iv-1).mod in self.interval_degrees and (iv+1).mod in self.interval_degrees:
                degree_below = int(self.interval_degrees[iv-1])
                frac_degree = round(degree_below + 0.5, 1)
                fractional_interval_degrees[iv] = frac_degree
        return ModDict(fractional_interval_degrees, index=0, max_key=11, raise_values=True, raise_by=7)

    @cached_property
    def fractional_degree_intervals(self):
        """reverse mapping of self.fractional_interval_degrees"""
        return reverse_mod_dict(self.fractional_interval_degrees, index=1, max_key=7, raise_values=True)

    def _get_arbitrary_degree_interval(self, deg):
        """retrieves the interval for any degree relative to this scale,
        whether or not that degree is in this scale"""
        if deg in self.degree_intervals:
            return self.degree_intervals[deg]
        else:
            return self.fractional_degree_intervals[deg]

    def _get_arbitrary_interval_degree(self, iv):
        """retrieves the degree for any interval relative to this scale,
        whether or not that degree is in this scale"""
        if iv in self.interval_degrees:
            return self.interval_degrees[iv]
        else:
            return self.fractional_interval_degrees[iv]

    ###### scale production methods (and related subroutines):

    def has_parallel(self):
        """returns True if a parallel scale is defined for this one"""
        return (self.scale_name in parallel_scale_names)

    @property
    def parallel(self):
        """returns the parallel minor or major or a natural major or minor scale,
        or of harmonic/melodic minor or major scales"""
        if self in parallel_scales:
            return parallel_scales[self]
        else:
            raise Exception(f'No parallel scale defined for {self}')

    def subscale(self, keep=None, omit=None):
        """Return a subscale derived from this scale's factors,
        specified as either a list of factors to keep or to discard"""
        return Scale(factors=self.factors.subscale(keep=keep, omit=omit))

    def mode(self, N, sanitise=True):
        """Returns a new scale that is the Nth mode of this scale.
        (where mode 1 is identical to the existing scale)"""
        if N == 1:
            return Scale(self)
        else:
            # scale rotation logic is fully handled by the logic in
            # the ScaleFactors rotation method, including chromatics etc:
            mode_factors = self.factors.mode(N)
            return Scale(factors=mode_factors)

    # return all the modes of this scale, starting from wherever it is:
    def get_modes(self):
        if self.order < 8:
            return [self.mode(m) for m in range(2,self.order+1)]
        else:
            # special exception for octatonic scales, which are too hard to mode (for now):
            return [self]
    @property
    def modes(self):
        return self.get_modes()

    def compute_best_pentatonic(self, *args, **kwargs):
        ranked_pentatonics = list(self.compute_pentatonics(*args, display=False, **kwargs).keys())
        return ranked_pentatonics[0]

    def compute_pentatonics(self, display=True, preserve_character=True, preserve_quality=False, **kwargs):
        """Given this scale and its degree-intervals,
        find the size-5 subset of its degree-intervals that maximises pairwise consonance"""

        if self.order > 5:
            # compute allowable subscales and rank them by consonance
            candidates = {}
            if preserve_character:
                character = self.character
                possible_degrees_to_exclude = [d for d, iv in self.degree_intervals.items() if ((d != 1) and (iv not in character))]
            else:
                possible_degrees_to_exclude = [d for d, iv in self.degree_intervals.items() if d != 1]

            if preserve_quality:
                pass # TBI? preserve the (major or minor) third in this scale if it has one

            for deg1 in possible_degrees_to_exclude:
                other_degrees_to_exclude = [d for d in possible_degrees_to_exclude if (d not in {1, deg1} and d > deg1)]
                for deg2 in other_degrees_to_exclude:
                    remaining_degrees = [d for d in self.degree_intervals.keys() if d not in {deg1, deg2}]
                    subscale_candidate = self.subscale(keep=remaining_degrees)
                    subscale_candidate.assigned_name = f'{self.name} omit({int(deg1)},{int(deg2)})'
                    candidates[subscale_candidate] = subscale_candidate.consonance
            sorted_cands = sorted(candidates.keys(), key = lambda x: (x.consonance), reverse=True)

        elif self.order <= 5:
            # the pentatonic of this scale is itself
            sorted_cands =  {self: self.consonance}


        if display:
            from .display import DataFrame
            title = f'Computed pentatonic scales of {self}'
            pres_str = f'\n    while preserving scale character: {",".join(character.as_factors)}' if preserve_character else ''
            print(title + pres_str)

            df = DataFrame(['Subscale', 'Factors', 'Omit', 'Cons.'])
            for cand in sorted_cands:
                cand_iv_key = (cand.intervals, cand.chromatic_intervals if len(cand.chromatic_intervals) > 0 else None)
                name = cand.assigned_name if cand_iv_key not in canonical_scale_interval_names else canonical_scale_interval_names[cand_iv_key]
                omitted = [str(f) for f in self.factors if f not in cand.factors]
                # kept = [str(f) for f in cand.factors if f in self.factors]
                factors_str = str(cand.factors)[1:-1]
                df.append([name, factors_str, ','.join(omitted), round(cand.consonance,3)])
            df.show(margin=' | ', **kwargs)

        else:
            return {x: round(x.consonance,3) for x in sorted_cands}


    def get_pentatonic(self):
        """Returns the pentatonic subscale of this scale.
        For well-defined pentatonics like the major and minor, this is a simple lookup.
        Pentatonics of other scales are derived computationally by producing a subscale
            that minimises intervallic dissonance while preserving the scale's character."""
        # check if a pentatonic scale is defined under this scale's canonical name:
        naive_pentatonic_name = f'{self.name} pentatonic'
        if naive_pentatonic_name in all_scale_name_factors:
            return Scale(naive_pentatonic_name)
        else:
            return self.compute_best_pentatonic(preserve_character=True)
    @property
    def pentatonic(self):
        return self.get_pentatonic()

    @property
    def nearest_natural_scale(self):
        return self.find_nearest_natural_scale()
    # quality-of-life alias (because I keep getting them mixed up):
    @property
    def closest_natural_scale(self):
        return self.nearest_natural_scale

    def find_nearest_natural_scale(self, tiebreak=True):
        """return the natural scale that has the most intervallic overlap with this scale
        (defaulting to major in the rare event of a tie)"""

        major_similarity, minor_similarity = 0, 0
        for iv in self.intervals:
            if iv in MajorScale.interval_degrees:
                major_similarity += 1
            if iv in MinorScale.interval_degrees:
                minor_similarity += 1

        if major_similarity > minor_similarity:
            return MajorScale
        elif minor_similarity > major_similarity:
            return MinorScale
        else:
            # the two are tied in interval identity
            # so tiebreak on interval distance instead
            major_dist, minor_dist = 0, 0
            for i, iv in enumerate(self.intervals):
                major_distances_from_this_interval = MajorScale.intervals - iv
                lowest_major_distance = min([abs(d) for d in major_distances_from_this_interval])
                major_dist += lowest_major_distance

                minor_distances_from_this_interval = MinorScale.intervals - iv
                lowest_minor_distance = min([abs(d) for d in minor_distances_from_this_interval])
                minor_dist += lowest_minor_distance
            log(f'Slow check to find closest natural scale to {self.name}: major distance {major_dist}, minor distance {minor_dist}')

            if major_dist > minor_dist:
                return MajorScale
            elif minor_dist > major_dist:
                return MinorScale
            else:
                if tiebreak:
                    return MajorScale # tiebreak in favour of major
                else:
                    return None # both are valid

    @property
    def neighbouring_scale_names(self):
        return self.get_neighbouring_scale_names()
    def get_neighbouring_scale_names(self, ignore_chromatic=True):
        """return a list of registered Scale objects that differ from this one by only a semitone"""
        neighbours = []
        for f in self.factors:
            # loop across each factor (but not the first)
            if f != 1:
                val = self.factors[f]
                # try values for this factor that differ by one accidental
                # (i.e sharpening or flattening a natural, or natural-ing a sharp/flat)
                if val == 0:
                    vals_to_try = [-1, 1]
                else:
                    vals_to_try = [0]
                for v in vals_to_try:
                    new_factor_dct = dict(self.factors)
                    new_factor_dct[f] = v
                    try:
                        if ignore_chromatic:
                            new_factors = ScaleFactors(new_factor_dct)
                        else:
                            new_factors = ScaleFactors(new_factor_dct, chromatic=self.factors.chromatic)
                        if new_factors in canonical_scale_factor_names:
                            neighbour_name = canonical_scale_factor_names[new_factors]
                            neighbours.append(new_factors)
                    except:
                        # failure to initialise ScaleFactors object indicates factor incompatibility
                        # e.g. augmented 3rd and perfect 4th.
                        # that's fine, skip this attempt and continue as normal
                        continue
        return neighbours

    @property
    def neighbouring_scales(self):
        return self.get_neighbouring_scales()
    def get_neighbouring_scales(self, *args, **kwargs):
        """as get_neighbouring_scale_names, but initialises and returns Scale objects"""
        neighbour_names = self.get_neighbouring_scale_names(*args, **kwargs)
        return [Scale(n) for n in neighbour_names]


    @property
    def character(self, verbose=False):
        """if this is a mode, returns the intervals of this mode that are different to its nearest natural scale.
        if it is a natural scale, return the intervals that make it distinct from its parallel scale."""
        if self.is_natural() or self.is_natural_pentatonic():
            nearest_natural = self.parallel
        else:
            nearest_natural = self.find_nearest_natural_scale(tiebreak=False)
            if nearest_natural is None:
                # if equally close to both natural scales
                # TBI: find a better solution than just returning major scale?
                nearest_natural = MajorScale # this is technically equivalent to tiebreak=True

        base_intervals = nearest_natural.intervals
        scale_character = []
        for iv_self, iv_base in zip(self.intervals, base_intervals):
            if iv_self != iv_base:
                scale_character.append(iv_self)
        if verbose:
            print(f'Character of {self.name} scale: (with respect to {nearest_natural.name})')
        return IntervalList(scale_character)


    def get_pairwise_intervals(self, extra_tonic=False):
        """returns a dict of interval pairs inside this scale that each map to the
        relative interval between that pair"""
        pairwise = {}
        # outer loop is across degree intervals:
        for deg, left_iv in self.degree_intervals.items(): # range(1, len(self.degree_intervals)+1):  # (is this equivalent to mode rotation?)
            # inner loop is across all intervals from that degree, including chromatics:
            ivs = [self.get_interval_from_degree(i) for i in range(int(deg), (deg**1).extended_degree)] # degrees from this interval to an octave higher
            if len(self.chromatic_intervals) > 0:
                for civ in self.chromatic_intervals:
                    # raise chromatic intervals by an octave if they're below the left interval
                    ivs.append(civ if civ > left_iv else civ**1)
            ivs = sorted(ivs)
            for right_iv in ivs:
                pairwise[(left_iv, right_iv)] = right_iv - left_iv
                if extra_tonic and (deg == 1):
                    pairwise[('tonic', right_iv)] = right_iv - left_iv # extra value for tonic, to upweight in weighted sum
        return pairwise
    @property
    def pairwise_intervals(self):
        return self.get_pairwise_intervals(extra_tonic=False)

    def get_pairwise_consonances(self, extra_tonic=False):
        # simply lifted from AbstractChord class:
        return AbstractChord.get_pairwise_consonances(self, extra_tonic=extra_tonic)
        # (this internally calls self.pairwise_intervals, which is defined above)
    @property
    def pairwise_consonances(self):
        return self.get_pairwise_consonances(extra_tonic=True)

    def get_consonance(self):
        """Calculates the pairwise intervallic consonance of this scale as a float"""
        if self in cached_consonances:
            return cached_consonances[self]
        else:
            cons_list = list(self.get_pairwise_consonances(extra_tonic=True).values())
            raw_cons = sum(cons_list) / len(cons_list)
            # return raw_cons
            # the raw consonance comes out as maximum=0.759 for the most consonant scale (yo pentatonic)
            # and just over 0.645 for the most dissonant scale, the whole-tone scale
            # so we set the former to be just below 1 and the latter to be just above 0,
            # and rescale the entire raw consonance range within those bounds:
            max_cons = 0.76
            min_cons = 0.64

            rescaled_cons = (raw_cons - min_cons) / (max_cons - min_cons)
            if _settings.DYNAMIC_CACHING:
                cached_consonances[self] = rescaled_cons
            return rescaled_cons
    @property
    def consonance(self):
        # property wrapper around get_consonance method
        return self.get_consonance()


    ### Key production methods:
    def on_tonic(self, tonic):
        """returns a Key object corresponding to this Scale built on a specified tonic"""
        # if not isinstance(tonic, Note):
        #     tonic = notes.Note.from_cache(tonic)
        # lazy import to avoid circular dependencies:
        from .keys import Key
        return Key(factors=self.factors, tonic=tonic)


    ##### utility, arithmetic, and magic methods:
    def __len__(self):
        """A scale's length is the number of intervals it has before the octave,
        so that all diatonic scales have length 7, and all pentatonic scales
        have length 5, and chromatic passing notes add 1 to this count,
        so that (for example) the blues scale has length 6"""
        return len(self.intervals)
    @property
    def len(self):
        return len(self)
    @property
    def size(self):
        # Scale.size is eqivalent to Scale.factors.size
        return len(self)

    @property
    def members(self):
        # a Scale's members are its intervals
        return self.intervals

    @property
    def span(self):
        """returns a raw list of intervals including the octave/span above"""
        out = [iv for iv in self.intervals]
        out.append(self.intervals[0] + 12)
        return out

    @property
    def order(self):
        """A scale's order is the number of factors/degrees it has, not counting
        chromatic intervals. So the blues scale has order 5, even though it contains
        a 6th passing note"""
        return len(self.factors)

    def get_interval_from_degree(self, i):
        """Retrieves the i'th item from this scale, which is the Interval at ScaleDegree i.
        if i is higher than this scale's max degree, return an appropriate compound interval"""
        if not isinstance(i, ScaleDegree):
            i = ScaleDegree(i, num_degrees = self.order)
        iv = self.degree_intervals[i]
        # now raise or lower the octave of that interval depending on the degree:
        if i.compound:
            # increase the interval's octave: (using the interval __pow__ method)
            iv = iv ** i.octave
        return iv

    def __eq__(self, other):
        assert type(other) is Scale, """Scales can only be compared to other Scales"""
        return self.factors == other.factors

    def __getitem__(self, i):
        """Indexing a Scale with i returns the interval on degree i of that Scale,
        which can be a compound interval if i exceeds the scale's highest degree."""
        return self.get_interval_from_degree(i)

    def __call__(self, i, order=3):
        """Calling a Scale with a degree i produces the triad chord built on that degree.
        Optionally, the order arg can be specified to return non-triad chords."""
        return self.get_chord(i, order=order)

    def get_chord(self, i, order=3, linked=True):
        """returns the AbstractChord built on degree i of this Scale,
            by selecting degree i, i+2, etc. (i.e. play-one skip-one construction)
        this produces familiar tertian chords when used on diatonic scales, but
            not necessarily for other scales like pentatonics.
        to produce tertian chords specifically (or their nearest equivalents),
            see Scale.get_tertian_chord """
        root_offsets = [i] + [i + (o*2) for o in range(1, order)]
        scale_intervals = [self.get_interval_from_degree(i) for i in root_offsets]
        # shift left to get chord that starts on root:
        start_interval = scale_intervals[0]
        # drop degree from intervals (and cast away from IrregularInterval objects) to get nice chord names:
        chord_intervals = IntervalList([Interval(iv.value) for iv in scale_intervals]) - start_interval
        if linked:
            return ScaleChord(chord_intervals, scale=self, degree=i)
        else:
            return AbstractChord(chord_intervals)

    def chord(self, i, order=3, linked=True):
        """convenience wrapper around Scale.get_chord; see the documentation for that method
        (note that this wrapper breaks the convention that nouns are properties and verbs are methods;
        'chord' is a noun, but Scale.chord is meaningless without a degree arg, so it hopefully remains intuitive)"""
        return self.get_chord(i, order, linked=linked)

    def get_tertian_chord(self, i, order=3, linked=True, prefer_chromatic=False):
        """returns an AbstractChord built on degree i of this Scale,
        by attempting to construct a chord using this scale's degrees that is as
        tertian as possible. may not always work, but will always try to return something."""
        assert i in self.degrees, f'{self.name} does not have a degree {degree}'

        # first try ordinary get_chord method (with spaced-degree harmonisation)
        # and see if the result is tertian:
        naive_chord = self.get_chord(i, order=order, linked=linked)
        if naive_chord.is_tertian() or naive_chord.is_inverted_tertian():
            # if so, just return it
            log(f'Degree {i}: Naive spaced chord construction returns a tertian chord: {naive_chord}')
            return naive_chord

        # otherwise, try building a tertian chord from other scale degrees
        root_degree = i
        root_factor = self.degree_factors[i]
        desired_chord_factors = range(1, (2*order), 2) # i.e. chord factors 1, 3, 5, etc.
        desired_scale_factors = [(((root_factor+f-2)%7)+1) for f in desired_chord_factors]
        available_chromatic_factors = {}
        if len(self.chromatic_intervals) > 0:
            for civ in self.chromatic_intervals:
                # note which degrees can be filled with a chromatic interval:
                for d in civ.common_degrees:
                    available_chromatic_factors[d] = civ
            for civ in self.chromatic_intervals:
                # fill possible degrees too:
                for d in civ.possible_degrees:
                    if d not in available_chromatic_factors:
                        available_chromatic_factors[d] = civ

        if not self.is_irregular():
            all_factors_available = True
            available_with_chromatic = False
            for f in desired_scale_factors:
                if f not in self.factors:
                    if f in available_chromatic_factors:
                        available_with_chromatic = True
                    else:
                        all_factors_available = False
                        log(f'Factor {f} not available in this subscale, so we cannot build an ordinary triad')
                        break
            if all_factors_available:
                # simply build a triad chord since we have all the notes needed:
                log(f'All desired factors {list(desired_scale_factors)} are available, so we can build an ordinary triad')
                root_interval = self.degree_intervals[root_degree]
                chord_intervals = [self.factor_intervals[root_factor]]
                for i, f in enumerate(desired_scale_factors[1:]):
                    if not prefer_chromatic:
                        # use raw factors first, then chromatic factors
                        factor_dicts = [self.factor_intervals, available_chromatic_factors]
                    else:
                        # use chromatic factors first:
                        factor_dicts = [available_chromatic_factors, self.factor_intervals]
                    for dct in factor_dicts:
                        if f in dct:
                            raw_interval = dct[f]
                            break

                    if raw_interval < chord_intervals[i-1]:
                        # raise by octave if we've lapped round the start of the scale:
                        chord_intervals.append(raw_interval ** 1)
                    else:
                        chord_intervals.append(raw_interval)
                chord_intervals = IntervalList(chord_intervals)
                log(f'With root interval: {root_interval} and chord intervals: {chord_intervals}, resulting in: {chord_intervals - root_interval}')
                if linked:
                    return ScaleChord(intervals=chord_intervals - root_interval, scale=self, degree=i)
                else:
                    return AbstractChord(inervals=chord_intervals - root_interval)

        # otherwise, could not construct a tertian chord using available scale degrees,
        # so generate all valid chords and make a shortlist from those

        valid_chords_on_root = self.valid_chords_on(root_degree, min_likelihood=0.7, min_consonance=0.5, min_order=order, max_order=order, no5s=False, inversions=True, display=False)
        log(f'Instead choosing a consonant chord from the valid chords that can be built on this degree:\n {[c.name for c in valid_chords_on_root]}')
        valid_chords_on_root = [c for c in valid_chords_on_root if c in self]

        if len(valid_chords_on_root) == 0:
            log(f'Did not find any with initial parameters, so expanding search parameters')
            valid_chords_on_root = self.valid_chords_on(root_degree, min_likelihood=0.5, min_consonance=0.4, min_order=order, max_order=order, no5s=True, inversions=True, display=False)
            valid_chords_on_root = [c for c in valid_chords_on_root if c in self]
            if len(valid_chords_on_root) == 0:
                log(f'Did not find any with expanded parameters, so dropping all search constraints except subscale membership')
                valid_chords_on_root = self.valid_chords_on(root_degree, min_likelihood=0, min_consonance=0, min_order=order, max_order=order, no5s=True, inversions=True, display=False)
                valid_chords_on_root = [c for c in valid_chords_on_root if c in self]
                assert len(valid_chords_on_root) > 0, f"Could somehow not make any chords at all of order={order} on degree {degree} of subscale: {self.name}"
        # secondary filtering step:
        shortlist = []
        for c in valid_chords_on_root:
            if c.is_tertian():
                log(f'Generated valid chord {c} is tertian, added to shortlist')
                shortlist.append(c)
                continue
            elif c.is_inverted_tertian():
                log(f'Generated chord {c} failed first tertian check, but an inversion of this chord is tertian: {c}')
                shortlist.append(c)
                continue
                # otherwise, prefer chords with 3rds and 5th if possible:
            elif (3 in c) and (5 in c):
                log(f'Generated chord {c} failed first and second tertian check')
                log(f'But does contains a 3rd and a 5th, so adding to shortlist')
                shortlist.append(c) # (since valid_chords is already sorted, shortlist is sorted by extension)
                continue
        if len(shortlist) >= 1:
            # return the most likely/consonant
            log(f'Degree {i}: Selecting first item from shortlist: {shortlist[0]}')
            return shortlist[0]
        else:
            # just return the most likely/consonant valid one
            log(f'Degree {i}: Did not find any chords that contain a 3rd and 5th, so just taking the first match')
            return valid_chords_on_root[0]

    def tertian_chord(self, i, order=3, linked=True):
        """convenience wrapper around Scale.get_tertian_chord;
        see the documentation for that method."""
        return self.get_tertian_chord(i, order, linked=linked)
    tertian = tertian_chord

    def get_chords(self, degrees=None, order=3, linked=True, display=False, pad=False, **kwargs):
        """returns a ChordList of the AbstractChords built on every degree
        of this Scale"""
        if degrees is None: # one for each scale degree by default
            degrees = self.degrees
        elif isinstance(degrees, (int, ScaleDegree)):
            degrees = [degrees]
        scale_chords = []
        if isinstance(order, int):
            # list of identical orders of the correct length:
            order = [order] * len(degrees)

        for i,d in enumerate(degrees):
            scale_chords.append(self.get_chord(d, order=order[i], linked=linked))
        if pad:
            # add an extra tonic chord on top:
            scale_chords.append(self.get_chord(self.degrees[0]**1, order=order, linked=linked))
        if display:
            title = f"Spaced-degree chords over: {self.__repr__()}"
            print(title)
            members = 'intervals' if type(self) == Scale  else 'notes'
            chord_table(scale_chords,
                        columns=['idx', 'chord', members, 'degrees', 'tert', 'cons'],
                        parent_scale=self, parent_degree='idx', margin=' | ',
                        **kwargs)
        else:
            return ChordList(scale_chords)
    chords = get_chords # convenience alias
    # @property
    # def chords(self):
    #     return self.get_chords(display=False)
    @property
    def triads(self):
        return self.get_chords(order=3, display=False)
    @property
    def tetrads(self):
        return self.get_chords(order=4, display=False)
    @property
    def pentads(self):
        return self.get_chords(order=5, display=False)
    @property
    def hexads(self):
        return self.get_chords(order=6, display=False)
    @property
    def heptads(self):
        return self.get_chords(order=7, display=False)

    def show_chords(self, degrees=None, order=3, display=True):
        # just a wrapper around get_chords but with default display=True
        return self.get_chords(degrees=degrees, order=order, display=display)
    # convenience aliases:
    harmonise = harmonize = show_chords
    # noun accessor:
    @property
    def harmony(self):
        return self.harmonise()

    def get_tertian_chords(self, degrees=None, order=3, linked=True, prefer_chromatic=False, display=False, **kwargs):
        """returns a ChordList of the (tertian) AbstractChords built on
        every degree of this Scale"""
        if degrees is None: # one for each scale degree by default
            degrees = self.degrees
        elif isinstance(degrees, (int, ScaleDegree)):
            degrees = [degrees]
        scale_chords = []
        if isinstance(order, int):
            # list of identical orders of the correct length:
            order = [order] * len(degrees)

        for i,d in enumerate(degrees):
            scale_chords.append(self.get_tertian_chord(d, order=order[i], linked=linked, prefer_chromatic=prefer_chromatic))
        if display:
            title = f"Attempted tertian chords over: {self.__repr__()}"
            print(title)
            members = 'intervals' if type(self) == Scale  else 'notes'
            chord_table(scale_chords,
                        columns=['idx', 'chord', members, 'degrees', 'tert', 'cons'],
                        parent_scale=self, parent_degree='idx', margin=' | ',
                        **kwargs)
        else:
            return ChordList(scale_chords)
    tertians = tertian_chords = get_tertian_chords # convenience aliases

    def show_tertian_chords(self, degrees=None, order=3):
        self.get_tertian_chords(degrees=degrees, order=order, display=True)
    harmonise_tertian = harmonize_tertian = show_tertians = show_tertian_chords
    @property
    def tertian_harmony(self):
        return self.harmonise_tertian()

    # accessors for notable chords of this scale:
    def get_dominant(self, order=4, linked=True):
        """return the ScaleChord built on the fifth"""
        # intervals of a dominant chord are always dominant:
        intervals_from_root = MajorScale.chord(5, order=order).intervals
        if linked:
            return ScaleChord(intervals=intervals_from_root, scale=self, degree=5)
        else:
            return AbstractChord(intervals=intervals_from_root)
    @property
    def dominant(self):
        return self.get_dominant(order=4)
    @property
    def dominant_triad(self):
        return self.get_dominant(order=3)

    def get_secondary_dominant(self, of=5, order=3, linked=True):
        "return the ScaleChord built on the fifth's fifth (or other non-tonic degree)"
        # note that a scale's major/minor quality does not influence the secondary dominant
        # but we do this calculation anyway in case it matters for more exotic scales
        secondary_interval_from_tonic = (self.degree_intervals[of] + 7).flatten()
        intervals_from_root = MajorScale.chord(5, order=order, linked=False).intervals

        if secondary_interval_from_tonic in self.interval_degrees:
            secondary_root_degree = self.interval_degrees[secondary_interval_from_tonic]
        else:
            secondary_root_degree = self.fractional_interval_degrees[secondary_interval_from_tonic]
        if linked:
            return ScaleChord(intervals=intervals_from_root, scale=self, degree=secondary_root_degree)
        else:
            return AbstractChord(intervals=intervals_from_root)
    @property
    def secondary_dominant(self):
        return self.get_secondary_dominant(order=4)
    @property
    def secondary_dominant_triad(self):
        return self.get_secondary_dominant(order=3)


    def progression(self, *degrees, order=3):
        """given a list of numeric integer degrees,
        produces a Progression with this scale's chords on those degrees"""
        from src.progressions import Progression
        if len(degrees) == 1: # unpack single list arg
            degrees = degrees[0]
        scale_chords = self.get_chords(degrees=degrees, order=order)
        return Progression(scale_chords)

    def valid_chords_on(self, degree, order=None, min_order=3, max_order=4, linked=True,
        min_likelihood=0.7, min_consonance=0, max_results=None, sort_by='likelihood',
        inversions=False, display=True, _root_note=None, no5s=False, **kwargs):
        """For a specified degree, returns all the chords that can be built on that degree
        that fit perfectly into this scale."""

        if order is not None:
            # overwrite min and max order if a specific order is given:
            min_order = max_order = order

        degree = int(degree)
        root_interval = self.get_interval_from_degree(degree)
        degrees_above_this_degree = [d for d in range(degree, degree+14) ]  # no chords span more than 14 degrees
        intervals_from_this_degree = IntervalList([self.get_interval_from_degree(d) for d in degrees_above_this_degree]) - root_interval
        # intervals_set = set(intervals_from_this_degree) # for faster lookup
        # intervals_from_this_degree = IntervalList([self.get_higher_interval(d) - root_interval for d in degrees_above_this_degree])

        if len(self.chromatic_intervals) > 0:
            # add chromatic intervals to the intervallist
            intervals_from_this_degree = IntervalList(list(intervals_from_this_degree) + list(self.chromatic_intervals)).sorted()

        # built a list of matching candidates as we go:
        shortlist = []
        for rarity, chord_names in chord_names_by_rarity.items():
            # for name in [c for c in chord_names if '(no5)' not in c]: # ignore no5 chords (no longer needed, no5s are not in that list:)
            for name in chord_names:

                # this will be a one-item dict if inversions are not allowd, or contain all possible inversions if they are
                candidate_intervals_by_inversion = {0: chord_names_to_intervals[name]}

                if inversions:
                    # invert this chord every which way and compare its intervals too
                    # first we need to know how big the main chord is:
                    chord_order = len(candidate_intervals_by_inversion[0])
                    # then loop through its possible bass degrees:
                    for i in range(1, chord_order):
                        inversion_intervals = AbstractChord(factors=chord_names_to_factors[name], inversion=i).intervals
                        candidate_intervals_by_inversion[i] = inversion_intervals

                for inversion, candidate_intervals in candidate_intervals_by_inversion.items():
                    is_match = True
                    for interval in candidate_intervals[1:]: # skip the root
                        if interval not in intervals_from_this_degree:
                            is_match = False
                            break
                    if is_match:
                        if linked:
                            candidate = ScaleChord(factors=chord_names_to_factors[name], inversion=inversion, scale=self, degree=degree)
                        else:
                            candidate = AbstractChord(factors=chord_names_to_factors[name], inversion=inversion)
                        if _root_note is not None: # for easy inheritance by Key class
                            candidate = candidate.on_bass(_root_note)
                        shortlist.append(candidate)

                        if no5s:
                            # also add the no5 version of this chord if it is at least a tetrad (but not for inversions)
                            if (inversion == 0) and (candidate.order >= 4) and (5 in candidate):
                                if linked:
                                    no5_candidate = ScaleChord(candidate.suffix + '(no5)', scale=self, degree=degree)
                                else:
                                    no5_candidate = AbstractChord(candidate.suffix + '(no5)')
                                shortlist.append(no5_candidate)

        # apply statistical minimums and maximums to our shortlist to decide what to keep:
        candidate_stats = {}
        # (and initialise sets containing 'normal' chord intervals for pruning):
        if inversions:
            non_inverted_intervals = set()
        if no5s:
            non_no5_intervals = set()

        if len(shortlist) == 0:
            import ipdb; ipdb.set_trace()

        for candidate in shortlist:
            if candidate.order <= max_order and candidate.order >= min_order:
                if candidate.likelihood >= min_likelihood and candidate.consonance >= min_consonance:
                    candidate_stats[candidate] = {'order': candidate.order,
                                                  'likelihood': round(candidate.likelihood,2),
                                                  'consonance': round(candidate.consonance,3)}
                    # add normal chords' intervals to the pruning comparison sets:
                    if inversions and (candidate.inversion == 0):
                        non_inverted_intervals.add(candidate_intervals)
                    if no5s and (5 in candidate):
                        non_no5_intervals.add(candidate.intervals)

        # if inversions were allowed, we prune the candidate list to remove inversions that have the same intervals as a non-inverted candidate:
        # TBI: we could prune repeated inversions having the same intervals too, by pruning for each inversion-place starting from the highest?
        # (idea: we could keep a dict that maps intervals to chords matching those intervals, and take the least rare from each)
        if inversions:
            # non_inverted_intervals = {c.intervals for c in candidate_stats if c.inversion == 0}
            pruned_candidates = {c:v for c,v in candidate_stats.items() if (c.inversion == 0) or (c.intervals not in non_inverted_intervals)}
            candidate_stats = pruned_candidates
        if no5s: # prune no5s as well:
            # non_no5_intervals = {c.intervals for c in candidate_stats if '(no5)' not in c.suffix}
            pruned_candidates = {c:v for c,v in candidate_stats.items() if (5 in c) or (c.intervals not in non_no5_intervals)}
            candidate_stats = pruned_candidates

        # sort result: (always by chord size first and tertian second)
        if sort_by=='likelihood':
            sort_key = lambda c: (-len(c), c.is_tertian(), -candidate_stats[c]['order'], candidate_stats[c]['likelihood'], candidate_stats[c]['consonance'])
        elif sort_by=='consonance':
            sort_key = lambda c: (-len(c), c.is_tertian(), -candidate_stats[c]['order'], candidate_stats[c]['consonance'], candidate_stats[c]['likelihood'])
        else:
            raise ValueError(f"valid_chords sort_by arg must be one of: 'likelihood', 'consonance', not: {sort_by}")

        sorted_cands = sorted(candidate_stats, key=sort_key, reverse=True)[:max_results]

        if display:
            title = f"Valid chords built on degree {degree} of {self}"
            print(title)
            chord_table(sorted_cands,
                        columns=['chord', 'intervals', 'degrees', 'tert', 'likl', 'cons'],
                        parent_scale=self, parent_degree=degree, margin=' | ',
                        max_results=max_results, **kwargs)
        else:
            return sorted_cands

    def __contains__(self, item):
        """if item is an Interval, does it fit in our list of diatonic-degree-intervals plus chromatic-intervals?
        if it is an IntervalList, do they all fit?"""
        if isinstance(item, (Interval, int)):
            if item % 12 == 0:
                return True # by definition
            else:
                return (Interval.from_cache(item).flatten() in self.intervals)
        elif isinstance(item, (list, IntervalList)):
            if type(item) == list:
                item = IntervalList(item)
            # for an iterable of intervals from root, check if they all belong:
            padded_intervals = self.intervals.pad()
            for iv in item.flatten():
                if iv not in padded_intervals:
                    return False
            return True
        elif isinstance(item, AbstractChord):
            if not isinstance(item, ScaleChord):
                raise TypeError("""A Scale does not know if it contains a given AbstractChord;
                                try Scale.contains_degree_chord or passing a ScaleChord object instead""")
            # a scale cannot be asked if it contains an AbstractChord without any other qualiifers,
            # but a ScaleChord contains its degree within the scale, so we wrap around
            # contains_degree_chord in this case:
            return self.contains_degree_chord(item.scale_degree, item)
        else:
            raise TypeError(f'Scale.__contains__ not defined for items of type: {type(item)}')

    def contains_degree_chord(self, degree, abs_chord, degree_interval=None):
        """checks whether a given AbstractChord on a given Degree of this Scale belongs in this Subscale"""
        if isinstance(abs_chord, str):
            abs_chord = AbstractChord(abs_chord)
        # assert type(abs_chord) == AbstractChord, "Scales can only contain AbstractChords"
        assert 1 <= degree <= self.factors.max_degree+0.9, "Scales can only contain chords built on degrees between 1 and 7"
        if degree not in self.degrees:
            return False # this subscale does not even have that degree
        if degree_interval is not None:
            # optionally require the specified degree to be a specific interval
            if self.degree_intervals[degree] != degree_interval:
                return False # this subscale does not have that interval
        root_interval = self.degree_intervals[degree]
        intervals_from_root = IntervalList([root_interval + iv for iv in abs_chord.intervals])
        # call __contains__ on resulting iv list:
        return intervals_from_root.flatten() in self

    # scales hash according to their factors and their chromatic intervals:
    def __hash__(self):
        # return hash(tuple(self.factors, self.chromatic_intervals))
        return hash(str(self))

    def which_intervals_chromatic(self):
        """returns a boolean list of the same length as self.intervals,
        which is True where that interval is chromatic and False otherwise"""
        if len(self.chromatic_intervals) == 0:
            # if this scale has no chromatic intervals, just return false everywhere
            return [False] * len(self.intervals)
        else:
            return [(iv in self.chromatic_intervals) for iv in self.intervals]

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
    def is_natural_pentatonic(self):
        """A scale is natural pentatonic if it is the major or minor pentatonic scale"""
        return (self.factors in [all_scale_name_factors['major pentatonic'], all_scale_name_factors['minor pentatonic']])
    def is_irregular(self):
        """A scale is irregular if it contains any IrregularIntervals,
        which in practice is true for octatonic scales (but not pentatonics)"""
        for iv in self.intervals:
            if isinstance(iv, IrregularInterval):
                return True
        return False

    @property
    def rarity(self):
        """Single integer representing this Scale's rarity with respect to other scales"""
        for r, names in canonical_scale_names_by_rarity.items():
            if self.scale_name in names:
                return r
        # unregistered scales are even rarer than the most rare registered scale:
        return r + 1

    @property
    def likelihood(self):
        # inverse of rarity
        return self.rarity_to_likelihood(self.rarity)
        # return round(1.0 - (0.1 * self.rarity), 1)

    @staticmethod
    def rarity_to_likelihood(rarity):
        # the publically-accessible calculation for the likelihood calculation
        return round(1.0 - (0.1 * rarity), 1)

    @staticmethod
    def likelihood_to_rarity(likelihood):
        # vice versa
        return int(round((1.0 - likelihood) * 10, 1))

    def is_subscale_of(self, other):
        """returns True if this scale's intervals all occur in the intervals
        of some other desired scale, and False otherwise"""
        if type(other) is not Scale:
            other = Scale(other)
        for iv in self.intervals:
            if iv not in other.intervals:
                # n.b. this double loop is O(2N) and could probably be optimised if necessary
                return False
        return True

    def find_possible_parent_scale_names(self, of_length=None):
        """returns a list of the names of scales that this Scale object
        could be a strict subscale of.
        arg 'of_length' controls the length that returned scales are allowed to be.
            if it is an integer, return only scales of that exact length.
            if it is a list, range, etc., return scales of any length in that list/range.
            if it is None (default), return any scales longer than this scale."""
        # check scales with lengths at least as long as this scale:
        if of_length is None:
            possible_parent_lengths = range(len(self)+1, 9)
        elif isinstance(of_length, int):
            possible_parent_lengths = [of_length]
        elif isinstance(of_length, (list, tuple, range)):
            assert check_all(of_length, 'isinstance', int), "possible parent scale lengths must be integers"
            possible_parent_lengths = of_length
        else:
            raise ValueError(f"arg 'of_length' must be int, list of ints, or None, but got: {type(of_length)}")

        match_names = []
        for pl in possible_parent_lengths:
            assert len(self) < pl, f"{self.name} can have no parent scales of length {pl} because it already has {len(self)} elements"
            possible_parent_names = canonical_scale_names_by_length[pl]
            possible_parent_name_intervals = {n:canonical_scale_name_intervals[n] for n in possible_parent_names}
            for p_name, p_intervals in possible_parent_name_intervals.items():
                is_match = True
                # loop over deg/val pairs in self and check if each has a match in the parent:
                for iv in self.intervals:
                    if iv not in p_intervals:
                        is_match = False
                        break
                if is_match:
                    match_names.append(p_name)
        return match_names
    @property
    def possible_parent_scale_names(self):
        return self.find_possible_parent_scale_names()

    def find_possible_parent_scales(self, heptatonic_only=False):
        """returns a list of Scale objects that this Scale object could be
        a strict subscale of."""
        # just wraps around possible_parent_scale_names but casts the results
        # to Scale objects:
        parent_names = self.possible_parent_scale_names(heptatonic_only=heptatonic_only)
        parent_scales = [Scale(n) for n in parent_names]
        return parent_scales
    @property
    def possible_parent_scales(self):
        return self.find_possible_parent_scales()

    def is_mode_of(self, other):
        """returns True if this Scale is a mode of a specified other Scale,
            and False otherwise.
        the 'other' arg is cast to Scale if it is not already one."""
        if type(other) is not Scale:
            other = Scale(other)

        if self.factors == other.factors:
            return True # trivial case 1
        elif len(self) != len(other):
            return False # trivial case 2
        else:
            return self in other.modes


    #### audio/guitar-related methods:

    def play(self, on='G3', up=True, down=True, **kwargs):
        ## if duration is not set, use a smaller default duration than that for chords:
        if 'duration' not in kwargs:
            kwargs['duration'] = 0.5
        # Scales don't have tonics, but we can just pick one arbitrarily:
        starting_note = notes.OctaveNote(on)
        assert up or down, "Scale must be played up or down or both, but not neither"
        notes_up = notes.NoteList([starting_note + iv for iv in self.intervals.pad(left=True, right=True)], strip_octave=False)
        full_notes = notes_up if up else NoteList([])
        if down:
            notes_down = full_notes[-2::-1]
            full_notes.extend(notes_down)
        full_notes.play(**kwargs)

    def show(self, tuning='EADGBE', **kwargs):
        """just a wrapper around the Guitar.show method, which is generic to most musical classes,
        so this method is also inherited by all Scale subclasses"""
        from .guitar import Guitar
        Guitar(tuning).show_scale(self, **kwargs)
    @property
    def fretboard(self):
        # just a quick accessor for guitar.show in standard tuning
        return self.show()

    ### naming/display methods:
    def roman_numeral(self, degree):
        """returns the roman numeral associated with the Chord on the desired degree of this scale"""
        chord = self.chord(degree)
        roman = numerals_roman[degree] # uppercase by default
        if chord.quality.major:
            pass # remain uppercase
            suffix = chord.suffix
        elif chord.quality.minor:
            roman = roman.lower()
            # exclude the 'm' suffix from minor chords - their minor-ness is indicated by the numeral case
            suffix = chord.suffix if chord.suffix != 'm' else ''
        else:
            # use upside down numerals instead of upper or lower case: ?
            # replacements = {'I': 'ı', 'V': 'ʌ'}
            # roman = ''.join(util.reduce_aliases(roman, replacements))
            # rare case of neither-major-nor-minor chord; maybe fall back on default assumptions of scale instead of this?
            roman = roman.lower() if ((scale.chord(1).quality.minor and degree in {1,4,5}) or (scale.chord(1).quality.major and degree in {2,3,6,7})) else roman
            suffix = chord.suffix
        return f'{roman}{suffix}'

    def _determine_common_scale_name(self):
        if self.factors in canonical_scale_factor_names:
            return canonical_scale_factor_names[self.factors]
        else:
            return None

    def _determine_rare_scale_name(self):
        """If this scale does not have a registered name, we try to call it an
        alteration of some existing scale"""
        # diatonic case:
        if len(self) == 7:
            # compare alterations to commonly registered scales,
            # in rough order of rarity:
            waves = [['ionian', 'aeolian']] + \
                     + [list(canonical_scale_names_by_rarity[r]) for r in (2,3,4)]
            # [, # natural scales
            #          [names[0] for mode_idx, names in base_scale_mode_names['natural major'].items() if mode_idx not in [1,6]], # diatonic modes
            #          ['harmonic minor', 'melodic minor', 'harmonic major', 'melodic major'], # non-diatonic heptatonic scales
            #          ['neapolitan minor', 'neapolitan major', 'double harmonic', 'miyako-bushi']]
                     # [name for name, facs in chromatic_scale_factor_names.items() if len(facs) == 7],
                     # [name for name, facs in rare_scale_factor_names.items() if len(facs) == 7]]
        elif len(self) == 5:
            # check natural pentatonics first, then all others
            natural_pentatonics = ['major pentatonic', 'minor pentatonic']
            other_pentatonics = [s for s in canonical_scale_names_by_length[5] if s not in natural_pentatonics]
            waves = [natural_pentatonics, other_pentatonics]
                     # [n for n in pentatonic_scale_factor_names.values() if n not in natural_pentatonics]]
        else:
            # just one wave, all scales of this length:
            waves = [canonical_scale_names_by_length[len(self)]]

        for comp_name_list in waves:
            for comp_name in comp_name_list:
                if isinstance(comp_name, list):
                    comp_name = comp_name[0]
                # comparison_scale = Scale(comp_name)
                comparison_factors = all_scale_name_factors[comp_name]
                if comparison_factors.size == self.factors.size:
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
        else:
            # try looking for a common/registered name:
            name = self._determine_common_scale_name()
            if name is None:
                # if not found, determine a rare name (i.e. alteration from a common scale)
                name = self._determine_rare_scale_name()
            self.cached_name = name # might be 'unknown', but otherwise we have exhausted possibilities
            return name

    @property
    def name(self):
        return self.get_name()

    @property
    def scale_name(self):
        """the name of this scale alone; not overriden by Key.name"""
        return Scale.get_name(self)

    def get_aliases(self):
        if self.name in canonical_scale_name_aliases:
            return canonical_scale_name_aliases[self.name]
        else:
            return []
    @property
    def aliases(self):
        return self.get_aliases()

    def _factors_str(self):
        """returns a string corresponding to this scale's factors.
        identical to str(self.factors) for scales without chromatic intervals,
        but wraps chromatic intervals in brackets if they exist"""
        return str(self.factors)

    def __str__(self):
        return f'{self._marker}{self.name} scale: {self._factors_str()}'

    def __repr__(self):
        return str(self)

    _marker = _settings.MARKERS['Scale']
    _chromatic_brackets = _settings.BRACKETS['chromatic_intervals']


##### supporting classes for Scale class: ScaleFactors, ScaleDegree, ScaleChord


# ScaleFactors are the types of Factors that apply to Scale objects:
class ScaleFactors(Factors):
    def __init__(self, *args, chromatic=None, **kwargs):
        """initialises a Scalefactors object, accepts arguments that would initialise
          a dict, or a string that describes scale factors relative to major,
          like e.g. for minor pentatonic: '1, b3, 4, 5, b7'
        optionally, 'chromatic' arg can be provided (in the same form, as dict etc.) to describe
          chromatic intervals that belong in a scale but are not on any of its degrees;
          chromatic factors can also be specified directly in the input string with square brackets,
          like e.g. for minor blues: '1, b3, 4, [b5], 5, b7'"""
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

        # init from input args/dict as parent Factors class does:
        super().__init__(*args, strip_octave=True, auto_increment_clashes=True, **kwargs)
        # but with an extra post-processing check over the default Factors init:
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
        lb, rb, = _settings.BRACKETS['chromatic_intervals']
        if lb in inp_string and rb in inp_string:
            bracket_matches_list = re.findall(r'\[([^]]+)\]', inp_string)
            output_string = re.sub(r'\[[^]]+\]', '', inp_string) # replace brackets and their contents with emptystring
            output_string = re.sub(r',\s*,', ',', output_string).strip()  # remove empty spaces and trailing whitespace
            output_list = [f for f in auto_split(output_string, allow_accidentals=True) if f != ''] # strip out leftover emptystrings if any remain
            return output_list, bracket_matches_list
        else:
            return auto_split(inp_string, allow_accidentals=True), []

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

    def __add__(self, other):
        # addition of ScaleFactors and ChordModifier preserves this ScaleFactors' chromatic attribute
        out = Factors.__add__(self, other)
        # check if any chromatic degrees have been overriden by now-in-scale degrees:
        if self.chromatic is not None:
            out.chromatic = ScaleFactors(self.chromatic)
            for deg, val in self.chromatic.items():
                if deg in out and out[deg] == val:
                    del out.chromatic[deg]
        return out

    def __sub__(self, other):
        if isinstance(other, ScaleFactors):
            if self.chromatic is not None or other.chromatic is not None:
                # special logic to compare chromatics as well
                factor_diff = Factors.__sub__(self, other)
                if self.chromatic is None:
                    chromatic_diff = Factors.__sub__(Factors(), other.chromatic)
                elif other.chromatic is None:
                    chromatic_diff = Factors.__sub__(self.chromatic, Factors())
                else:
                    chromatic_diff = Factors.__sub__(self.chromatic, other.chromatic)
                return (factor_diff, chromatic_diff)
        # otherwise, return a single diff object as normal
        return Factors.__sub__(self, other)

    def __eq__(self, other):
        if other.__class__ is self.__class__:
            # ScaleFactors are equal if their factors and chromatic intervals are both the same:
            return (self.items() == other.items()) and (self.chromatic == other.chromatic)
        else:
            return False # not equal to objects of any other type

    def __hash__(self):
        return hash(str(self))

    @property
    def size(self):
        """the size of a ScaleFactors object is the length of its factors
        plus the length of its chromatic factors object"""
        return len(self) + (len(self.chromatic) if self.chromatic is not None else 0)

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
            degree_intervals = [k + (v*0.2) for k,v in self.items()]
            chromatic_intervals = [k + (v*0.2) for k,v in self.chromatic.items()]
            # dict of shifted degrees that maps to True for chromatic intervals and degree for chromatics
            temp_dct = {d: (d in chromatic_intervals) for d in degree_intervals+chromatic_intervals}
            sorted_tmp_keys = sorted(temp_dct.keys())

            # temp_dct = {k:v for k,v in self.items()}
            # add chromatic factors in the half-integer
            # temp_dct.update({k + 0.1 + (v*0.5) : 0 for k,v in self.chromatic.items()})
            prefer_sharps = self._sharp_preference()
            factor_strs = []
            clb, crb = _settings.BRACKETS['chromatic_intervals']
            # for f,v in temp_dct.items():
            #
            # if log.verbose:
            #     import ipdb; ipdb.set_trace()
            for d in sorted_tmp_keys:
                is_chromatic = temp_dct[d]
                integer_degree = int(round(d))
                # -1 for flats, 1 for sharps, 0 for naturals:
                acc_offset = int(round((d - integer_degree) * 5))
                acc = offset_accidentals[acc_offset][0]
                factor_str = f'{acc}{integer_degree}'
                if is_chromatic:
                    factor_str = f'{clb}{factor_str}{crb}'
                factor_strs.append(factor_str)
                # else: # half degree, i.e. chromatic 'factor'
                #     # render as sharpened floor of float if prefer sharps, else as flattened ceil:
                #     f, v = (floor(f), 1) if prefer_sharps else (ceil(f), -1)
                #     factor_str = f'{clb}{offset_accidentals[v][0]}{f}{crb}'
                #     factor_strs.append(factor_str)
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

    def mode(self, N, sanitise=True):
        """returns the ScaleFactors corresponding to the Nth mode of this object"""
        if N == 1:
            return self
        else:
            original_intervals = self.to_intervals(chromatic=False)
            # preserve original degrees in the case of heptatonic scales:
            mode_intervals = original_intervals.mode(N, preserve_degrees = (len(self) == 7))

            if (len(self) < 7) and (sanitise):
                # scales that are less than heptatonic in length may need explicit sanitisation
                mode_intervals = mode_intervals.sanitise_degrees()

            factors_str = ','.join(mode_intervals.to_factors())
            mode_factors = [iv.degree for iv in mode_intervals]

            if self.chromatic is not None:
                # chromatic intervals are ALSO shifted by a mode rotation
                # depending on the intervals in the original list
                # so we shift those explicitly here:
                num_places = N-1
                left_shift = original_intervals[num_places]
                # the interval at the num_places index of the original intervals
                # is how far leftward the chromatic intervals must be shifted

                original_chromatic_intervals = self.chromatic.to_intervals()
                mode_chromatic_intervals = (original_chromatic_intervals - left_shift).flatten()

                # place chromatic factors on factors not used by main factors where possible:
                sanitised_mode_chromatic_intervals = IntervalList()
                for iv in mode_chromatic_intervals:
                    # does this chromatic degree occur in the factors:
                    if iv.degree in mode_factors:
                        # does the degree of the swapped-sign degree also occur in the factors?
                        try:
                            alternative_iv = iv.swap_accidental()
                            if alternative_iv.degree not in mode_factors:
                                # if not, prefer this swapped one instead
                                preferred_iv = alternative_iv
                                # sanitised_mode_chromatic_intervals.append(alternative_iv)
                            else:
                                # if BOTH exist, prefer the flat:
                                # (this is somewhat a kludge to ensure blues scale modes work as intended)
                                preferred_iv = iv if iv.offset_from_default < 0 else alternative_iv # pick the one that is flat
                                if (iv.degree, alternative_iv.degree) in [(4,5), (5,4)] and log.verbose:
                                    import ipdb; ipdb.set_trace()
                                pass
                                # sanitised_mode_chromatic_intervals.append(preferred_iv)
                        except:
                            # this interval can't be swapped, so just keep it
                            preferred_iv = iv
                    else:
                        preferred_iv = iv
                    sanitised_mode_chromatic_intervals.append(preferred_iv)


                chromatic_factors_str = ','.join(sanitised_mode_chromatic_intervals.to_factors())



                # kludge to ensure mode-matching works properly for minor/major blues etc.
                # if a #4 is the only chromatic note, and both a

            else:
                chromatic_factors_str = None

            factors_obj = ScaleFactors(factors_str, chromatic=chromatic_factors_str)
            return factors_obj



################################################################################

# usage convention for scale factors and scale degrees:
# a 'ScaleFactor' is an integer that is always either in the range 1-7,
# or enharmonic to the range 1-7 (i.e. the 8th factor is always an octave over the 1st)
# while a 'ScaleDegree' is an integer that is always continuous in its own range,
# so that e.g. the major pentatonic scale has factors (1,2,3,5,6) but degrees (1,2,3,4,5)
class ScaleDegree(int):
    """class representing the degrees of a scale with associated mod-operations"""
    def __new__(cls, degree, num_degrees=7):

        assert isinstance(degree, int)

        extended_degree = degree
        # note about indexing:
        # negative degrees are defined, but the degree 0 is not. (to avoid confusion!)
        # therefore, the degree one step below 1 is the degree 7(-1)
        if degree == 0:
            raise ValueError('ScaleDegree of 0 is ill-defined')

        sign = 1 if degree > 0 else -1
        if abs(degree) > num_degrees:
            # mod this degree to its base range, while preserving sign:
            degree = (((abs(degree) -1 ) % num_degrees) + 1) * sign
        if sign == -1:
            # this degree is negative, so invert it (so that negative 1 is correctly 7)
            degree = ((num_degrees+1) - abs(degree))

        obj = int.__new__(cls, degree) # int() on a degree returns the flat (non-compound) degree as int
        obj.degree = int(degree) # should always be identical to int(self)
        obj.num_degrees = num_degrees # i.e. scale size
        obj.extended_degree = extended_degree
        obj.octave = int((obj.extended_degree - obj.degree)/obj.num_degrees)
        obj.sign = 1 if obj.degree > 0 else -1
        obj.compound = (obj.degree != obj.extended_degree) # boolean flag
        return obj

    @staticmethod
    def of_scale(scale, degree):
        """alternative ScaleDegree init method, accepts a specified
        Scale object as the parent and instantiates a ScaleDegree of the
        appropriate order on the desired degree of that scale"""
        return ScaleDegree(degree, scale.factors.max_degree)
    # convenience alias:
    from_scale = of_scale

    # mathematical operations on scale degrees preserve extended degree and scale size:
    def __add__(self, other):
        # assert not isinstance(other, Interval), "ScaleDegrees cannot be added to intervals"
        assert type(other) is int, "ScaleDegrees can only be added with ints"
        new_degree = self.extended_degree + int(other)
        new_sign = 1 if new_degree > 0 else -1
        if new_degree == 0 or (new_sign != self.sign):
            # this addition/subtraction has sent the resulting value to 0,
            # which is illegal for a ScaleDegree,
            # or has had a sign swap and passed over the (illegal) zero value,
            # so we push it one degree more instead
            new_degree = self.extended_degree + (int(other) - self.sign)
        return ScaleDegree(new_degree, num_degrees=self.num_degrees)

    def __sub__(self, other):
        # just add with the negation of other:
        return self + (-other)

    def __abs__(self):
        """flatten compound degree into a simple one,
        i.e. abs(ScaleDegree(10)) == ScaleDegree(3)"""
        # similar behaviour to int(self), but returns a new ScaleDegree instead of an int
        return ScaleDegree(self.degree, num_degrees=self.num_degrees)

    def __pow__(self, octave):
        """octave transposition: a ScaleDegree raised by x raises it by that many octaves
        i.e. ScaleDegree(3)**1 == ScaleDegree(10)"""
        assert type(octave) is int, "ScaleDegrees can only be multipled (octave transposition) by integers"
        if octave >= 1:
            return self + (self.num_degrees * octave)
        elif octave <= -1:
            return self - (self.num_degrees * abs(octave))
            # return ScaleDegree(self.extended_degree-(self.num_degrees*(abs(octave))),  num_degrees=self.num_degrees)
        elif octave == 0: # return the same ScaleDegree
            return ScaleDegree(self.extended_degree, num_degrees=self.num_degrees)

    def __mul__(self, other):
        raise Exception('ScaleDegree.__mul__ not defined')
    def __div__(self, other):
        raise Exception('ScaleDegree.__div__ not defined')
    def __mod__(self, other):
        raise Exception('ScaleDegree.__mod__ not defined')

    # def __int__(self):
    #     # casting a degree to an int returns the (base, not extended) degree
    #     return self.degree
    def __eq__(self, other):
        # degrees are equal to the integer of their (base, not extended) degree:
        return int(self) == other
    def __hash__(self):
        # and scale degrees hash as integers for lookup purposes:
        return hash(int(self))

    def __str__(self):
        # ScaleDegree shows as integer char combined with caret above:
        degree_str = f'{self.degree}{self._diacritic}'
        if self.extended_degree != self.degree:
            # clarify that this is a compound degree:
            degree_str += f'({self.extended_degree})'
        if self.num_degrees != 7:
            # with an added subscript for non-diatonic (irregular) scale degrees
            degree_str += numeral_subscript(self.num_degrees) # i.e. would be '8' for regular scale degrees
        return degree_str

    def __repr__(self):
        return str(self)

    _diacritic = _settings.DIACRITICS['ScaleDegree']


class ScaleChord(AbstractChord):
    """AbstractChord that lives in a Scale, and understands a few things about
    harmony within the scale as well as its relative position inside it.
    Used inside Progression class."""
    def __init__(self, *args, scale=None, degree=None, factor=None, _init_abs=True, **kwargs):
        """as AbstractChord, except for the additional required args:
        scale: a Scale object, or string that casts to Scale
            denoting the scale this chord lives in.

        and one of:

        degree: an integer or ScaleDegree, denoting which degree of the above scale
            this chord sits on.
            can also be a float (like 2.5), denoting a fractional degree,
            indicating a chord whose root is not on a scale degree.
            (like a bIII chord in major scale)
        factor: an integer denoting which factor of the scale this chord sits on.
                (the difference is meaningful only for non-heptatonic scales).

        alternatively: can be defined by a single roman numeral string, such as
        'VII' or 'bIII'. if so, scale is auto-detected, though can be manually overwritten
        (e.g. with ScaleChord('V', scale='minor'))"""

        # initialise everything else as AbstractChord: (if not being inherited by KeyChord)

        init_by_numeral = False # control flow flag
        if len(args) == 1 and isinstance(args[0], str):
            # if initialised with a single string, this could be a roman numeral:
            name = args[0]
            # roman_value = parsing.begins_with_roman_numeral(name, return_value=True)
            if parsing.begins_with_roman_numeral(name):
                # name indeed begins with a roman numeral
                deg, abs_chord = parse_roman_numeral(name)
                init_by_numeral = True # ignore usual init routine

                if scale is None:
                    # auto detect major/minor scale from chord quality
                    # if not otherwise specified
                    scale = _detect_scale((deg, abs_chord))




        if _init_abs:
            AbstractChord.__init__(self, *args, **kwargs)

        if not isinstance(scale, Scale):
            scale = Scale(scale)




        self.scale = scale

        if degree is not None:
            assert factor is None, f"ScaleChord received clashing factor/degree args"
            if isinstance(degree, ScaleDegree):
                self.scale_degree = degree
                self.scale_factor = scale.degree_factors[degree]
                self.root_in_scale = True
            elif isinstance(degree, int):
                self.scale_degree = ScaleDegree.of_scale(self.scale, degree)
                self.scale_factor = scale.degree_factors[degree]
                self.root_in_scale = True
            elif isinstance(degree, float):
                # fractional degree whose root is out-of-scale
                upper, lower = ceil(degree), floor(degree)
                assert degree != upper and degree != lower # i.e. not a float equal to an integer
                self.scale_degree = round(lower + 0.5, 1) # ensure strict half-integer to 1d.p.
                self.scale_factor = []
                self.root_in_scale = False
                self.in_scale = False
        elif factor is not None:
            assert degree is None, f"ScaleChord received clashing factor/degree args"
            assert isinstance(factor, int), f"ScaleChord only understands integer factors, not {type(factor)}"
            self.scale_factor = factor
            self.scale_degree = scale.factor_degrees[factor]



        if self.root_in_scale:
            self.in_scale = scale.contains_degree_chord(degree, self)

    @staticmethod
    def from_numeral(numeral, scale=None):
        from src.progressions import parse_roman_numeral, Progression
        deg, abs_chord = parse_roman_numeral(numeral)
        if scale is None:
            scale = Progression._detect_scale(self=None, degree_chords=[(deg, abs_chord)])
        else:
            if not isinstance(scale, Scale):
                scale = Scale(scale)
        return abs_chord.in_scale(scale, degree=deg)

    @property
    def numeral(self):
        return self.get_numeral()

    @property
    def simple_numeral(self):
        return self.get_numeral(modifiers=False, marks=False, diacritics=False)

    def get_numeral(self, modifiers=True, marks=_settings.DEFAULT_PROGRESSION_MARKERS, diacritics=_settings.DEFAULT_PROGRESSION_DIACRITICS):
        """returns the roman numeral associated with this ScaleChord
        with respect to its Scale and its degree within it"""

        # first: is this a bIII or similar?
        if not self.root_in_scale:
            sharp_degree, flat_degree = ceil(self.scale_degree), floor(self.scale_degree)
            sharp_factor, flat_factor = self.scale.degree_factors[sharp_degree], self.scale.degree_factors[flat_degree]

            if sharp_factor in self.scale.factors and sharp_factor != 1:
                # this can be called a flat degree
                root_prefix, root_factor = fl, sharp_factor
            elif flat_factor in self.scale.factors and flat_factor != 1:
                # the rarer sharp degree
                root_prefix, root_factor = sh, flat_factor
            else:
                # this chord's root is not even adjacent to any scale factor
                # so it gets called a chromatic / out-of-scale chord
                lb, rb = _settings.BRACKETS['non_key_chord_root']
                raise Exception('this should never actually occur')

        else:
            # root in scale, so no prefix needed
            root_prefix, root_factor = '', self.scale_factor

        chord_in_related_scale = False
        rel_mark, diacritic = '', None
        if (not self.in_scale):
            # mark a chord as not in its scale,
            # but indicate if it belongs to other closely related scales:
            if self.scale == NaturalMajor:
                related_scales = [# 'natural minor',
                                  'harmonic major', 'melodic major',
                                  'lydian', 'mixolydian']
                rel_scalename_marks = {scale_name:_settings.SCALE_MARKS[scale_name] for scale_name in related_scales}
                rel_scale_marks = {common_scales_by_name[n]: rel_scalename_marks[n] for n in related_scales}
                             # dominant/subdominant keys?

            elif self.scale == NaturalMinor:
                related_scales = [# 'natural major',
                                  'harmonic minor', 'melodic minor',
                                  'dorian', 'phrygian']
                rel_scalename_marks = {scale_name:_settings.SCALE_MARKS[scale_name] for scale_name in related_scales}
                rel_scale_marks = {common_scales_by_name[n]: rel_scalename_marks[n] for n in related_scales}

            else:
                # just report the parallel scale
                if self.scale.has_parallel():
                    rel_scale_marks = {self.scale.parallel: _settings.SCALE_MARKS['parallel']}
                else:
                    rel_scale_marks = {}

            for rel_scale, mark in rel_scale_marks.items():
                if self in rel_scale:
                    rel_mark = mark
                    chord_in_related_scale = True
                    break

            # set out-of-scale diacritics:
            if (chord_in_related_scale) and (not marks):
                # no need for the diacritic if an out-of-scale mark is shown
                diacritic = _settings.DIACRITICS['chord_in_related_scale']
            else:
                diacritic = _settings.DIACRITICS['chord_not_in_scale']


        # next, decide whether the numeral should be upper or lowercase:
        if self.quality.major_ish:
            uppercase = True
        elif self.quality.minor_ish:
            uppercase = False
        else:
            # chords of ambiguous quality (sus chords etc) use their respective scale triad quality:
            if self.scale.chord(self.scale_degree).quality.minor_ish:
                uppercase = False
            else:
                uppercase = True # falling back on uppercase if even the scale triad is ambiguous:

        if uppercase:
            numeral = parsing.numerals_roman[root_factor].upper()
        else:
            numeral = parsing.numerals_roman[root_factor].lower()

        # get the chord suffix, but ignore any suffix that means 'minor'
        # because minor-ness is already communicated by the numeral's case
        if modifiers:
            chord_suffix = self.suffix
            if '/' in chord_suffix: # remove slash over bass (added back later)
                chord_suffix = chord_suffix.split('/')[0]
            if (len(chord_suffix)) > 0 and (chord_suffix[0] == 'm') and (not self.quality.major_ish):
                chord_suffix = chord_suffix[1:]

            # turn suffix modifiers into superscript marks etc. where possible:
            chord_suffix = ''.join(reduce_aliases(chord_suffix, parsing.modifier_marks))
            # get inversion as integer degree rather than bass note:
            inv_string = '' if self.inversion == 0 else f'/{self.inversion}'
        else:
            chord_suffix, inv_string = '', ''

        # finally, compose full numeral:
        if (diacritics) and (diacritic is not None):
            # underline chord name part of this numeral to illustrate out-of-scale etc.:
            numeral = ''.join([ char + diacritic for char in numeral])

        full_name = root_prefix + numeral + chord_suffix + inv_string
        if marks:
            full_name = rel_mark + full_name
        return full_name

    as_numeral = get_numeral # convenience alias

    @property
    def root_interval_from_tonic(self):
        """returns the interval (relative to scale tonic) that this chord's root sits on"""
        if self.scale_degree in self.scale.degree_intervals:
            return self.scale.degree_intervals[self.scale_degree]
        else:
            return self.scale.fractional_degree_intervals[self.scale_degree]

    def in_key(self, tonic):
        """constructs a KeyChord object from this ScaleChord with respect to a
        desired Key tonic (keeping the same scale degree)"""
        if not isinstance(tonic, notes.Note):
            tonic = notes.Note(tonic)
        root_note = tonic + self.root_interval_from_tonic
        return self.on_root(root_note)

    def on_root(self, root_note):
        """constructs a KeyChord object from this ScaleChord with respect to a
            desired root"""
        from src.keys import Key, KeyChord
        if not isinstance(root_note, notes.Note):
            root_note = notes.Note(root_note)
        tonic_note = root_note - self.root_interval_from_tonic
        key = self.scale.on_tonic(tonic_note)
        return KeyChord(root=root_note, factors=self.factors, inversion=self.inversion,
                        key=key, degree=self.scale_degree, assigned_name=self.assigned_name)

    def on_bass(self, bass_note):
        """constructs an inverted KeyChord object from this inverted ScaleChord with respect to a desired bass"""
        from src.keys import Key, KeyChord
        if self.inversion == 0:
            # bass is root, so on_bass is equivalent to on_root:
            return self.on_root(bass_note)
        else:
            # construct the root note from the desired bass note and this AbstractChord's inversion:
            root_to_bass_interval = self.root_intervals[self.inversion]
            root_note = Note.from_cache(bass_note) - root_to_bass_interval
            interval_from_tonic = self.scale.degree_intervals[self.scale_degree]
            tonic_note = root_note - interval_from_tonic
            key = self.scale.on_tonic(tonic_note)
            return KeyChord(root=root_note, factors=self.factors, inversion=self.inversion, key=key, degree=self.scale_degree)

    @property
    def scale_triad(self):
        """as Chord.simplify(), but always simplifies to the parent scale's respective triad on this degree"""
        return self.scale.chord(self.scale_degree, order=3)

    def __hash__(self):
        """ScaleChords hash depending on their chord hash as well as their scale and degree"""
        return hash((self.factors, self.inversion, self.scale, self.scale_degree))

    def __str__(self):
        return self.name

    @property
    def name(self):
        return f'{super().short_name} chord ({self.simple_numeral})'

    @property
    def short_name(self):
        return f'{super().short_name} {self.simple_numeral}'

    @property
    def compact_name(self):
        ### compact repr for ScaleChord class since it turns up in markov models etc. a lot:
        f'{self._marker}{self.get_numeral(modifiers=True, marks=False, diacritics=False)}'

    def __repr__(self):
        # in_str = 'not ' if not self.in_scale else ''
        return f'{self.name} {self.intervals} ({self.simple_numeral} of: {self.scale._marker}{self.scale.name})'
        # return f'{self._marker}{self.get_numeral(modifiers=True, marks=False, diacritics=False)}'


def parse_roman_numeral(numeral, ignore_alteration=False, return_params=False):
    """given a (string) roman numeral, in upper or lower case,
    with a potential chord modifier at the end,
    parse into a (degree, AbstractChord) tuple, where degree is an int between 1-7.

    if return_params is False, returns the AbstractChord object itself.
        if True, returns the modifiers/inversion parameters used to initialise it.
        (in case we want to avoid double-initialising downstream)"""

    if ignore_alteration and parsing.is_accidental(numeral[0]):
        # if required, disregard accidentals in the start of this degree, like bIII -> III
        numeral = numeral[1:]

    out = reduce_aliases(numeral, parsing.progression_aliases)
    assert isinstance(out[0], tuple) # an integer, quality tuple
    deg, quality_str = out[0]
    quality = Quality.from_cache(name=quality_str)

    modifiers = []
    inversion = 0

    if quality.minor:
        modifiers.append(minor_mod)

    if len(out) > 1: # got one or more additional modifiers as well
        rest = ''.join(out[1:])

        rest_inv = rest.split('/')
        if len(rest_inv) > 1:
            assert len(rest_inv) == 2 # chord part and inversion part
            rest, inversion = rest_inv[0], int(rest_inv[1])

        if len(rest) > 0:
            rest_mods = parse_chord_modifiers(rest, catch_duplicates=True)
            modifiers.extend(rest_mods)

    if not return_params:
        chord = AbstractChord(modifiers=modifiers, inversion=inversion)
        return deg, chord
    else:
        return deg, (modifiers, inversion)


def infer_chord_scale(degree, quality, return_evidence=False):
    """from a single (degree, Quality) pair representing a scale chord's
    root degree and triad quality, determine whether it might be in the natural
        major or minor scale.
    if return_evidence is False, returns the most likely scale.
        if True, returns a (major_evidence, minor_evidence) tuple."""

    major_evidence, minor_evidence = 0, 0
    # just an ugly block of conditionals, wish I could think of a more elegant way:
    if degree == 1 and quality.major_ish:
        major_evidence = 3
    elif degree == 1 and quality.minor_ish:
        minor_evidence = 3
    elif quality.major:
        if degree in {4,5}:
            major_evidence = 1
        elif degree in {2,3,6}:
            minor_evidence = 1
    elif quality.minor:
        if degree in {4,5}:
            minor_evidence = 1
        elif degree in {3,6,7}:
            major_evidence = 1
    elif quality.diminished:
        if degree == 2:
            minor_evidence = 2
        elif degree == 7:
            major_evidence = 2

    if return_evidence:
        return (major_evidence, minor_evidence)
    else:
        return NaturalMajor if major_evidence >= minor_evidence else NaturalMinor


def infer_scale(degree_qualities):
    """from a provided list of chord tuples of form: (root_degree, Quality)
    determine whether they most likely correspond to a major or minor scale by summing evidence
    and returns the resulting scale as an object"""
    # just a loop wrapper around infer_chord_scale
    major_evidence, minor_evidence = 0, 0
    for degree, quality in degree_qualities:
        ev1, ev2 = infer_chord_scale(degree, quality, return_evidence=True)
        major_evidence += ev1
        minor_evidence += ev2
    log(f'For scale chords: {[f"{d}:{q.short_name}" for d,q in degree_qualities]}')
    log(f'  Evidence for major scale: {major_evidence}')
    log(f'  Evidence for minor scale: {minor_evidence}')
    inferred_scale = NaturalMajor if major_evidence >= minor_evidence else NaturalMinor
    log(f'    (inferred: {inferred_scale})\n')
    return inferred_scale



def matching_scales(degree_chord_pairs, major_roots=None):
    """accepts a list of degree-chord pairs, of the form: [(root degree, AbstractChord), etc.]
        and returns a list of matching Scales based on which intervals/factors correspond to those chords
    if major_roots is True, interpret chords like III and VII as being rooted on their major intervals
        (i.e. the major 3rd and major 7th), unless specified bIII and bVII etc.
    if major_roots is False, interpret those chords as rooted on their minor intervals,
        (i.e. the minor 3rd and 7th), unless specified #III and #VII.
    if major_roots is None, we make a best guess - use the tonic's quality if there, or
        assume major if not otherwise specified."""
    degrees = [d for d,ch in degree_chord_pairs]
    abs_chords = [ch for d,ch in degree_chord_pairs]
    if major_roots is None:
        # try and guess from tonic if present:
        if 1 in degrees:
            which_1 = [i for i,d in enumerate(degrees) if d==1][0]
            tonic_chord = abs_chords[which_1]
            major_roots = not tonic_chord.quality.minor_ish # assume major for maj/aug/ind tonic chords
        else:
            major_roots = True # assume major since not otherwise specified

    input_intervals_from_tonic = [MajorScale.get_degree]

    input_intervals_from_tonic = []
    for root_degree, abs_chord in degree_chord_pairs:
        pass # ... TBI


# 'standard' scales are: naturals, harmonic majors/minors, and melodic minor, the most commonly used in pop music
standard_scale_names = {'natural major', 'natural minor', 'harmonic major', 'harmonic minor', 'melodic minor'}
# 'base' scales are those not obtained by rotations of any other scales:
# base_scale_names = {'natural major', 'melodic minor', 'harmonic minor', 'harmonic major', 'neapolitan major', 'neapolitan minor', 'double harmonic'}
# 'natural' scales are just the natural major and minors:
natural_scale_names = {'natural major', 'natural minor'}

# the following dicts map scale factors to the corresponding scale names
# with names as a list, where the first item in the list is taken to be the
# 'canonical' name for that scale, with all others as valid aliases.

base_scale_factor_names = { # base scales are defined here, modes and subscales are added later:

    #### heptatonic scales:
    ScaleFactors('1,  2,  3,  4,  5,  6,  7'): ['natural major', 'major'],
    # ScaleFactors('1,  2, b3,  4,  5, b6, b7'): ['natural minor', 'minor'],
    ScaleFactors('1,  2,  3,  4,  5, b6,  7'): ['harmonic major'],
    ScaleFactors('1,  2, b3,  4,  5, b6,  7'): ['harmonic minor'],
    # ScaleFactors('1,  2,  3,  4,  5, b6, b7'): ['melodic major'],
    ScaleFactors('1,  2, b3,  4,  5,  6,  7'): ['melodic minor', 'jazz minor', 'melodic minor ascending'], # (ascending)
    ScaleFactors('1, b2, b3,  4,  5,  6,  7'): ['neapolitan major', 'phrygian melodic minor'],
    ScaleFactors('1, b2, b3,  4,  5, b6,  7'): ['neapolitan minor', 'phrygian harmonic minor'],
    ScaleFactors('1, b2,  3,  4,  5, b6,  7'): ['double harmonic', 'double harmonic major'],
    ScaleFactors('1, b2,bb3,  4,  5, b6,bb7'): ['miyako-bushi'],

    #### pentatonic scales:
    ScaleFactors('1,  2,  3,  5,  6'): ['major pentatonic', 'pentatonic', 'natural major pentatonic', 'ryo'], # mode 1

    # modes of the hirajoshi / in scale:
    ScaleFactors('1,  2, b3,  5, b6'): ['hirajoshi'], # base scale with 5 modes

    # modes of the dorian pentatonic:
    ScaleFactors('1,  2, b3,  5,  6'): ['dorian pentatonic'], # base scale with modes 2 and 5
    # ScaleFactors('1, b2,  4,  5, b7'): ['kokinjoshi'], # mode 2
    # ScaleFactors('1, b3,  4, b5, b7'): ['minor b5 pentatonic'], # mode 5

    # pentatonics derived from (flattened) 9th chords:
    ScaleFactors('1,  2,  3,  5,  7'): ['blues major pentatonic', 'maj9 pentatonic', 'major 9th pentatonic'],
    ScaleFactors('1,  2,  3,  5, b7'): ['dominant pentatonic', 'dominant 9th pentatonic'],
    ScaleFactors('1,  2, b3,  5, b7'): ['pygmy', 'm9 pentatonic', 'minor 9th pentatonic'],
    ScaleFactors('1,  2, b3,  5,  7'): ['minor-major pentatonic', 'mmaj9 pentatonic'],
    ScaleFactors('1,  2,  3, #5, b7'): ['augmented pentatonic', 'aug9 pentatonic'],
    ScaleFactors('1,  2,  3, #5,  7'): ['augmented major pentatonic', 'augmaj9 pentatonic'],
    ScaleFactors('1,  2, b3, b5,  6'): ['diminished pentatonic', 'dim9 pentatonic'],
    ScaleFactors('1, b2, b3, b5,  6'): ['diminished minor pentatonic', 'dmin9 pentatonic', ],
    ScaleFactors('1,  2, b3, b5,  b7'): ['half-diminished pentatonic', 'hdim9 pentatonic'],
    ScaleFactors('1, b2, b3, b5,  b7'): ['half-diminished minor pentatonic', 'hdmin9 pentatonic'],
    ScaleFactors('1, #2,  3,  5,  b7'): ['hendrix pentatonic'],

    # misc:
    ScaleFactors('1,  2,  4,  5,  7'): ['suspended', 'suspended pentatonic'],
    ScaleFactors('1,  3,  4,  5,  7'): ['okinawan'],
    # ScaleFactors('1, b2, b3,  5, b6'): ['balinese'], # 2nd mode of okinawan scale
    ScaleFactors('1,  2,  3,  5, b6'): ['major b6 pentatonic'],

    #### scales containing chromatic intervals:
    ScaleFactors('1, b3,  4, [b5], 5, b7'): ['minor blues', 'blues', 'minor blues hexatonic'],
    # ScaleFactors('1,  2, [b3], 3,  5,  6'): ['major blues', 'major blues hexatonic'],
    ScaleFactors('1, b2, [b3], 4,  5,  b6, [b7]'): ['sakura'],
    # ScaleFactors('1, 2, 3, 4, 5, 6, [b7],7'): ['bebop dominant'],
    # ScaleFactors('1, 2, 3, 4, 5,[b6], 6, 7'): ['bebop', 'bebop major', 'barry harris', 'major 6th diminished'],
    # ScaleFactors('1, 2,b3, 4, 5,[b6], 6, 7'): ['bebop minor', 'bebop melodic minor', 'minor 6th diminished'],

    # natural-melodic-harmonic hybrids:
    ScaleFactors('1,  2,  b3,  4,  5,  b6, b7,  [7]'): ['chromatic minor (natural/harmonic)'],
    ScaleFactors('1,  2,   3,  4,  5, [b6], 6,   7 '): ['chromatic major (natural/harmonic)'],
    ScaleFactors('1,  2,   3,  4,  5,  b6, [6], b7 '): ['chromatic minor (natural/melodic)'],
    ScaleFactors('1,  2,   3,  4,  5,   6, [b7], 7 '): ['chromatic major (natural/melodic)'],

    ScaleFactors('1,  2,   3,  4,  5,[b6],  6,[b7],  7'): ['chromatic major'],
    ScaleFactors('1,  2,  b3,  4,  5,  b6, [6], b7, [7]'): ['chromatic minor'],

    # chromatic scale from major: (currently do not work with mode rotation)
    # ScaleFactors('1, [b2], 2,  [b3], 3, 4, [b5], 5, [b6], 6, [b7], 7'): ['chromatic major'],
    # ScaleFactors('1, [b2], 2,  b3, [3], 4, [b5], 5, b6, [6], b7, [7]'): ['chromatic minor'],

    #### rare hexatonic and octatonic scales:
    # hexatonic scales:
    ScaleFactors('1,  2,  3, #4, #5, #6'): ['whole tone', 'whole-tone'],
    ScaleFactors('1,  2,  3, b5,  6, b7'): ['prometheus'],
    ScaleFactors('1, b2, b3, #4,  5, b7'): ['tritone'],

    # octatonic scales: (these get parsed with IrregularInterval members)
    ScaleFactors('1,  2, b3,  4, b5, b6,  6,  7'): ['diminished', 'whole-half', 'wholehalf', 'whole half'],
    ScaleFactors('1, b2, b3, b4, b5,  5,  6, b7'): ['half-whole', 'halfwhole', 'half whole'],
    ScaleFactors('1,  2,  3,  4,  5,  6, b7, 7'): ['bebop dominant', 'bebop dominant octatonic'],
    ScaleFactors('1,  2,  3,  4,  5, #5,  6, 7'): ['bebop', 'bebop major', 'barry harris', 'major 6th diminished', 'bebop major octatonic', 'bebop octatonic', ],
    ScaleFactors('1,  2, b3,  4,  5, #5,  6, 7'): ['bebop minor', 'bebop melodic minor', 'bebop minor octatonic', 'minor 6th diminished'],
}

base_scale_name_factors = unpack_and_reverse_dict(base_scale_factor_names)
base_scale_names = set(base_scale_name_factors.keys())

# while it's true that "melodic minor" can refer to a special scale that uses
# the natural minor scale when descending, that is out-of-scope for now

#     }
# heptatonic_scale_name_factors = unpack_and_reverse_dict(heptatonic_scale_factor_names)

# this dict maps base scale names to dicts that map scale degrees to the modes of that base scale
base_scale_mode_names = {
                    # the diatonic base scale and its modes:
   'natural major': {1: ['ionian', 'bilawal'],
                     2: ['dorian', 'kafi'],
                     3: ['phrygian', 'bhairavi'],
                     4: ['lydian', 'kalyan'],
                     5: ['mixolydian', 'khamaj'],
                     6: ['natural minor', 'minor', 'aeolian', 'asavari',],
                     7: ['locrian']},

                     # non-diatonic heptatonic base scales and their modes:
   'melodic minor': {1: ['athenian'],
                     2: ['cappadocian', 'phrygian ♯6', 'dorian ♭2'],
                     3: ['asgardian', 'lydian augmented'],
                     4: ['acoustic', 'pontikonisian', 'lydian dominant', 'overtone'],
                     5: ['melodic major', 'olympian', 'aeolian dominant', 'mixolydian ♭6'],
                     6: ['sisyphean', 'aeolocrian', 'half-diminished'],
                     7: ['palamidian', 'altered dominant']},
  'harmonic minor': {1: [],
                     2: ['locrian ♯6'],
                     3: ['ionian ♯5'],
                     4: ['ukrainian dorian', 'ukrainian minor'],
                     5: ['phrygian dominant', 'spanish gypsy', 'egyptian'],
                     6: ['lydian ♯2', 'maqam mustar'],
                     7: ['altered diminished']},
  'harmonic major': {1: [],
                     2: ['blues heptatonic', 'dorian ♭5', 'locrian ♯2♯6'],
                     3: ['phrygian ♭4', 'altered dominant ♯5'],
                     4: ['lydian minor', 'lydian ♭3', 'melodic minor ♯4'],
                     5: ['mixolydian ♭2'],
                     6: ['lydian augmented ♯2'],
                     7: ['locrian 𝄫7']},
'neapolitan minor': {1: [],
                     2: ['lydian ♯6'],
                     3: ['mixolydian augmented'],
                     4: ['romani minor', 'aeolian ♯4'],
                     5: ['locrian dominant'],
                     6: ['ionian ♯2'],
                     7: ['ultralocrian', 'altered diminished 𝄫3']},
'neapolitan major': {1: [],
                     2: ['lydian augmented ♯6'],
                     3: ['lydian augmented dominant'],
                     4: ['lydian dominant ♭6'],
                     5: ['major locrian'],
                     6: ['half-diminished ♭4', 'altered dominant #2'],
                     7: ['altered dominant 𝄫3']},
'double harmonic':  {1: ['byzantine', 'arabic', 'gypsy major', 'flamenco', 'major phrygian', 'bhairav'],
                     2: ['lydian ♯2 ♯6'],
                     3: ['ultraphrygian'],
                     4: ['hungarian minor', 'gypsy minor', 'egyptian minor', 'double harmonic minor'],
                     5: ['oriental'],
                     6: ['ionian ♯2 ♯5'],
                     7: ['locrian 𝄫3 𝄫7']},

                     # pentatonic base scales and their modes:
'major pentatonic': {1: ['pentatonic', 'natural major pentatonic', 'ryo'],
                     2: ['egyptian pentatonic'],
                     3: ['blues minor pentatonic', 'phrygian pentatonic', 'minyo', 'man gong'],
                     4: ['yo', 'ritsu', 'ritusen', 'major pentatonic II'],
                     5: ['minor pentatonic', 'natural minor pentatonic']},
       'hirajoshi': {
                     2: ['iwato', 'sachs hirajoshi'],
                     3: ['kumoi', 'kumoijoshi'],
                     4: ['hon kumoi', 'hon kumoijoshi', 'sakura pentatonic', 'in', 'in sen'],
                     5: ['amritavarshini', 'chinese', 'burrows hirajoshi']},

                     # incidental/partial mode names:
         'okinawan': {2: ['balinese']},
'dorian pentatonic': {2: ['kokinjoshi'], 5: ['minor ♭5 pentatonic']},
      'minor blues': {2: ['major blues']},
  # 'chromatic major': {11: ['chromatic minor']},
                 }

# base_scale_names = list(base_scale_mode_names.keys())
# #
# base_scale_factor_names = {
    # natural pentatonics and their modes:
#     }
# pentatonic_scale_name_factors = unpack_and_reverse_dict(pentatonic_scale_factor_names)
#
# chromatic_scale_factor_names = {
    # note: while 'pentatonic' on its own redirects to major pentatonic,
    # 'blues' on its own redirects to minor blues, by convention
#     }
# chromatic_scale_name_factors = unpack_and_reverse_dict(chromatic_scale_factor_names)
#
# # unusual scales with that ought not to be searched:
# rare_scale_factor_names = {}

# rare_scale_name_factors = unpack_and_reverse_dict(rare_scale_factor_names)

base_mode_factor_names = {}
# loop across base scale modes to build more factor mappings:
for base_name, mode_dict in base_scale_mode_names.items():
    # retrieve the factors of a base scale:
    base_factors = base_scale_name_factors[base_name]
    # loop across this scale's theoretical modes:
    for mode_num, name_list in mode_dict.items():
        if len(name_list) > 0:
            mode_factors = base_factors.mode(mode_num)
            base_mode_factor_names[mode_factors] = name_list

registered_scale_name_dicts = [base_scale_factor_names, base_mode_factor_names]

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
for fac,name in canonical_scale_factor_names.items():
    fiv = fac.to_intervals(chromatic=False)
    civ = fac.chromatic.to_intervals() if fac.chromatic is not None else None
    if (fiv,civ) not in canonical_scale_interval_names:
        canonical_scale_interval_names[(fiv,civ)] = name
    else:
        print(f'Clash between scale {name} with intervals {(fiv,civ)}, already registered to: {canonical_scale_interval_names[(fiv,civ)]}')

# canonical_scale_interval_names = {f.as_intervals:n for f,n in
canonical_scale_name_factors = reverse_dict(canonical_scale_factor_names)
canonical_scale_name_intervals = reverse_dict(canonical_scale_interval_names)
canonical_scale_alias_names = unpack_and_reverse_dict(canonical_scale_name_aliases, include_keys=True)

# mapping of possible scale lengths to lists of scale names which have that length:
canonical_scale_names_by_length = {}
base_scale_names_by_length = {}
for l in range(5,13):
    canonical_scale_names_by_length[l] = [scale_name for scale_name, factors in canonical_scale_name_factors.items() if len(factors) == l]
    base_scale_names_by_length[l] = [scale_name for scale_name, factors in canonical_scale_name_factors.items() if len(factors) == l and scale_name in base_scale_mode_names]

wordbag_scale_names = {frozenset(name.split(' ')):name for name in canonical_scale_name_factors.keys()}

def is_valid_scale_name(name):
    """returns True if name is the canonical name of a scale, an alias of a scale,
    or reduces to a scale's wordbag"""
    if name in all_scale_name_factors:
        return True
    else:
        # replace aliases with canonical names and freeze wordbag:
        reduced_name_words = reduce_aliases(name, replacement_scale_names, chunk=True)

        # join and split on whitespace in case no replacements were made but an alteration exists:
        reduced_name_words = ' '.join(reduced_name_words).split(' ')

        # check for alterations:
        alterations = [word for word in reduced_name_words if is_alteration(word)]
        if len(alterations) > 0:
            # if there are any alterations, then the name becomes
            # all the words that AREN'T alterations:
            reduced_name_words = [word for word in reduced_name_words if not is_alteration(word)]

        wordbag = frozenset(reduced_name_words)
        if wordbag in wordbag_scale_names:
            return True
        else:
            return False


# string replacements for scale searching:
scale_name_replacements = {
                        'major': ['maj', 'M', 'Δ', ],
                        'minor': ['min', 'm'],
                        'natural': ['nat'],
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
                        'neapolitan': ['naples', 'neapo'],
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

# rex_patterns = []
# for target, substrings in scale_name_replacements.items():
#     for substring in substrings:
#         remainder = [char for char in target if char not in substring]
#         remainder = ''.join(remainder)
#         pattern = f'(?P<{target}>{substring}({remainder})?)'
#         rex_patterns.append(pattern)

# build alias mappings and master mapping of all possible scale names to their factors
all_scale_name_factors = {k:v for k,v in canonical_scale_name_factors.items()}
for alias, canonical_name in canonical_scale_alias_names.items():
    if alias not in all_scale_name_factors:
        alias_factors = canonical_scale_name_factors[canonical_name]
        all_scale_name_factors[alias] = alias_factors

# base scale lists:
heptatonic_base_scale_names = [n for n in base_scale_mode_names if len(all_scale_name_factors[n]) == 7]
hexatonic_base_scale_names = [n for n in base_scale_mode_names if len(all_scale_name_factors[n]) == 6]
pentatonic_base_scale_names = [n for n in base_scale_mode_names if len(all_scale_name_factors[n]) == 5]

# define rarities for heptatonic scales:
heptatonic_scale_names_by_rarity = {
1: {'natural major', 'natural minor'}, #, },
2: {'harmonic major', 'harmonic minor', 'melodic minor'}, # , 'minor blues', 'major blues'},
3: {'melodic major', 'dorian', 'phrygian', 'lydian', 'mixolydian', 'locrian'},
4: {'neapolitan major', 'neapolitan minor', 'double harmonic', 'miyako-bushi'}}

# define rarities for non-heptatonics:
canonical_scale_names_by_rarity = dict(heptatonic_scale_names_by_rarity)
canonical_scale_names_by_rarity[1].update(['major pentatonic', 'minor pentatonic'])
canonical_scale_names_by_rarity[2].update(['minor blues', 'major blues'])
canonical_scale_names_by_rarity[4].update(['hirajoshi', 'iwato', 'kumoi', 'yo'])

common_scale_names = set()
for r, names in canonical_scale_names_by_rarity.items():
        common_scale_names.update(names)

# all remaining scales:
canonical_scale_names_by_rarity[5] = {n for n in canonical_scale_name_factors if n not in common_scale_names and not contains_accidental(n)}
canonical_scale_names_by_rarity[6] = {n for n in canonical_scale_name_factors if contains_accidental(n)}


# initialise empty caches:
cached_consonances = {}
cached_pentatonics = {}

# pre-initialised scales for efficient import by other modules instead of re-init:
NaturalMajor = MajorScale = Ionian = IonianScale = Scale('major')
Dorian = DorianScale = Scale('dorian')
Phrygian = PhrygianScale = Scale('phrygian')
Lydian = LydianScale = Scale('lydian')
Mixolydian = MixolydianScale = Scale('mixolydian')
NaturalMinor = MinorScale = Aeolian = AeolianScale = Scale('minor')
Locrian = LocrianScale = Scale('locrian')

HarmonicMinor = HarmonicMinorScale = Scale('harmonic minor')
HarmonicMajor = HarmonicMajorScale = Scale('harmonic major')
MelodicMinor = MelodicMinorScale = Scale('melodic minor')
MelodicMajor = MelodicMajorScale = Scale('melodic major')

MajorPentatonic = MajorPentatonicScale = MajorPent = MajPent = Scale('major pentatonic')
MinorPentatonic = MinorPentatonicScale = MinorPent = MinPent = Scale('minor pentatonic')
MajorBlues = MajorBluesScale = MajBlues = Scale('major blues')
MinorBlues = MinorBluesScale = MinBlues = Scale('minor blues')

# dict mapping parallel major/minor scales:
# (hardcoded since these are mostly established by convention,
# as all modes are technically parallel)
parallel_scale_names = {'natural major': 'natural minor',
                        'melodic major': 'melodic minor',
                        # natural pentatonics and blues scales are straightforward:
                        'major pentatonic': 'minor pentatonic',
                        'minor blues': 'major blues',
                        # and some other scales have only one named mode, which
                        # is a natural parallel:
                        'okinawan': 'balinese',
                        'dorian pentatonic': 'kokinjoshi',
                        }
# and for other base scales, just pick the most consonant (named) mode:
common_base_scale_names = base_scale_names.intersection(common_scale_names)

# this list is important: it's the scales that get searched for matching_keys
common_base_scales = [Scale(n) for n in common_base_scale_names]

common_modes = [Scale(n) for n in common_scale_names if n not in common_base_scale_names]
common_scales = list(common_base_scales) + list(common_modes)
common_scales_by_name = {scale.name : scale for scale in common_scales} # for fast access

for name, scale in zip(common_base_scale_names, common_base_scales):
    if name not in parallel_scale_names.keys():
        named_modes = [m for m in scale.modes if m.factors in canonical_scale_factor_names]
        modes_by_consonance = sorted(named_modes, key=lambda x: -x.consonance)
        if len(modes_by_consonance) > 0:
            most_consonant_mode = modes_by_consonance[0]
            parallel_scale_names[name] = most_consonant_mode.name

# instantiate objects:
parallel_scales = {Scale(p1): Scale(p2) for p1, p2 in parallel_scale_names.items()}
# parallel scales are symmetric, so include the reverse mappings as well:
parallel_scale_names.update(reverse_dict(parallel_scale_names))
parallel_scales.update(reverse_dict(parallel_scales))

# cached scale attributes for performance:
if _settings.PRE_CACHE_SCALES:
    cached_consonances.update({c: c.consonance for c in common_base_scales})
    cached_pentatonics.update({c: c.pentatonic for c in common_base_scales})
