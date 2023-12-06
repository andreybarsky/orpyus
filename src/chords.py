from .notes import Note, NoteList
from .intervals import Interval, IntervalList, P5, default_degree_intervals
from .util import log, precision_recall, rotate_list, check_all, all_equal, sign, reverse_dict, unpack_and_reverse_dict, reduce_aliases
from .qualities import Quality, ChordModifier, parse_chord_modifiers
from .parsing import sh, fl, nat
from . import notes, parsing, qualities, tuning,
from .config import settings, def_chords
#from .config.def_chords import chord_names_by_rarity

from collections import defaultdict, UserDict, Counter
import itertools

################################################################################


class AbstractChord:
    """a hypothetical chord not built on any specific note but having all the modifiers that a chord would,
    whose principal members are Intervals. see AbstractChord._parse_input for valid input schemas.
    an AbstractChord is fully identified by its Factors and its Inversion."""
    def __init__(self, name=None, factors=None, intervals=None, inversion=None, inversion_degree=None, modifiers=None, auto_invert=True, assigned_name=None):
        """primary input arg must be one of the following mutually exclusive keywords, in order of resolution:
        1. 'name' arg as string denoting the name of an AbstractChord (like 'mmaj7'),
                which we look up and parse as a list of ChordModifiers.
                  --this name can also contain an inversion (like 'mmaj7/2'), which
                    we interpret as an 'inversion' arg (and therefore ignore an
                    inversion kwarg if one has been supplied)
        2. (re-casting): 'name' arg of type AbstractChord, or a subclass of AbstractChord, from which
                we read the factors/intervals/inversion directly.
        3. 'factors' arg of type dict or ChordFactors, keying degree to semitone offsets,
                which we accept directly and build into intervals.
        4. 'intervals' arg as list of Intervals, or ints that cast to Intervals, which we
                interpret as distances from the desired chord's root
                (using each Interval.degree attribute to build ChordFactors from)

        and special case:
        5. 'modifiers' arg as string or list of ChordModifier objects, (or objects that cast
                to ChordModifiers), which we successively apply to the major triad.
                    this can be given as sole init argument, but is also valid to provide in combination
                    with any of the other keyword args, in which case we apply the modifiers
                    not to the major triad, but whatever other chord got parsed out by the keyword arg.

        lastly, an optional arg: one of 'inversion' or 'inversion_degree':
            'inversion' as int, denoting that this chord is an "Xth inversion", meaning that
                the bass note is the Xth note in the chord, with notes ordered ascending.
                (e.g. Cmaj7, inversion=3 implies 3rd inversion, with bass on B)
        or
            'inversion_degree' as int, denoting the degree that the chord's bass note is on.
                (e.g. Cmaj7, inversion_degree=3 implies bass is on the 3rd of the chord, i.e. E)
        note that both are ignored if the 'name' arg contains a slash."""

        # if self.__class__.__name__ == 'AbstractChord':
        #     global ABS_CHORDS_INITIALISED
        #     ABS_CHORDS_INITIALISED += 1
        #     cache_size = len(cached_abstract_chords)
        #     log(f'Initialising {self.__class__.__name__} #{ABS_CHORDS_INITIALISED} (cache size: {cache_size})', True, depth=3)

        if type(name) == str:
            self.assigned_name = name # record the name this chord was initialised by
        else:
            self.assigned_name = None

        self.factors, self.root_intervals, self.inversion = self._parse_input(name, factors, intervals, inversion, inversion_degree, modifiers)

        # dict mapping chord factors to intervals-from-tonic (and vice versa):
        self.factor_intervals = {i.extended_degree: i for i in self.root_intervals}
        self.interval_factors = reverse_dict(self.factor_intervals)

        if self.inversion != 0: # list of self.intervals is with respect to this chord's inversion
            self.intervals = self.root_intervals.invert(self.inversion)
        else:
            self.intervals = self.root_intervals

        self.quality = self._determine_quality()




    # main logic for understanding input args:
    def _parse_input(self, name, factors, intervals, inversion, inversion_degree, modifiers, _allow_note_name=False, min_inversion_rarity=3, max_uninverted_rarity=5, _debug=False):
        """takes valid inputs to AbstractChord and parses them into factors, intervals and inversion.
        (see docstring for AbstractChord.__init__)"""

        if isinstance(name, list):
            # we've been fed a list, probably of integers or intervals:
            if (type(name) == IntervalList) or (type(name) == list and isinstance(name[0], (int, Interval))): # check_all(name, 'isinstance', (int, Interval))):
                # we've been fed an IntervalList as first (name) arg, which we quietly re-cast:
                assert intervals is None
                intervals = name
                name = None
            else:
                raise ValueError(f'AbstractChord expected a string but was initialised with a list as first arg, and it does not seem to be a valid IntervalList: {name}')

        if name is None and factors is None and intervals is None:
            # we have been given nothing to init by, so initialise a basic major triad:
            factors = ChordFactors()


        if name is not None:
            assert factors is None and intervals is None
            # check for inversion by slashes: (or sometimes backslashes)
            if '/' in name or '\\' in name:
                assert inversion is None and inversion_degree is None, 'Parsed slash chord as denoting inversion, but received mutually exclusive inversion arg'
                # parse inversion from name
                name = name.replace('\\', '/')
                name, inversion_str = name.split('/')

                # if the string after the slash is a digit, or a negative digit,
                # treat it as an integer place inversion
                if inversion_str.isnumeric() or inversion_str[0] == '-' and inversion_str[1:].isnumeric():
                    inversion = int(inversion_str)
                else:
                    assert _allow_note_name, f'String inversions only allowed for non-AbstractChords'
                    inversion = inversion_str

            # detect if name refers to a major chord:
            if name == '' or name in ((qualities.modifier_aliases['maj']) + ['maj']):
                factors = ChordFactors() # major triad by default
            else:
                modifiers_from_name = parse_chord_modifiers(name)
                factors = ChordFactors() + modifiers_from_name
        elif factors is not None:
            assert name is None and intervals is None
            # do nothing! factors are already defined, just pass to next block
        elif intervals is not None:
            assert name is None and factors is None
            # sanitise interval list input, expect root to be provided:
            if not isinstance(intervals, IntervalList):
                intervals = IntervalList(intervals)
            if intervals[0] != 0:
                # pad with root if needed
                intervals = intervals.pad(left=True, right=False)

            # # cast to IntervalList object, pad to canonical chord intervals form with left bass root but not upper octave root
            assert len(intervals) == len(set(intervals)), f'Interval list supplied to AbstractChord init contains repeated intervals: {intervals}'

            # check if this is an inversion of some common chord:
            if intervals in intervals_to_chord_names:
                # (we'll use the inversion only if it's significantly less rare than the root intervals)
                supplied_interval_chord_name = intervals_to_chord_names[intervals]
                supplied_rarity = chord_name_rarities[supplied_interval_chord_name]
                supplied_factors = chord_names_to_factors[supplied_interval_chord_name]
                has_uninverted_name = True
            else:
                has_uninverted_name = False
                supplied_rarity = 10 # max possible

            # search for possible inversions if this is not already one,
            # and adopt the most common, if it's more common than what we've been given:
            if inversion is None and inversion_degree is None:
                possible_inversions = AbstractChord.inversions_from_intervals(intervals)
                if len(possible_inversions) > 0:
                    # take least rare inversion:
                    sorted_inversions = sorted(possible_inversions, key=lambda x: x.rarity)
                    best_inversion = sorted_inversions[0]
                    # adopt the inversion if it is less rare than our existing name and at least as common as our max_inversion_rarity threshold,
                    # OR if we have no other registered chord to fall back on
                    if (not has_uninverted_name) or (best_inversion.rarity < supplied_rarity and best_inversion.rarity <= max_uninverted_rarity and supplied_rarity > min_inversion_rarity):
                        # adopt the inverted chord's root intervals and inversion instead
                        old_intervals = intervals
                        new_intervals = best_inversion.root_intervals
                        intervals = new_intervals
                        assert best_inversion.inversion not in [0, None]
                        inversion = best_inversion.inversion
                        # and one last change (bit of a kludge): if this is a Chord, intercept and change the root:
                        if isinstance(self, Chord):
                            inversion_of_inversion = len(intervals) - inversion
                            self.root += old_intervals[inversion_of_inversion]
                    else:
                        # found an inversion but it was too rare to consider and we have another name to use instead
                        inversion = 0
                else:
                    # we've failed to find an inversion, so just use the intervals as they are
                    inversion = 0

            # if a chord with these intervals already has registered factors, use those:
            if intervals in intervals_to_chord_names:
                chord_name = intervals_to_chord_names[intervals]
                log(f'Caught chord intervals (but not factors)')

                factors = chord_names_to_factors[chord_name]
                intervals = factors.as_intervals
            elif 5 not in [iv.degree for iv in intervals]:
                # check if this is a registered no5 chord, and use those factors if they exist:
                intervals_with_5 = (intervals + IntervalList([P5])).sorted()
                if intervals_with_5 in intervals_to_chord_names:
                    full_chord_name = intervals_to_chord_names[intervals_with_5]
                    log(f'Caught no5 chord intervals (but not factors)')
                    factors_without_5 = dict(chord_names_to_factors[full_chord_name])
                    del factors_without_5[5]
                    factors = ChordFactors(factors_without_5)


            if factors is None:
                # build factors by looping through intervals:
                factors = ChordFactors({1:0}) # note: NOT a major triad
                mod_factors_used = set()
                for i in intervals: # parse interval degree and quality into factors dict
                    # if i.mod != 0: # catch special case: do not record perfect octaves
                    # count the mod intervals we've already used, so we ignore adding them if they come up again:
                    # (this ensures that e.g. 'CEGCGEC' is parsed as 'CEG')
                    if i.mod not in mod_factors_used:
                        factors[i.extended_degree] = i.offset_from_default
                        mod_factors_used.add(i.mod)

        if modifiers is not None:
            if factors is None:
                # if no factors yet, start modifying a major triad by default
                factors = ChordFactors()

            if isinstance(modifiers, str):
                # parse string of modifiers as an iterable of them
                modifiers = parse_chord_modifiers(modifiers)
            # make sure we're dealing with an iterable of them:
            check_all(modifiers, 'isinstance', ChordModifier)
            # apply them to our factors:
            factors = factors + modifiers

        if intervals is None: # i.e. if we have defined factors from name or factor kwarg
            # in this case we trust them and do not insist that this is an inversion
            # i.e. we keep 6(no5) instead of casting to m/2
            intervals = []
            for deg, offset in factors.items():
                # note that interval list always includes Unison as root
                intervals.append(Interval.from_degree(deg, offset=offset))
            intervals = IntervalList(intervals)

        if inversion_degree is not None:
            # which Xth inversion is this, from the inversion degree:
            for x, deg in enumerate(sorted(factors.keys())):
                if inversion_degree == deg:
                    inversion = x
                    break

        if (inversion is not None) and (inversion != 0):

            if isinstance(inversion, int):
                # mod inversion so that it can wrap around to the start,
                # or allow for negative inversions (i.e. -1 meaning final inversion)
                inversion = inversion % len(intervals)
            elif isinstance(inversion, str):
                if not _allow_note_name:
                    raise TypeError(f'inversion arg for AbstractChord must be an int, but got: {type(inversion)}')
                else:
                    if not parsing.is_valid_note_name(inversion):
                        raise ValueError(f'got string argument to inversion, but does not seem to be a valid note name: {inversion}')
            else:
                raise TypeError(f'inversion must be an int or str, but got: {type(inversion)}')
        else:
            inversion = 0 # 0th inversion means no inversion at all

        return factors, intervals.sorted(), inversion

    def _determine_quality(self):
        """determines a chord's Quality from its factors attribute.
        if the fifth is perfect, this will be the quality of the third (major/minor),
        but if the fifth is raised or lowered, it will be augmented or diminished respectively."""
        # quality of a chord is primarily the quality of its third:
        if 3 in self.factors:
            if self.factors[3] == 0: # major 3rd
                # is augmented if the 5th is augmented, otherwise is major
                if 5 in self.factors and self.factors[5] == 1: # aug 5th
                    return qualities.Augmented
                else:
                    return qualities.Major
            elif self.factors[3] == -1: # minor 3rd
                if 5 in self.factors and self.factors[5] == -1: # dim 5th
                    return qualities.Diminished
                else:
                    return qualities.Minor
            else:
                # third is present but neither major or minor, meaning it is dim or aug (or ddim or aaug)
                # so we'll just call this chord whatever the third is:
                return Quality.from_offset_wrt_major(self.factors[3])
        else:
            # if no 3rd; try using the 5th instead
            # (this is usually perfect, but could be a dim5(no3) or something
            if 5 in self.factors:
                return Quality.from_offset_wrt_perfect(self.factors[5])
            else:
                # no 5th OR 3rd; this means it's something horrible like a sus4(no5)
                # so just return ind
                return qualities.Perfect

    def __len__(self):
        return len(self.factors)

    @property
    def _inv_string(self):
        """inversion string, used internally by suffix method (and inherited by subclasses)"""
        return f'/{self.inversion}' if (self.inversion != 0) else ''

    @property
    def suffix(self):
        return self.get_suffix(inversion=True)

    def get_suffix(self, inversion=True):
        """dynamically determine chord suffix from factors and inversion"""
        if self._is_registered():
            return self._get_registered_name(inversion=inversion)
        else:
            inv_string = self._inv_string if inversion else ''

            if 5 not in self.factors:
                # try adding a 5 to see if this is a (no5) chord
                factors_with_5 = dict(self.factors)
                factors_with_5[5] = 0
                factors_with_5 = ChordFactors(factors_with_5)
                if factors_with_5 in factors_to_chord_names:
                    return factors_to_chord_names[factors_with_5] + '(no5)' + inv_string

            # try flattening intervals and seeing if that produces a chord: (i.e. parsing CGE as CEG)
            flat_intervals = self.intervals.flatten()
            if flat_intervals in intervals_to_chord_names:
                # affix with extended chord identifying char:
                ext_char = settings.CHARACTERS['extended_chord']
                return intervals_to_chord_names[flat_intervals] + ext_char
            elif self.factors == _major_triad:
                return ''
            elif self.assigned_name is not None:
                log(f'Falling back on assigned name for unregistered chord: {self.assigned_name}')
                ### experimental: register this chord under this name too
                if settings.DYNAMIC_CACHING and cache_initialised:
                    log(f'Post-hoc registering chord inside AbstractChord.get_suffix')
                    self._register()
                return self.assigned_name
            else:
                unknown_marker = self._unknown_char
                return f'{unknown_marker}{inv_string}'

    def _is_registered(self):
        """returns True if this chord is registered under a name-factor mapping,
        and False otherwise"""
        if self.factors in factors_to_chord_names:
            return True
        elif self.root_intervals in intervals_to_chord_names:
            return True
        else:
            return False

    def _get_registered_name(self, inversion=True):
        """returns the name this chord is registered under by its factors/intervals"""
        inv_string = self._inv_string if inversion else ''
        if self.factors in factors_to_chord_names:
            return factors_to_chord_names[self.factors] + inv_string
        elif self.root_intervals in intervals_to_chord_names:
            return intervals_to_chord_names[self.intervals] + inv_string

    def _register(self):
        """adds this chord to the register of named chords and associated lookups,
        by whatever name it was initialised by"""
        intervals_to_chord_names[self.intervals] = self.assigned_name
        factors_to_chord_names[self.factors] = self.assigned_name
        chord_names_to_factors[self.assigned_name] = self.factors
        chord_names_to_intervals[self.assigned_name] = self.intervals
        chord_names_by_rarity[self.rarity].append(self.assigned_name)
        chord_name_rarities[self.assigned_name] = self.rarity

    @property
    def rarity(self):
        """an integer denoting how rarely this chord is used in practice"""
        if self.factors in factors_to_chord_names:
            registered_name = factors_to_chord_names[self.factors]
            if registered_name in chord_name_rarities:
                return chord_name_rarities[registered_name]
            else:
                # strange case
                log(f'Chord {self.name} with factors {self.factors} has registered factors but no rarity')
                return max_rarity
        else:
            # no5 chords have no registered rarity; so here we check the rarity of this chord
            # WITH a perfect 5th, and make it one step rarer than that
            if 5 not in self.factors:
                intervals_with_5 = IntervalList(list(self.intervals) + [P5])
                intervals_with_5.sort()
                if intervals_with_5 in intervals_to_chord_names:
                    rarity_with_5 = chord_name_rarities[intervals_to_chord_names[intervals_with_5]]
                    return rarity_with_5 + 1
            return max_rarity

    def get_likelihood(self):
        """converse of rarity, likelihood score as a float between 0-1"""
        l_score = (10-self.rarity)/10
        # with a penalty for inversions:
        if self.inversion != 0:
            l_score -= 0.05
        return l_score
    @property
    def likelihood(self):
        return self.get_likelihood()

    def identify_inversion(self):
        """searches all of this chord's possible inversions to see if one of them
        matches an existing chord, and returns that chord's inversion as a new object"""
        return self.inversions_from_intervals(self.intervals)

    def get_pairwise_intervals(self):
        pairwise = {}
        for i in range(len(self.intervals)):
            for j in range(i+1, len(self.intervals)):
                pairwise[(self.intervals[i], self.intervals[j])] = self.intervals[j] - self.intervals[i]
        return pairwise
    @property
    def pairwise_intervals(self):
        return self.get_pairwise_intervals()

    def get_pairwise_consonances(self, extra_factors=None, temperament=None):
        """returns a dict that keys (interval, interval) pairs to the consonances of the
            relative intervals between those two.
        optionally, extra_factors can be a list of integers, indicating the chord factors
            to upweight, by making them appear again in the output dict."""
        pw_intervals = self.get_pairwise_intervals()
        pw_consonances = {}
        if extra_factors is not None:
            extra_intervals = [self.factor_intervals[f]  for f in extra_factors  if f in self.factors]
        for pair, diff in pw_intervals.items():
            left, right = pair
            this_consonance = round(diff.get_consonance(temperament=temperament),4)
            pw_consonances[(left, right, 0)] = this_consonance
            # if extra factors are required: add them here:
            if extra_factors is not None:
                for j, iv in enumerate(extra_intervals):
                    if left == iv or right == iv:
                        # double this one and add another version of it to the consonances dict
                        pw_consonances[(left, right, j+1)] = this_consonance
        return pw_consonances
    @property
    def pairwise_consonances(self):
        return self.get_pairwise_consonances()

    @property
    def consonance(self):
        return self.get_consonance()
    def get_consonance(self, temperament=None, raw=False,
                       extra_factors=[1,1,1,3,4,5,5]): # emphasise tonic, fourth and fifth (as stable degrees)
                                                       # as well as the third (to cover the tonic triad)
        """the weighted mean of pairwise interval consonances"""
        # just retrieve cached consonance if it has already been computed:
        if temperament is None:
            temperament = tuning.get_temperament('CONSONANCE')

        if self._is_registered() and (temperament, self.suffix) in cached_consonances_by_suffix:
            raw_cons = cached_consonances_by_suffix[(temperament, self.suffix)]
        else:
            pairwise_cons = self.get_pairwise_consonances(extra_factors=extra_factors, temperament=temperament)
            cons_list = list(pairwise_cons.values())
            # cons_list = []
            # for pair, cons in self.get_pairwise_consonances(extra_factors=extra_factors, temperament=temperament).items():
            #     if (tonic_weight != 1) and (pair[0].value == 0): # intervals from root are counted double
            #         cons_list.extend([cons]*tonic_weight)
            #     else:
            #         cons_list.append(cons)
            # simple average of consonance list: (weighting incorporated by the extra_factors mechanic)
            raw_cons = sum(cons_list) / len(cons_list)
            if settings.DYNAMIC_CACHING:
                cached_consonances_by_suffix[(temperament,self.suffix)] = raw_cons

        if raw:
            return round(raw_cons, 3)
        else:
            # the raw consonance comes out as maximum=0.933 (i.e. 14/15) for the most consonant chord (the octave)
            # by definition because of the constant 15 in the interval dissonance calculation, where
            # perfect consonance (unison) has dissonance 0 and the octave has dissonance 1.

            # chords cannot be on unison, so we'll set the ceiling to 1 instead of 0.9333.

            # and the empirically observed minimum is 0.459 for the dimsus4
            # so we set that to be just around 0, and rescale the entire raw consonance range within those bounds:
            max_cons = 14/15
            min_cons = 0.45
            rescaled_cons = (raw_cons - min_cons) / (max_cons - min_cons)
            return round(rescaled_cons, 3)

    @staticmethod
    def inversions_from_intervals(intervals):
        """searches an interval list's inversions for possible matching chords
        and returns as a dict keying candidate inverted AbstractChords to their rarities"""
        candidates = []
        for inversion_place in range(1, len(intervals)):
            inverted_intervals = intervals.invert(-inversion_place)
            if inverted_intervals in intervals_to_chord_names:
                that_chord_name = intervals_to_chord_names[inverted_intervals]
                candidates.append(AbstractChord.from_cache(that_chord_name, inversion=inversion_place))
        candidates.sort(key = lambda x: x.rarity)
        return candidates


    def invert(self, inversion=None, inversion_degree=None):
        """returns a new AbstractChord based off this one, but inverted.
        not to be confused with self.__invert__!"""
        if inversion >= self.order:
            # mod inversion back into chord range: i.e. Chord('C').invert(3) is the same as invert(0)
            inversion = inversion % self.order
        return self._reinit(factors=self.factors, inversion=inversion, inversion_degree=inversion_degree)

    def simplify(self):
        """returns the simplest version of this chord,
        which is a major or minor triad for chords that contain a 3rd,
        or a 5 (power chord) for indeterminate chords,
        always in root position."""
        new_factors = ChordFactors({f:v for f,v in self.factors.items() if f in [1,3,5]})
        return self._reinit(factors=new_factors, inversion=0)

    def get_variants(self, min_likelihood=0.5, min_consonance=0.35, num_changes=1,
                 additive=True, subtractive=True, mutative=True):
        """retrieves variations of this chord by adding, subtracting and/or altering single factors"""
        variant_chords = set() # set of all unfiltered variant chords to be filtered later
        # additive modifier variants:
        if additive:
            unused_factors = [f for f in range(1,14) if f not in self.factors]
            for f in unused_factors:
                new_factors = dict(self.factors)
                for acc in (-1, 0, 1):
                    new_factors[f] = acc
                    new_factors = ChordFactors(new_factors)
                    # allow these factors if they are registered:
                    if new_factors in factors_to_chord_names:
                        new_chord = self._reinit(factors=new_factors, inversion=0)
                        variant_chords.add(new_chord)
        if subtractive:
            droppable_factors = [f for f in self.factors if f not in (1,5)]
            for f in droppable_factors:
                new_factors = dict(self.factors)
                del new_factors[f]
                new_factors = ChordFactors(new_factors)
                if new_factors in factors_to_chord_names:
                    new_chord = self._reinit(factors=new_factors, inversion=0)
                    variant_chords.add(new_chord)
        if mutative:
            # try moving factors up or down:
            mutable_factors = [f for f in self.factors if f != 1]
            for f in mutable_factors:
                current_value = self.factors[f]
                # try the other values for this factor:
                possible_values = [v for v in (-1, 0, 1) if v != current_value]
                for v in possible_values:
                    new_factors = dict(self.factors)
                    new_factors[f] = v
                    new_factors = ChordFactors(new_factors)
                    if new_factors in factors_to_chord_names:
                        new_chord = self._reinit(factors=new_factors, inversion=0)
                        variant_chords.add(new_chord)
            # special case: try suspensions as well, since they are 'mutations'
            # of the third but considered a separate degree
            if 3 in self.factors and 2 not in self.factors:
                new_factors = self.factors + ChordModifier('sus2')
                if new_factors in factors_to_chord_names:
                    new_chord = self._reinit(factors=new_factors, inversion=0)
                    variant_chords.add(new_chord)
            if 3 in self.factors and 4 not in self.factors:
                new_factors = self.factors + ChordModifier('sus4')
                if new_factors in factors_to_chord_names:
                    new_chord = self._reinit(factors=new_factors, inversion=0)
                    variant_chords.add(new_chord)
        # finally: filtering step by likelihood and consonance:
        filtered_variants = [ch for ch in variant_chords if ch.likelihood >= min_likelihood and ch.consonance >= min_consonance]
        # sort by likelihood, then variance:
        sorted_variants = sorted(filtered_variants, key=lambda ch: (-ch.likelihood, -ch.consonance))
        return sorted_variants
    @property
    def variants(self):
        return self.get_variants()

    @property
    def inversions(self):
        return self.get_inversions()
    def get_inversions(self):
        """a list of this chord's inversions"""
        inversions = []
        for i in range(self.order):
            if i != self.inversion:
                inversions.append(self.invert(i))
        return inversions

    def on_root(self, root_note, prefer_sharps=None):
        """constructs a Chord object from this AbstractChord with respect to a
            desired root"""
        return Chord.from_cache(root=root_note, factors=self.factors, inversion=self.inversion,
                                assigned_name=self.assigned_name)

    def in_scale(self, scale, degree=None, factor=None):
        """constructs a ScaleChord from this AbstractChord on a desired degree or
            factor of a desired Scale"""
        from src.scales import ScaleChord
        return ScaleChord(factors=self.factors, inversion=self.inversion, scale=scale, degree=degree, factor=factor)

    def on_bass(self, bass_note):
        """constructs an inverted Chord object from this inverted AbstractChord with respect to a desired bass"""
        if self.inversion == 0:
            # bass is root, so on_bass is equivalent to on_root:
            return self.on_root(bass_note)
        else:
            # construct the root note from the desired bass note and this AbstractChord's inversion:
            root_to_bass_interval = self.root_intervals[self.inversion]
            root_note = Note.from_cache(bass_note) - root_to_bass_interval
            return Chord.from_cache(root=root_note, factors=self.factors, inversion=self.inversion)

    # @property
    # def triad(self):
    #     """returns the first three notes of this chord"""
    #     return AbstractChord(intervals=self.intervals[:3])

    @property
    def triad(self):
        """returns the simple major or minor triad associated with this AbstractChord"""
        if self.quality.major_ish:
            return AbstractChord.from_cache('')
        elif self.quality.minor_ish:
            return AbstractChord.from_cache('m')
        else:
            raise MusicError(f'{self} has indeterminate quality and therefore has no associated triad')

    def __len__(self):
        """this chord's order, i.e. the number of notes/factors"""
        return len(self.factors)

    @property
    def order(self):
        return len(self)

    def is_tertian(self):
        """returns True if each ascending (unstacked) interval is a third"""
        steps = self.intervals.strip().unstack()
        step_degs = [step.degree for step in steps]
        if check_all(step_degs, '==', 3):
            return True
        else:
            return False

    def is_inverted_tertian(self):
        """returns True if any of this chord's inversions are tertian"""
        for inv in self.inversions:
            if inv.is_tertian():
                return True
        return False

    def _reinit(self, *args, root=None, notes=None, scale=None, key=None, degree=None, **kwargs):
        """reinitialises another object of this same type,
        whether it is AbstractChord or ScaleChord or KeyChord etc.
        if scale/key/degree args are not given, passes the same ones as this object."""
        if self.__class__.__name__ == 'AbstractChord':
            return self.__class__(*args, **kwargs)
        elif self.__class__.__name__ == 'Chord':
            if root is None and notes is None:
                root = self.root
            return self.__class__(*args, root=root, notes=notes, assigned_name=self.assigned_name, **kwargs)
        elif self.__class__.__name__ == 'ScaleChord':
            if scale is None:
                scale = self.scale
            if degree is None:
                degree = self.scale_degree
            return self.__class__(*args, scale=scale, degree=degree, **kwargs)
        elif self.__class__.__name__ == 'KeyChord':
            if degree is None:
                if root is None: # preserve same degree if root not given
                    degree = self.scale_degree
                else: # but if root is given, silently shift the degree as well
                    assert key is None, "KeyChord reinit wants to silently shift degree but got conflicting key arg"
                    if not isinstance(root, Note):
                        root = Note(root)
                    if root in self.key.note_degrees:
                        degree = self.key.note_degrees[root]
                    else:
                        degree = self.key.fractional_note_degrees[root]
            if root is None and notes is None:
                root = self.root
            if key is None:
                key = self.key
            return self.__class__(*args, key=key, root=root, notes=notes, degree=degree, **kwargs)
        else:
            raise Exception(f'Unrecognised Chord subclass: {self.__class__}')


    ### magic methods for chord arithmetic etc:

    def __add__(self, other):
        """Chord + Chord results in a ChordList (which can further be analysed as a progression)
        Chord + Note appends the Note to the Chord to produce a new Chord
        Chord + Interval produces a new Chord that is transposed by that Interval
        Chord + ChordModifier produces a new Chord where that modifier has been applied
        Chord + List adds from each item in the list recursively and successively"""
        if isinstance(other, str):
            # parse if this str is a note or a chord, preferring note first:
            if parsing.is_valid_note_name(other):
                other = Note.from_cache(other)
            elif parsing.begins_with_valid_note_name(other):
                other = self.__class__(other) # casts to same type as self
            else:
                raise ValueError(f'{self.__class__}.__add__ could not understand string operand: {other}')

        if isinstance(other, self.__class__):
            # concatenation of chords to produce ChordList (or ChordProgression?):
            return ChordList([self, other])

        elif isinstance(other, Note):
            # addition of new note to produce new chord:
            new_notes = list(self.notes) + [other]
            return self._reinit(notes=new_notes)

        elif isinstance(other, (int, Interval)):
            # transposition by int/interval:
            new_root = self.root + int(other)
            return self._reinit(factors=self.factors, root=new_root)

        elif isinstance(other, ChordModifier):
            new_factors = self.factors + other
            return self._reinit(factors=new_factors, root=self.root)

        elif isinstance(other, list):
            temp_chord = self
            # recursively call this method on each item in the list:
            for item in other:
                temp_chord = temp_chord + item
            return temp_chord

        else:
            raise TypeError(f'__add__ method not defined between {self.__class__} and type: {type(other)}')

    def __sub__(self, other):
        """Chord - Note produces a new Chord with that note deleted
        Chord - Chord produces a chord distance object (as ChordModifier)
        Chord - Interval transposes this chord downward by that interval"""
        if isinstance(other, str):
            # try interpreting string as note name:
            if parsing.is_valid_note_name(other):
                other = Note.from_cache(other)
            # otherwise as chord name:
            elif parsing.begins_with_valid_note_name(other):
                other = Chord.from_cache(other)
            else:
                raise ValueError(f'{self.__class__}.__sub__ could not understand string operand: {other}')

        if isinstance(other, Note):
            # note deletion
            assert other != self.root, "Cannot delete a chord's root"
            assert other != self.bass, "Cannot delete a chord's bass note"
            new_notes = [n for n in self.notes if n != other]
            return self._reinit(notes=new_notes, bass=self.bass)

        elif isinstance(other, Chord):
            return self.chord_distance(other)

        elif isinstance(other, (int, Interval)):
            new_root = self.root - int(other)
            return self._reinit(root=new_root, factors=self.factors, inversion=self.inversion)

        else:
            raise TypeError(f'{self.__class__}.__sub__ not defined for type: {type(other)}')

    def chord_distance(self, other):
        """distance between two Chords as a ChordModifier object"""
        assert isinstance(other, AbstractChord)
        return self.factors - other.factors

    def __contains__(self, item):
        """AbstractChords can contain degrees (as integers), or intervals (as Intervals)"""
        if isinstance(item, Interval):
            return item in self.intervals # note: uses inverted intervals, not root position
        elif isinstance(item, int):
            return item in self.factors.keys()
        else:
            raise TypeError(f'AbstractChord object cannot contain items of type: {type(item)}')

    def __eq__(self, other):
        """AbstractChords are equal to others on the basis of their factors and inversion"""
        if not isinstance(other, Chord):
            return (self.factors == other.factors) and (self.inversion == other.inversion)
        else:
            raise TypeError(f'AbstractChords cannot be compared to {other.__class__.__name__}s')

    def __hash__(self):
        return hash(((tuple(self.factors.items())), self.inversion))

    # enharmonic equality:
    def enharmonic_to(self, other):
        """Compares enharmonic equivalence between AbstractChords,
        which is: do they contain the exact same flattened intervals from bass?
        by this definition, m7/1 is enharmonic to maj6, maj7add4 is enharmonic to maj7add11, etc."""

        if isinstance(other, AbstractChord) and not isinstance(other, Chord):
            return set(self.intervals.flatten().unique()) == set(other.intervals.flatten().unique())
        else:
            raise TypeError(f'Enharmonic equivalence operator & not defined between AbstractChord and: {type(other)}')

    @staticmethod
    def from_cache(name=None, factors=None, modifiers=None, inversion=None, assigned_name=None):
        # efficient abstractchord init by cache lookup of proper name or proper ChordFactors object:
        if name is not None:
            cache_key = (name, None, None, inversion, assigned_name)
        elif factors is not None:
            if not isinstance(factors, ChordFactors):
                factors = ChordFactors(factors)
            cache_key = (None, factors, None, inversion, assigned_name)
        elif modifiers is not None:
            cache_key = (None, None, tuple(modifiers), inversion, assigned_name)
        else:
            raise TypeError(f'Chord init from cache must include one of: "name" or "factors" or "modifiers" (and, optionally, "inversion")')

        if cache_key in cached_abstract_chords:
            return cached_abstract_chords[cache_key]
        else:
            chord_obj = AbstractChord(name=name, factors=factors, modifiers=modifiers, inversion=inversion, assigned_name=assigned_name)
            if settings.DYNAMIC_CACHING:
                log(f'Registering abstract chord by key {cache_key} to cache')
                cached_abstract_chords[cache_key] = chord_obj
            return chord_obj


    ### display methods:

    def show(self, tuning='EADGBE', **kwargs):
        """just a wrapper around the Guitar.show method, which is generic to most musical classes,
        so this method is also inherited by all Scale subclasses"""
        from .guitar import Guitar
        Guitar(tuning).show(self, **kwargs)
    on_guitar = show # convenience alias

    @property
    def fretboard(self):
        # just a quick accessor for guitar.show in standard tuning
        return self.show()
    diagram = fretboard

    def get_short_name(self):
        if '/' in self.suffix:
            suffix, inv = self.suffix.split('/')
            inv = f'/{inv}'
        else:
            suffix, inv = self.suffix, ''
        if suffix == '':
            # unique to AbstractChord: report major and dominant suffix
            return f'maj{inv}'
        elif suffix.isnumeric() and suffix not in {'5', '6'}: # dominant chords (which are not 5s or 6s)
            return f'dom{suffix}{inv}'
        else:
            return f'{suffix}{inv}'
    @property
    def short_name(self):
        return self.get_short_name()

    def get_name(self):
        return f'{self.short_name} chord'
    @property
    def name(self):
        return self.get_name()

    def __str__(self):
        return f'{self._marker}{self.name}'

    def __repr__(self):
        # note that intervals are presented with respect to inversion
        return f'{str(self)} {self.intervals}'

    # AbstractChord object unicode identifier:
    _marker = settings.MARKERS['AbstractChord']
    _unknown_char = settings.CHARACTERS['unknown_chord']

################################################################################

class Chord(AbstractChord):
    """a Chord built on a note of the chromatic scale, but in no particular octave.
            shares all of the attributes/methods of AbstractChord,
            but additionally has a root and a note list. (and a sharp/flat preference)
            if inverted, also stores bass note, and note list in inverted position.
    """

    def __init__(self, name=None,
                       root=None, factors=None, intervals=None, notes=None,
                       inversion=None, inversion_degree=None, bass=None,
                       modifiers=None,
                       in_key=None, prefer_sharps=None,
                       assigned_name=None, _debug=False):
        """initialised in one of three ways:

        1. from 'notes' arg, as a list of Notes (or a note-string),
            in which case we set the first Note as the root,
            and initialise the remaining intervals as with an AbstractChord.

        2. from 'name' arg, as a proper Chord name (like "Csus2" or "Ebminmaj7"),
            in which case we extract the root note from the string, and initialise
            the remaining suffix as with an AbstractChord.
                name can also specify an inversion, such as: "Csus2/D", which
                overwrites explicit inversion args (see below)

        3. from 'root' arg, as a Note object (or an object that casts to a Note),
            in combination with any of the keyword args that would initialise an AbstractChord,
            i.e. one of 'factors', 'intervals', or 'name'.

        if a NoteList, or IntervalList, or ChordFactors object is fed as first arg (name),
            we'll try to detect that and re-parse the args appropriately.
            we'll even check if name is a valid note-string, like Chord('CEA').

        for any initialisation method, an inversion can also be specified
            (unless a slash chord name was used). this must be one of:

                a) 'inversion', the index of the bass note with respect to root.
                    (same as common musical term: "Cm, 2nd inversion" is Cm/G)

                b) 'inversion_degree', the degree of the bass note.
        """

        # if prefer_sharps is not given, we parse the name to see if we've been asked for it:
        if prefer_sharps is None and isinstance(name, str):
            # have we been given the name of a tonic note with a sharp in it?
            if parsing.contains_sharp(name[1:3]):
                prefer_sharps = True

        # re-parse args to detect if 'name' is a list of notes, a list of intervals, or a dict of chordfactors:
        name, root, factors, intervals, notes = self._reparse_args(name, root, factors, intervals, notes)


        if notes is not None: # initialise from ascending note list by casting notes as intervals from root
            self.ignore_interval_degrees = True
            # ignore intervals/factors/root inputs
            assert root is None and factors is None and intervals is None
            assert name is None # but allow inversions
            note_list = NoteList(notes)
            # recover intervals and root, and continue to init as normal:
            intervals = NoteList(notes).ascending_intervals()

            root = note_list[0]

        else:
            self.ignore_interval_degrees = False # interval degrees matter for init

        # if name is a proper chord name like 'C' or 'Amaj' or 'D#sus2', separate it out into root and suffix components:
        self.root, suffix = self._parse_root(name, root)

        if assigned_name is None:
            self.assigned_name = suffix # the (root-less) name this chord was initialised by (or None, if not initialised by a name)
        else:
            self.assigned_name = assigned_name

        assert self.root is not None

        # allow inversion by bass keyword arg, by reallocating into inversion arg for _parse_input:
        if bass is not None:
            assert inversion is None
            inversion = Note.from_cache(bass).name

        # some flags to control naming behaviours:
        self.compound_slash_chord = False # flag to denote 'fake' slash chords like Am/F
                                          # (overwritten later if needed, in _parse_inversion)

        # recover factor offsets, intervals from root, and inversion position from input args:
        self.factors, self.root_intervals, inversion = self._parse_input(suffix, factors, intervals, inversion, inversion_degree, modifiers, _allow_note_name=True, _debug=_debug)
        # note that while 'inversion' in AbstractChord comes out as strictly int or None
        # here we allow it to be a string denoting the bass note, which we'll correct in a minute

        self.root_notes = NoteList([self.root + iv for iv in self.root_intervals])

        self.quality = self._determine_quality()

        # set sharp preference based on root note:
        self._set_sharp_preference(prefer_sharps) ### TBI: move this up and make it affect root_notes etc. as well?

        # discover the correct inversion parameters, as well as inverted notes / intervals if they differ from root position:
        inv_params, self.notes, self.intervals = self._parse_inversion(inversion)
        self.inversion, self.inversion_degree, self.bass = inv_params

        # mapping of chord factors to intervals from tonic:
        self.factor_intervals = {i.extended_degree: i for i in self.root_intervals}
        self.interval_factors = reverse_dict(self.factor_intervals)
        # mapping of chord factors to notes:
        self.factor_notes = {factor: (self.root_notes[i]) for i, factor in enumerate(self.factors)}
        self.note_factors = reverse_dict(self.factor_notes)

        ### check if this chord is registered
        ### (and if not, post-hoc register it)
        if not self._is_registered() and self.assigned_name is not None:
            log(f'Registering chord with factors {self.factors} as assigned name: {self.assigned_name}')
            self._register()
            # log(f'Confirmed registration: {self._is_registered()} (as: {self.name})')


    @staticmethod
    def _reparse_args(name, root, factors, intervals, notes):
        """re-parse args to detect if 'name' is a list of notes, a list of intervals, or a dict of chordfactors,
        and returns the appropriate 'corrected' args if so."""
        # accept re-casting if name is just another Chord object:
        if isinstance(name, Chord):
            # initialise by input chord's name: (which contains its inversion information)
            assert (factors, intervals, notes) == (None, None, None), f'tried to initialise Chord object from another chord but with conflicting factors/intervals/notes arg'
            name = name.name
        # is name an IntervalList, or a list that contains only Intervals/ints:
        if isinstance(name, IntervalList) or (isinstance(name, (list, tuple)) and check_all(name, 'isinstance', (int, Interval))):
            assert intervals is None, f'list of Intervals was passed as first input to Chord init, but intervals arg was also given'
            intervals = name
            name = None
        # is name a NoteList, or a list that contains only Notes/strings:
        elif isinstance(name, NoteList) or (isinstance(name, (list, tuple)) and check_all(name, 'isinstance', (str, Note))):
            assert notes is None, f'list of Notes was passed as first input to Chord init, but notes arg was also given'
            notes = name
            name = None
        elif isinstance(name, str):
            ### here we must distinguish if name is a potential note_string, of the kind we can parse out
            parse_result = parsing.parse_out_note_names(name, graceful_fail=True)
            if parse_result is not False and len(parse_result) >= 2: # we don't allow note_strings for chord init unless they contain 2 or more notes
                notes = parse_result
                name = None
            else:
                # this is not a note_string, so just return the args as they came
                pass

        return name, root, factors, intervals, notes

    @staticmethod
    def _parse_root(name, root):
        """takes the class init method's name and root args, and determines which has been given.
        returns root as a Note object, and chord suffix as string or None"""
        if name is not None:
            # assume no root given
            root_name, suffix = parsing.note_split(name)
            root = Note.from_cache(root_name)
        elif root is not None:
            # assume no name given
            root = Note.from_cache(root)
            suffix = None # name # i.e. None
        else:
            raise TypeError('neither name nor root provided to Chord init, we need one or the other!')
        return root, suffix


    def _parse_inversion(self, inversion):
        """given an inversion as int (Xth inversion) or string (bass note),
        with respect to already-defined self.root_notes.
        returns canonical forms: ((inversion, inversion_degree, bass),
                                  inverted_notes, inverted_intervals) """
        if inversion == 0:
            inversion_degree = None
            # inversion = inversion_degree = None
            # no inversion, so the bass is just the root, and the notes/intervals are in root position:
            bass = self.root
            inverted_notes, inverted_intervals = self.root_notes, self.root_intervals

            inv_params = (inversion, inversion_degree, bass)
            return (inv_params), inverted_notes, inverted_intervals

        elif isinstance(inversion, int):
            # assert 0 <= inversion, f'Cannot have a negative inversion'
            inversion = inversion % len(self)
            inversion_degree = self.root_intervals[inversion].extended_degree
            bass = self.root_notes[inversion]
        elif isinstance(inversion, (Note, str)):
            bass = Note.from_cache(inversion)

            ####################################################################

            ### here we catch a special case: inversion over a bass note that is not in the specified chord.
            # e.g. something like Chord('D/C#') - it is not really a D major chord,
            # but a voicing of Dmaj7 or something

            # if bass not in self.factor_notes.values():
            if bass not in self.root_notes:

                return self._parse_compound_slash_chord(bass)

            else:
                # inversion_degree = [k for k,v in self.factor_notes.items() if v == bass][0]
                inversion = [i for i,n in enumerate(self.root_notes) if n == bass][0]
                inversion_degree = self.root_intervals[inversion].extended_degree
        bass_place = inversion # kludge? odd behaviour around 11sus4 // 13sus4 // 13sus2 chords

        inverted_intervals = self.root_intervals.invert(bass_place)
        inverted_notes = NoteList([bass + i for i in inverted_intervals])

        inv_params = (inversion, inversion_degree, bass)
        return (inv_params), inverted_notes, inverted_intervals

    def _parse_compound_slash_chord(self, slash_bass, max_proper_name_rarity=10):
        """as _parse_inversion, but handles the logic behind compound slash chords
        i.e. those with a bass that is not in the prefix chord, such as Am/G.
        requires an already-initialised self.root_notes (without the extra bass),
        and sets root_notes and root_intervals to appropriate new values."""
        full_notes = self.root_notes + NoteList([slash_bass])
        asc_intervals = full_notes.ascending_intervals()
        inversion = len(full_notes)-1 # final inversion by definition (bc the slash note is on bottom)
        inversion_degree = asc_intervals[-1].extended_degree
        self.root_notes = full_notes
        self.root_intervals = asc_intervals
        # and add new degree to self.factors:
        self.factors[inversion_degree] = self.root_intervals[-1].offset_from_default

        inv_notes = self.root_notes.rotate(inversion)
        inv_intervals = self.root_intervals.invert(inversion)

        self.compound_slash_chord = True
        if (inv_intervals in intervals_to_chord_names):
            # record this slash chord's 'true' name for display purposess
            true_root = slash_bass
            abs_true_name = intervals_to_chord_names[inv_intervals]
            self.compound_true_name = f'{true_root.chroma}{abs_true_name}'
        else:
            self.compound_true_name = None

        return (inversion, inversion_degree, slash_bass), inv_notes, inv_intervals

    @property
    def _inv_string(self):
        """inversion string, used internally by suffix method (and inherited by subclasses)"""
        return f'/{self.bass.name}' if (self.inversion != 0) else ''

    def _detect_sharp_preference(self, default=False): #tonic, quality='major', default=False):
        """detect if a chord should prefer sharp or flat labelling
        depending on its tonic and quality"""
        if self.quality.major:
            if self.root in notes.sharp_major_tonics:
                return True
            elif self.root in notes.flat_major_tonics:
                return False
            else:
                return default
        elif self.quality.minor:
            if self.root in notes.sharp_minor_tonics:
                return True
            elif self.root in notes.flat_minor_tonics:
                return False
            else:
                return default
        else:
            return default

    def _set_sharp_preference(self, prefer_sharps):
        """set the sharp preference of this Chord,
        and of all notes inside this Chord,
        including the tonic, root, and constituent factors"""
        if prefer_sharps is None:
            # detect from object attributes
            prefer_sharps = self._detect_sharp_preference()

        self.prefer_sharps = prefer_sharps
        # reinitialise note objects (to avoid caching/hashing interactions)
        self.root = Note.from_cache(position=self.root.position, prefer_sharps=prefer_sharps)
        self.root_notes = NoteList([Note.from_cache(position=n.position, prefer_sharps=prefer_sharps) for n in self.root_notes])

    @property
    def sharp_notes(self):
        """returns notes inside self, all with sharp preference"""
        return NoteList([Note.from_cache(n.chroma, prefer_sharps=True) for n in self.notes])

    @property
    def flat_notes(self):
        """returns notes inside self, all with flat preference"""
        return NoteList([Note.from_cache(n.chroma, prefer_sharps=False) for n in self.notes])

    def __contains__(self, item):
        """Chords can contain degrees (as integers), intervals (as Intervals),
        or notes (as Notes, or strings that cast to Notes)"""
        if isinstance(item, Interval):
             return item in self.intervals # note: uses inverted intervals, not root position
        elif isinstance(item, int):
            return item in self.factors
        elif isinstance(item, (Note, str)):
            n = Note.from_cache(item)
            return n in self.notes
        else:
            raise TypeError(f'Chord object cannot contain items of type: {type(item)}')

    def __eq__(self, other):
        """Chords are equal to others on the basis of their root, factors and inversion"""
        if isinstance(other, Chord):
            return (self.factors == other.factors) and (self.inversion == other.inversion) and (self.root == other.root)
        else:
            raise TypeError(f'Chords can only be compared to other Chords, not: {type(other)}')

    def __hash__(self):
        return hash(((tuple(self.factors.items())), self.inversion, self.root))

    # enharmonic equality:
    def enharmonic_to(self, other):
        """Compares enharmonic equivalence between Chords,
        which is: do they contain the exact same unique notes? (if not in the same order)"""

        if isinstance(other, Chord):
            return set(self.notes.unique()) == set(other.notes.unique())
        else:
            raise TypeError(f'Enharmonic equivalence operator & not defined between Chord and: {type(other)}')

    # enharmonic comparison operator:
    def __and__(self, other):
        return self.enharmonic_to(other)


    ### relative majors/minors are not very well-defined for chords (as opposed to keys), but we can have them anyway:
    @property
    def relative_minor(self):
        # assert not self.minor, f'{self} is already minor, and therefore has no relative minor'
        assert self.quality.major_ish, f'{self} is not major, and therefore has no relative minor'
        rel_root = notes.relative_minors[self.root.name]
        new_factors = ChordFactors(self.factors)
        new_factors[3] -= 1 # flatten third
        if 5 in self.factors: # if fifth is aug/dim, make it dim/aug
            new_factors[5] = -self.factors[5]
        return self._reinit(factors=new_factors, root=rel_root, inversion=self.inversion)

    @property
    def relative_major(self):
        # assert not self.major, f'{self} is already major, and therefore has no relative major'
        assert self.quality.minor_ish, f'{self} is not minor, and therefore has no relative major'
        rel_root = notes.relative_majors[self.root.name]
        new_factors = ChordFactors(self.factors)
        new_factors[3] += 1 # raise third
        if 5 in self.factors: # if fifth is aug/dim, make it dim/aug
            new_factors[5] = -self.factors[5]
        return self._reinit(factors=new_factors, root=rel_root, inversion=self.inversion)

    @property
    def relative(self):
        if self.quality.major_ish:
            return self.relative_minor
        elif self.quality.minor_ish:
            return self.relative_major
        else:
            raise MusicError(f'Chord {self} is neither major or minor, and therefore has no relative')

    @property
    def parallel_minor(self):
        if not self.quality.major_ish:
            raise MusicError(f'{self} is not major, and therefore has no parallel minor')
        new_factors = ChordFactors(self.factors)
        new_factors[3] -= 1 # flatten third
        if 5 in self.factors: # if fifth is aug/dim, make it dim/aug
            new_factors[5] = -self.factors[5]
        return self._reinit(factors=new_factors, root=self.root, inversion=self.inversion)

    @property
    def parallel_major(self):
        if not self.quality.minor_ish:
            raise MusicError(f'{self} is not minor, and therefore has no parallel major')
        new_factors = ChordFactors(self.factors)
        new_factors[3] += 1 # raise third
        if 5 in self.factors: # if fifth is aug/dim, make it dim/aug
            new_factors[5] = -self.factors[5]
        return self._reinit(factors=new_factors, root=self.root, inversion=self.inversion)

    @property
    def parallel(self):
        if self.quality.major:
            return self.parallel_minor
        elif self.quality.minor:
            return self.parallel_major
        else:
            raise MusicError(f'Chord {self} is neither major or minor, and therefore has no parallel')

    @property
    def triad(self):
        """returns the simple major or minor triad with the same root and quality as this chord"""
        if self.quality.major_ish:
            return major_triads[self.root]
        elif self.quality.minor_ish:
            return minor_triads[self.root]
        else:
            raise MusicError(f'{self} has indeterminate quality and therefore has no associated triad')

    def get_adjacent_chords(self, num_notes=1, distances=[2,1,0,-1,-2], # i.e. up or down by whole or half step
                            # filters for types of motion: (relevant for num_notes > 1)
                            parallel=True, similar=True, contrary=True, oblique=True,
                            # filters for resulting chords:
                            min_likelihood=1., min_consonance=0.35,
                            whitelist=['dim'], blacklist=['sus2', 'sus4'],
                            require_different_root=False):
        """find the chords that differ from this chord by moving one
        of its notes up or down by a step (or a half step).
        if require_different_root is True, only returns those chords that have a different root to this one.
            (e.g. filter out Cm when coming from C)"""

        # explored_note_sets = set()
        output_chords = []
        # loop through N-sized permutations of the notes in this chord:
        replacement_permutations = list(itertools.permutations(range(len(self)), num_notes)) # list of tuples of note indices
        # print(f'Possible replacement permutations: {",".join([str(r) for r in replacement_permutations])}')
        # import ipdb; ipdb.set_trace()
        for rep_idxs in replacement_permutations:
            # print(f' Trying replacement permutation: {rep_idxs}')
            stable_idxs = [j for j in range(len(self)) if j not in rep_idxs]

            # which notes do stay stable, and which are replaced:
            rep_notes = [self.notes[i] for i in rep_idxs]
            stable_notes = [self.notes[j] for j in stable_idxs]

            distance_permutations = list(itertools.product(distances, repeat=num_notes))
            # log(f'  Possible distance permutations: {",".join([str(d) for d in distance_permutations])}')
            # loop through all possible ways of shifting those notes:
            for rep_dists in distance_permutations:
                if (not oblique) and 0 in rep_dists:
                    # log(f'  {rep_dists} filtered because: oblique')
                    continue
                if (not parallel) and all_equal(rep_dists):
                    # log(f'  {rep_dists} filtered because: parallel')
                    continue
                nonzero_dists = [d for d in rep_dists if d != 0]
                dist_directions = [sign(d) for d in nonzero_dists]
                if (not similar):
                    if all_equal(dist_directions) and not all_equal(nonzero_dists):
                        # log(f'  {rep_dists} filtered because: similar')
                        continue
                if (not contrary):
                    if not all_equal(dist_directions):
                        # log(f'  {rep_dists} filtered because: contrary')
                        continue

                # log(f'   Trying distance permutation: {rep_dists}')

                new_notes = [n + d for n,d in zip(rep_notes, rep_dists)]
                # check if any of the new notes have landed on an existing note:
                valid_replacement = True
                for i, n in enumerate(new_notes):
                    other_new_notes = [new_notes[j] for j in range(num_notes) if j!=i]
                    num_overlaps = 0
                    if n in other_new_notes:
                        valid_replacement = False
                        log(f'-   Considered replacing {rep_notes} with {new_notes}, to make {stable_notes + new_notes}')
                        log(f'-   But replacement discarded: {n} clashes with other replacements {other_new_notes}')
                        break
                    elif n in self.notes: # (or if the same note is repeated)
                        num_overlaps += 1
                        # print(f'-   Considered replacing {rep_notes} with {new_notes}, to make {stable_notes + new_notes}')
                        # print(f'-   But replacement discarded: clashes with {self.notes} or contains repeats')
                        # break
                if num_overlaps == num_notes:
                    valid_replacement = False
                    log(f'-   Considered replacing {rep_notes} with {new_notes}, to make {stable_notes + new_notes}')
                    log(f'-   But replacement discarded: overlaps exactly with {self.notes}')

                if valid_replacement:
                    # these notes have been shifted and form a new chord that is not the original
                    new_chord_notes = NoteList(stable_notes + new_notes)
                    chord_matches = matching_chords(new_chord_notes, exact=True, invert=False,
                                        min_likelihood=min_likelihood, min_consonance=min_consonance,
                                        whitelist=whitelist, blacklist=blacklist, display=False)
                    if len(chord_matches) > 1:
                        log(f'++    Multiple possible chord matches for notes {new_chord_notes}: {[ch.name for ch in chord_matches]}')
                        # valid_matches = [ch for ch in chord_matches if ch.likelihood >= min_likelihood]
                        # output_chords.extend(chord_matches)
                    elif len(chord_matches) == 0:
                        pass # no matches
                        # print(f'No matches for: {new_chord_notes}')
                    else:
                        log(f'==    Valid chord:  {new_chord_notes}: {chord_matches[0].name}')
                        # match = chord_matches[0]
                            # output_chords.append(match)
                    for chord in chord_matches:
                        # filter out chords with the same root if asked for:
                        if (chord.root != self.root) or (not require_different_root):
                            # and avoid adding the same chord twice:
                            if chord not in output_chords:
                                output_chords.append(chord)
        return output_chords

        # for n in triad_notes:
        #     # the notes that are kept steady:
        #     stable_notes = [sn for sn in triad_notes if sn != n]
        #     distances = [2, 1, -1, -2] # up or down by whole or half step
        #     for d in distances:
        #         new_note = n + d
        #         if new_note not in triad_notes:
        #             new_chord_notes = NoteList(stable_notes + [new_note])
        #             chord_matches = matching_chords(new_chord_notes, exact=True, min_likelihood=0.8, display=False)
        #             if len(chord_matches) > 1:
        #                 # print(f'Multiple possible chord matches for notes {new_chord_notes}: {[ch.name for ch in chord_matches]}')
        #                 valid_matches = [ch for ch in chord_matches if ch.likelihood >= min_likelihood]
        #                 output_chords.extend(valid_matches)
        #             elif len(chord_matches) == 0:
        #                 pass # no matches
        #                 # print(f'No matches for: {new_chord_notes}')
        #             else:
        #                 # print(f'    Valid chord:  {new_chord_notes}: {chord_matches[0].name}')
        #                 match = chord_matches[0]
        #                 if match.likelihood >= min_likelihood:
        #                     output_chords.append(match)
        # return output_chords

    def get_semiadjacent_triads(self):
        """find the chords that differ from this (basic triad) chord by moving TWO
        of its notes up or down by a step (or a half step).
        only searches for basic major or minor triads."""
        ... # TBI

    def __neg__(self):
        """returns the parallel major or minor (using negation operator '-')"""
        return self.parallel

    def __invert__(self):
        """returns the relative major or minor (using inversion operator '~')"""
        return self.relative

    def invert(self, inversion=None, inversion_degree=None, bass=None):
        """returns a new Chord based off this one, but inverted.
        not to be confused with self.__invert__!"""
        return self._reinit(factors=self.factors, root=self.root, inversion=inversion, inversion_degree=inversion_degree, bass=bass)

    def root_position(self):
        """return this Chord in root position (i.e. inversion=0)"""
        if self.inversion != 0:
            return self.invert(0)
        else:
            return self
    def abstract(self):
        """return the AbstractChord that this Chord is associated with"""
        return AbstractChord.from_cache(factors=self.factors, inversion=self.inversion, assigned_name=self.assigned_name)

    def in_key(self, key, degree=None, factor=None):
        """constructs a KeyChord from this Chord on a desired degree or
            factor of a desired Key"""
        from src.keys import KeyChord
        return KeyChord(root=self.root, factors=self.factors, inversion=self.inversion,
                        key=key, degree=degree, factor=factor, assigned_name = self.assigned_name)


    #### useful utility methods/properties:

    def summary(self):
        print(f"""
        {str(self)}
        Type:           {type(self)}

        Name:           {self.name}
        Root:           {self.root}
        Intervals:      {self.intervals}
        Notes:          {self.notes}

        Factors:        {self.factors}
        Inversion:      {self.inversion}
          (bass note):  {self.bass}

        Suffix:         {self.suffix}
        Quality:        {self.quality}

        SharpPref:      {self.prefer_sharps}
        assigned_name:  {self.assigned_name}
        registered:     {self._is_registered()}

        ID:             {id(self)}""")

    @staticmethod
    def from_cache(name=None, factors=None, modifiers=None, root=None, inversion=None, assigned_name=None):
        # efficient chord init by cache lookup of proper name or proper ChordFactors object:
        if name is not None:
            cache_key = (name, None, None, None, inversion, assigned_name)
        elif factors is not None or modifiers is not None:
            assert root is not None
            root_chroma = root.chroma if isinstance(root,Note) else root # cast to string
            cache_key = (None, factors, modifiers, root_chroma, inversion, assigned_name)
        else:
            raise TypeError(f'Chord init from cache must include one of: "name", or  "root" plus "factors" or "modifiers"')

        if cache_key in cached_chords:
            return cached_chords[cache_key]
        else:
            chord_obj = Chord(name=name, factors=factors, modifiers=modifiers,
                              root=root, inversion=inversion, assigned_name=assigned_name)
            if settings.DYNAMIC_CACHING:
                log(f'Registering chord by key {cache_key}  to cache')
                cached_chords[cache_key] = chord_obj
            return chord_obj

    #### audio methods:

    # wrappers for the NoteList audio methods of self.notes:
    def _waves(self, *args, **kwargs):
        return self.notes._waves(*args, **kwargs)

    def _chord_wave(self, *args, **kwargs):
        return self.notes._chord_wave(*args, **kwargs)

    def _melody_wave(self, *args, **kwargs):
        return self.notes._melody_wave(*args, **kwargs)

    def play(self, *args, **kwargs):
        self.notes.play(*args, **kwargs)


    #### display methods:

    @property
    def name(self):
        # returns tonic and suffix
        if not self.compound_slash_chord:
            return f'{self.root.name}{self.suffix}'

        # unless this is a compound slash chord, in which case
        # we return what it was named at init (with a warning marker)
        # plus a parenthetical true name if one exists:
        else:
            comp_char = settings.CHARACTERS['compound_slash_chord']
            if self.compound_true_name is not None:
                true_name_str = f' ({self.compound_true_name})'
            else:
                true_name_str = ''
            return f'{self.root.name}{self.assigned_name}{comp_char}{true_name_str}'


    def get_short_name(self):
        # identical to self.name in the case of Chord class,
        # unless a compound slash chord (see self.name)
        return f'{self.root.name}{self.suffix}'

    def __str__(self):
        return f'{self._marker}{self.name}'

    def _dotted_notes(self, markers=True, sep=', '):
        """outputs list of notes in this chord,
        with diacritic dotes to indicate notes outside the starting octave"""
        notes_str = [] # notes are annotated with accent marks depending on which octave they're in (with respect to root)
        up1, up2, down1, down2 = [settings.DIACRITICS[d] for d in ['octave_above', '2_octaves_above', 'octave_below', '2_octaves_below']]

        for i, n in zip(self.intervals, self.notes):
            assert (self.bass + i) == n, f'bass ({self.bass}) + interval ({i}) should be {n}, but is {self.bass + i}'
            if markers:
                this_note_str = str(n)
                start_idx = 2
            else:
                this_note_str = n.name
                start_idx = 1
            nl, na = this_note_str[:start_idx], this_note_str[start_idx:] # note letter and accidental (so we can put the dot over the letter)
            if i < -12:
                notes_str.append(f'{nl}{down2}{na}') # lower diaresis
            elif i < 0:
                notes_str.append(f'{nl}{down1}{na}') # lower dot
            elif i < 12:
                notes_str.append(this_note_str)
            elif i < 24:
                notes_str.append(f'{nl}{up1}{na}') # upper dot
            else:
                notes_str.append(f'{nl}{up2}{na}') # upper diaresis
        notes_str = sep.join(notes_str)
        return notes_str

    def __repr__(self):
        """shows full Chord name as well as constituent notes, with clarifying diacritics:
        dots over note names indicate that note is in a higher octave"""
        lb, rb = NoteList._brackets
        notes_str = self._dotted_notes(markers=True)

        return f'{str(self)}  {lb}{notes_str}{rb}'

    # Chord object unicode identifier:
    _marker = settings.MARKERS['Chord']


################################################################################

# the Factors class is used internally within Chord objects to represent chord tones:

class Factors(UserDict):
    """a class representing the factors of an AbstractChord or Scale, as a dict which has:
        keys: chord degrees (1 representing the root, 5 representing the fifth, etc.)
        values: semitone offsets from default degree intervals.
            e.g. the fifth degree is 7 semitones by default, so {5: -1} implies
            a fifth that is diminished (-1 from perfect), i.e. 6 semitones from root.
        modifiers: a list of Modifier objects that have been applied to this object.
            note these are not modifiers that *should* be applied, but a history for this object.
            applying modifiers must be done using the __add__ method, or the modifier's .apply method"""

    # this class also gets inherited by ChordFactors and ScaleFactors later on,
    # which is why we see a bunch of self.__class__ and self.__name__ in these methods

    def __init__(self, arg=None, modifiers=None, strip_octave=False, auto_increment_clashes=False):
        """accepts any arg that would initialise a dict,
          and also allows a string of degree alterations (e.g. "1-♭3-♭♭5")
          or a list of such alterations (e.g. ["1", "♭3", "♭♭5"])
        also treats init by None (i.e. no args) as a major triad by default."""

        # accept re-casting by dict comp:
        if isinstance(arg, self.__class__):

            arg = {k:v for k,v in arg.items()}

        ### allow initialisation by string or list of chord degrees:
        if isinstance(arg, str):
            ### parse string into list of degrees/alterations by auto splitting non-accidentals
            arg = parsing.auto_split(arg, allow_accidentals=True)

        if isinstance(arg, list) and type(arg[0]) != tuple:
            # parse a list of non-tuples (i.e. invalid list for dict input) as list of chord degrees
            dict_arg = {}
            running_increment = 0 # used for resolving clashes in ScaleFactor construction
            for item in arg:
                assert isinstance(item, str)
                # this is a string denoting a degree or degree alteration, like '2' or 'b3' or '#4'
                mod_dict = parsing.parse_alteration(item)
                degree, offset = list(mod_dict.keys())[0], list(mod_dict.values())[0]

                if degree == 8 and offset == 0:
                    if strip_octave:
                        # default behaviour for ScaleFactors: ignore unaltered 8s since it's just the tonic again
                        continue

                if degree+running_increment in dict_arg:
                    # there is a clash, we've been given the same degree twice
                    if not auto_increment_clashes:
                        # default behaviour for ChordFactors: raise error
                        raise ValueError(f'Factor clash in {self.__class__.__name__} object: Tried to add {mod_dict} to factors but {degree} already exists as: {self[degree]}')
                    else:
                        # default behaviour for ScaleFactors: ignore numbering and add a new factor
                        running_increment += 1

                # in case we've been given two values of the same degree, we must adjust to compensate:
                if running_increment > 0: # (only triggers if auto_increment_clashes is Tre)
                    orig_default_interval = default_degree_intervals[degree]
                    inc_default_interval = default_degree_intervals[degree+running_increment]
                    inc_offset = inc_default_interval - orig_default_interval
                    degree = int(degree) + running_increment
                    offset = int(offset) - inc_offset

                mod_dict = {degree:offset}

                dict_arg.update(mod_dict)


            arg = dict_arg
            # then continue as normal

        if arg is None:
            # default init with no input args is a major triad:
            arg = {1:0, 3:0, 5:0}

        assert type(arg) is dict
        # all keys are sorted by default:
        sorted_keys = sorted(arg.keys())
        input_dict = {k:arg[k] for k in sorted_keys}
        super().__init__(input_dict)

        # modifiers is not a list of modifiers to apply; rather, it is a list of
        # modifiers that HAVE been applied to this object, like a history
        if modifiers is None:
            self.modifiers = []
        else:
            self.modifiers = list(modifiers)

    @property
    def degrees(self):
        return list(self.keys())

    @property
    def offsets(self):
        return list(self.values())

    @property
    def order(self):
        """the number of notes in the chord/scale that this object represents"""
        return len(self)

    def to_intervals(self, as_dict=False):
        """translates these Factors into an IntervalList
        or, if as_dict, into a factor_intervals dict mapping degrees to intervals"""
        if not as_dict:
            return IntervalList([Interval.from_degree(d, offset=o) for d, o in self.items()]).sorted()
        elif as_dict:
            return {d:Interval.from_degree(d, offset=o) for d, o in self.items()}

    @property
    # noun-wrapper for the verb-method 'to_intervals'
    def as_intervals(self):
        return self.to_intervals()

    def __add__(self, other):
        """modifies these factors by the alterations in a ChordModifier,
        return new factors object."""
        output_factors = dict(self)
        output_modifiers = list(self.modifiers)
        if isinstance(other, ChordModifier):
            output_factors = other.apply(self)
            output_modifiers.append(other)
            # output_factors.modifiers.append(other)
        elif isinstance(other, (list, tuple)):
            # apply a list of ChordModifiers instead:
            # output_factors = dict(self)
            output_modifiers = list(self.modifiers)
            for mod in other:
                assert isinstance(mod, ChordModifier), f"ChordFactor tried to be modified by an item in a list that was not a ChordModifier but was: {type(mod)}"
                output_factors = mod.apply(output_factors)
                output_modifiers.append(mod)
                # output_factors.modifiers.append(mod)
        # ensure that we keep ourselves sorted:
        else:
            raise TypeError(f'Cannot add Factors object to type: {type(other)}')
        sorted_keys = sorted(list(output_factors.keys()))
        # return output_factors
        return self.__class__({k: output_factors[k] for k in sorted_keys}, modifiers = output_modifiers)

    def distance(self, other):
        # distance from other actors objects, to detect altered chords from their factors
        # as modifier: what must be done to RIGHT (other) to make it LEFT (self)
        # assert isinstance(other, self.__class__)
        add, modify, remove  = {}, {}, []
        for degree, offset in self.items():
            if degree not in other:
                # other must add this degree at this value
                add[degree] = offset
            elif offset != other[degree]:
                other_offset = other[degree]
                offset_dist = offset - other_offset
                modify[degree] = offset_dist
        for degree in other.keys():
            if degree not in self:
                remove.append(degree)
        dist_modifier = ChordModifier(add=add, modify=modify, remove=remove)
        return dist_modifier

    def __sub__(self, other):
        """the - operator calculates (symmetric) distance between Factor objects"""
        # assert isinstance(other, self.__class__)
        return self.distance(other)

    def _hashkey(self):
        """the input to the hash function that represents this object"""
        return tuple([(k,v) for k,v in self.items()])

    def __hash__(self):
        return hash(self._hashkey())

    def __str__(self):
        factor_strs = [f'{parsing.offset_accidentals[v][0]}{d}' for d,v in self.items()]
        lb, rb = self._brackets
        return f'{lb}{", ".join(factor_strs)}{rb}'

    def __repr__(self):
        return f'{self.__class__.__name__}: {str(self)}'

    # ChordFactors object unicode identifier:
    _brackets = settings.BRACKETS['ChordFactors']

# ChordFactors are simply the type of Factors that apply to Chords:
class ChordFactors(Factors):
    pass
# as opposed to ScaleFactors, defined in the scales module

# a chord's factors look like this:
_major_triad = ChordFactors({1:0, 3:0, 5:0})
# meaning: default intervals of 1st, 3rd, and 5th degrees
# this _major_triad object is used for comparisons, but should never be modified

################################################################################

cache_initialised = False # flag that avoids certain behaviours during library import

# import base rarity definitions for common chord names:
#from .defines.def_chords import chord_names_by_rarity
from def_chords import chord_names_by_rarity


# and calculate the rarities of more complex, modified chords
# based on the relative rarity of the base chord types used
# to formulate them:

max_rarity = len(chord_names_by_rarity)-1
# 'tweaks' are the chord modifiers that can be applied to other base chords: (e.g. the sus2 in C7sus2)
ordered_tweak_names = ['sus4', 'sus2', 'add9', 'add11', 'add13']
tweak_names_by_rarity = {2: ['sus4', 'sus2', 'add9'], 3: ['add11', 'add13']}

# these tweaks make a chord's quality indeterminate, so we don't apply them to chords that have had the minor modifier already applied
ind_tweaks = {'sus4', 'sus2', '5'}
# these chord names cannot be modified: (they are not 'base chords')
unmodifiable_chords = {'', '5', 'add4', 'add9', 'add11', 'add13'}
# '' because most ordinary chord types already imply modification from major, i.e. 'sus4' implies ['' + 'sus4']
# '5' and '(no5)' because they both imply simple removals of triad degrees, and are best handled by fuzzy matching
# and add4/add9/add11 chords because they are themselves tweaks; they combine oddly with sus2/sus4, and must be done strictly in sus/add order

# now we'll loop over those chords and build a dict mapping intervals/factors to their names:
factors_to_chord_names, intervals_to_chord_names = {}, {}
# (while adding chord tweaks/alterations as well)

chord_name_rarities = unpack_and_reverse_dict(chord_names_by_rarity)
tweak_name_rarities = unpack_and_reverse_dict(tweak_names_by_rarity)

new_rarities = {i: [] for i in range(max_rarity +1)}
for rarity, chord_names in chord_names_by_rarity.items():
    log(f'Handling base chords for rarity={rarity}, chords={chord_names}')

    for chord_name in chord_names:
        base_chord = AbstractChord(chord_name)
        log(f'Handling base chord: r:{rarity} {chord_name}')

        if base_chord.factors in factors_to_chord_names or base_chord.intervals in intervals_to_chord_names:
            log(f'  {chord_name} clash with {intervals_to_chord_names[base_chord.intervals]}')
        else:
            factors_to_chord_names[base_chord.factors] = chord_name
            intervals_to_chord_names[base_chord.intervals] = chord_name

# handle the modifiers of base chords in a new loop:
for rarity, chord_names in chord_names_by_rarity.items():
    log(f'Handling modifiers for rarity={rarity}, chords={chord_names}')

    for chord_name in chord_names:
        if chord_name not in unmodifiable_chords:
            base_chord = AbstractChord(chord_name)
            # now: add chord tweaks to each base chord as well, increasing rarity accordingly
            for tweak_name in ordered_tweak_names:
                tweak = qualities.chord_tweaks[tweak_name] # fetch ChordModifier object by name
                # add a tweak if it does not already exist by name and is valid on this base chord:
                if tweak.valid_on(base_chord.factors):
                    # (we check if base chord is major because the tweaks on their own apply to major chords,
                    #  i.e. the chord 'sus2' implies ['' + 'sus2'])
                    if not ((tweak in ind_tweaks) and (base_chord.quality.minor)):
                        altered_name = chord_name + tweak_name

                        altered_factors = base_chord.factors + tweak
                        altered_intervals = altered_factors.to_intervals()
                        # avoid double counting: e.g. this ensures that '9sus4' and 'm9sus4' are treated as one chord, '9sus4', despite both being a valid chord init
                        if altered_factors not in factors_to_chord_names and altered_intervals not in intervals_to_chord_names:
                            factors_to_chord_names[altered_factors] = altered_name
                            intervals_to_chord_names[altered_intervals] = altered_name

                            # figure out the rarity of this tweak and add it to the rarity dict:
                            tweak_rarity = tweak_name_rarities[tweak_name]
                            altered_rarity = chord_name_rarities[chord_name] + tweak_rarity
                            new_rarities[altered_rarity].append(altered_name)

                            # finally: do the same again, but one level deeper!
                            for tweak_name2 in ordered_tweak_names:
                                tweak2 = qualities.chord_tweaks[tweak_name] # fetch ChordModifier object by name
                                # do not apply the same tweak twice, and do so only if valid:
                                if (tweak2 is not tweak) and tweak2.valid_on(altered_factors):
                                    if not ((tweak2 in ind_tweaks) and (base_chord.quality.minor)):
                                        # and, special case, not if (no5) is the first tweak, since it always comes last:
                                        if tweak_name != '(no5)':
                                            altered2_name = altered_name + tweak2_name

                                            altered2_factors = altered_factors + tweak2
                                            altered2_intervals = altered2_factors.to_intervals()
                                            # avoid the lower triangular: (e.g. m(no5)add9 vs madd9(no5))
                                            if altered2_factors not in factors_to_chord_names and altered2_intervals not in intervals_to_chord_names:
                                                factors_to_chord_names[altered2_factors] = altered2_name
                                                intervals_to_chord_names[altered2_intervals] = altered2_name

                                                # these are all rarity 7, the 'legendary chords'
                                                new_rarities[max_rarity].append(altered2_name)

# update chord_names_by_rarity with new rarities:
for r, names in new_rarities.items():
    chord_names_by_rarity[r].extend(names)

# re-instantiate the reverse dict since we've added to the forward one (but we still needed it earlier:)
chord_name_rarities = unpack_and_reverse_dict(chord_names_by_rarity)

# reverse these too:
chord_names_to_factors = reverse_dict(factors_to_chord_names)
chord_names_to_intervals = reverse_dict(intervals_to_chord_names)

### pre-initialised major and minor AbstractChords:
MajorTriad = MajorChord = AbstractChord('maj')
MinorTriad = MinorChord = AbstractChord('min')
### and rooted Chords on each tonic:
major_triads = {n: Chord(n.chroma) for n in notes.major_tonics}
minor_triads = {n: Chord(n.chroma + 'm') for n in notes.minor_tonics}

# empty caches to be filled later, by pre-caching and/or dynamic caching:
cached_abstract_chords = {}
cached_chords = {}
cached_consonances_by_suffix = {}

if settings.PRE_CACHE_CHORDS: # initialise common chord objects in cache for faster access later
    # cache abstract chords by name up to a certain rarity:
    cached_abstract_chords.update({(chord_name,None,None,None,None): AbstractChord(chord_name) for chord_name, rarity in chord_name_rarities.items() if rarity <= 1}) # not currently used
    # let the cache point to them by their factors as well:
    cached_abstract_chords.update({(None,c.factors,None,None,None): c for c in cached_abstract_chords.values()})
    cached_abstract_chords[(None, None, (), None, None)] = AbstractChord() # major triad
    cached_abstract_chords[(None, None, (ChordModifier('minor'),), None, None)] = AbstractChord('m') # minor triad

    # cache rooted chords by name up to a certain rarity:
    cached_chords.update({(tonic+chord_name,None,None,None,None,None): Chord(tonic+chord_name) for tonic in parsing.common_note_names for chord_name, rarity in chord_name_rarities.items() if rarity <= 1})
    # and by factors:
    cached_chords.update({(None,c.factors,None,c.root.chroma,None,None): c for c in cached_chords.values()})

    # intonation = tuning.get_intonation()
    # cached_consonances_by_suffix.update({(intonation, ac.suffix): ac.consonance for ac in cached_abstract_chords.values()}) # does this perform a double update if settings.DYNAMIC_CACHING is on?

cache_initialised = True

######################################################


class ChordList(list):
    """container class for multiple Chord objects"""
    def __init__(self, *items):

        # this class contains some lazy imports from the keys and progressions modules,
        # which is untidy as those modules themselves inherit from this module (chords),
        # but since chordlists are inherently tied to progressions, this seems cleanest

        if len(items) == 1:
            arg = items[0]
            if isinstance(arg, str):
                # could be a dash-separated string of chord names or something, try auto-split
                # but first, straighten out all subscripts/superscripts:
                arg_unscript = [c  if c not in parsing.unscript  else parsing.unscript[c]  for c in arg]
                arg_unscript = ''.join(arg_unscript)
                # then auto split, but allow the kinds of symbols that occur in chord names:
                items = parsing.auto_split(arg, allow='°øΔ♯♭♮+𝄫𝄪#/()!?')
            else:
                assert isinstance(arg, (list, tuple)), f"Expected list or tuple of chord-like objects, but got single non-list/tuple arg: {type(arg)}"
                items = arg
        # assert len(items) > 1, "ChordList must contain at least two Chords"

        valid_chords = []
        for c in items:
            # if is chord: add it to list
            if isinstance(c, Chord):
                valid_chords.append(c)
            elif isinstance(c, AbstractChord):
                valid_chords.append(c)
            # if is string: try parsing as chord name
            elif isinstance(c, str):
                if parsing.begins_with_valid_note_name(c):
                    # chord
                    valid_chords.append(Chord.from_cache(c))
                else:
                    valid_chords.append(AbstractChord.from_cache(c))

        # initialise as list:
        super().__init__(valid_chords)

    # outer brackets for this container class:
    _brackets = settings.BRACKETS['ChordList']


    def __str__(self, brackets=True):
        # return f'𝄃{super().__repr__()}𝄂'
        chord_names = [ch.name if ch.__class__.__name__ not in ('ScaleChord', 'KeyChord')
                       else ch.compact_name
                       for ch in self ]
        if brackets:
            lb, rb = self._brackets
        else:
            lb = rb = ''
        sep_char = ' - '
        # if any of the chords in this progression are AbstractChords, use a different sep char
        # (because AbstractChords have spaces in their names)
        for c in self:
            if type(c) == AbstractChord:
                sep_char = ' - '
                break
        return f'{lb}{sep_char.join(chord_names)}{rb}'

    def __repr__(self):
        return str(self)

    def append(self, c):
        """appends an item to self, ensuring it is a Chord or AbstractChord"""
        if isinstance(c, Chord):
            super().append(c)
        elif isinstance(c, AbstractChord):
            super().append(c)
        # if is string: try parsing as chord name
        elif isinstance(c, str):
            if parsing.begins_with_valid_note_name(c):
                # chord
                super().append(Chord.from_cache(c))
            else:
                super().append(AbstractChord.from_cache(c))
        else:
            raise TypeError(f'Tried to append to ChordList, expected Chord or str but got: {type(other)}')

    def __add__(self, other):
        # if other is a str, try and parse it as a chord:
        if isinstance(other, str):
            if parsing.begins_with_valid_note_name(other):
                other = Chord.from_cache(other)
            else:
                other = AbstractChord.from_cache(other)

        # appending a new chord:
        if isinstance(other, Chord):
            new_chords = list(self) + [other]
            return ChordList(new_chords)

        # concatenation of chordlists:
        elif isinstance(other, (tuple, list, ChordList)):
            # if this is a list or tuple, needs to be a list or tuple of chords or strings that cast to chords:
            if type(other) in {tuple, list}:
                other = ChordList(other)
            new_chords = list(self) + list(other)
            return ChordList(new_chords)

        # transpose every chord in this list by an interval:
        elif isinstance(other, (int, Interval)):
            new_chords = [c + int(other) for c in self]
            return ChordList(new_chords)

        else:
            raise TypeError(f'ChordList.__add__ not defined for type: {type(other)}')

    def __sub__(self, other):
        return self + (-other)

    def all_notes(self):
        """returns a NoteList of all the notes that occur in these chords, in order"""
        notes = NoteList()
        for chord in self:
            notes.extend(chord.notes)
        return notes

    def unique_notes(self):
        return self.all_notes().unique()

    def note_counts(self):
        return Counter(self.all_notes())

    def weighted_note_counts(self, weight_factors, ignore_counts=False):
        """given a weight_factors dict that maps chord factors to multiplicative weights,
        return a Counter object of note counts that multiplies the final results
        by those weights.
        if ignore_counts, the Counter accounts only for the MAX weight of each
            note that occurs, instead of a weighted total proportional to occurrence frequency."""

        # fill weights dict with 1s where not defined:
        weight_factors = {f:weight_factors[f] if f in weight_factors else 1 for f in range(1,14)}

        if not ignore_counts:
            # update output by note occurrence frequency
            note_counts = Counter()
            result_dict = note_counts
        else:
            # will just set dict values to the highest observation
            note_maxes = {n:1 for n in self.unique_notes()}
            result_dict = note_maxes

        for chord in self:
            if not ignore_counts:
                # raw note occurence:
                base_count = {n:1 for n in chord.notes}
                # multiplication with factor-weightings in input dict:
                weighted_count = {n: base_count[n] * weight_factors[f] for f,n in chord.factor_notes.items()}
                # update output counter:
                result_dict.update(weighted_count)
            else:
                for f,n in chord.factor_notes.items():
                    observed_weight = weight_factors[f]
                    if result_dict[n] < observed_weight:
                        # update to new max
                        result_dict[n] = observed_weight

        return result_dict


    def abstract(self):
        """returns a new ChordList that is purely the AbstractChords within this existing ChordList"""
        abs_chords = [c.abstract() if (type(c) == Chord)  else c  for c in self]
        assert check_all(abs_chords, 'type_is', AbstractChord)
        return ChordList(abs_chords)

    def rotate(self, N):
        """rotates the chords in this list by N places"""
        rotated_items = rotate_list(list(self), N)
        return ChordList(rotated_items)

    @property
    def roots(self):
        """returns the root notes of the chords in this list, in order"""
        return NoteList([ch.root for ch in self])

    def root_degrees_in(self, key):
        from src.keys import Key
        if isinstance(key, str):
            key = Key(key)
        assert isinstance(key, Key), f"key input to ChordList.root_degrees_in must be a Key or string that casts to Key, but got: {type(key)})"
        root_intervals_from_tonic = [c.root - key.tonic for c in self]
        root_degrees = []
        for iv in root_intervals_from_tonic:
            if iv in key.interval_degrees:
                root_degrees.append(key.interval_degrees[iv])
            else:
                # interpret as fractional degree
                upper_iv, lower_iv = iv+1, iv-1
                if lower_iv in key.interval_degrees:
                    frac_degree = round(int(key.interval_degrees[lower_iv]) + 0.5, 1)
                elif upper_iv in key.interval_degrees:
                    frac_degree = round(int(key.interval_degrees[upper_iv]) - 0.5, 1)
                else:
                    frac_degree = None
                root_degrees.append(frac_degree)
        # root_degrees = [key.interval_degrees[iv]  if iv in key.interval_degrees  else None for iv in root_intervals_from_tonic]
        return root_degrees

    def as_numerals_in(self, key, sep=' ', modifiers=True, marks=False, diacritics=False, *args, **kwargs):
        """returns this ChordList's representation in roman numeral form
        with respect to a desired Key"""
        from src.keys import Key
        if not isinstance(key, Key):
            key = Key(key)

        root_degrees = self.root_degrees_in(key)
        scale_chords = [ch.in_scale(key.scale, degree=root_degrees[i]) for i,ch in enumerate(self)]

        numerals = [ch.get_numeral(modifiers=modifiers, marks=marks, diacritics=diacritics, *args, **kwargs) for ch in scale_chords]

        if sep is not None:
            roman_chords_str = sep.join(numerals)
            return roman_chords_str
        else:
            # just return the raw list, instead of a sep-connected string
            return numerals

    @property
    def progression(self):
        from src.progressions import ChordProgression
        return ChordProgression(self)

    def matching_keys(self, *args, **kwargs):
        """just a wrapper around keys.matching_keys of this ChordList"""
        from src.matching import matching_keys
        return matching_keys(chords=self, *args, **kwargs)

    def play(self, chord_delay=1, note_delay=0, duration=2.5, octave=None, falloff=True, block=False, type='fast', **kwargs):
        """play this chordlist as audio"""
        chord_waves = [c._melody_wave(duration=duration, delay=note_delay, octave=octave, type=type, **kwargs) for c in self]
        from .audio import arrange_melody, play_wave, play_melody
        play_melody(chord_waves, delay=chord_delay, falloff=falloff, block=block)
        # prog_wave = arrange_melody(chord_waves, delay=delay, **kwargs)
        # play_wave(prog_wave, block=block)

    @property
    def fretboard(self):
        """wrapper around Guitar.standard.show_chord for each chord in this list"""
        from . import guitar
        for ch in self:
            guitar.standard.show_chord(ch)
    diagram = fretboard # convenience alias

    def show(self, tuning='EADGBE', **kwargs):
        """displays these chords on a guitar in specified tuning"""
        from . import guitar
        if tuning == 'EADGBE':
            g = guitar.standard
        else:
            g = guitar.Guitar(tuning=tuning)
        for ch in self:
            g.show_chord(ch, **kwargs)
    on_guitar = show

# convenience alias:
Chords = ChordList



def most_likely_chord(note_list, stats=False, **kwargs):
    """from an unordered set of notes, return the single most likely chord,
    within specified constraints, as a tuple of (Chord, match_params)"""

    # by default, relax all minimum score constraints (to ensure we get something rather than nothing)
    # but allow overwriting by kwarg
    from .matching import fuzzy_matching_chords

    for kwarg in ['min_precision', 'min_recall', 'min_likelihood']:
        if kwarg not in kwargs:
            kwargs[kwarg] = 0.0
    candidates = fuzzy_matching_chords(note_list, return_scores=True, display=False, **kwargs)
    if len(candidates) > 0:
        best_match = list(candidates.keys())[0]
        match_params = candidates[best_match]
    else:
        best_match = match_params = None

    if stats:
        return best_match, match_params
    else:
        return best_match



### WIP, incomplete class
class ChordVoicing(Chord):
    """a Chord built on a specific note of a specific pitch, whose members are OctaveNotes.
    unlike its parent classes, a ChordVoicing can have repeats of the same Note at multiple pitches.

    exact same attributes as chord, except also having a self.octave attribute defined"""
    def __init__(self, name=None, root=None, octave=None, factors=None, intervals=None, inversion=None, modifiers=None, in_key=None):

        self.root, self.octave, chord_name = self._parse_root_octave(name, root, octave)

        self.factors, self.intervals, self.inversion = self._parse_input(chord_name, factors, intervals, inversion, inversion_degree, modifiers)

        ### TBI: everything else

    @staticmethod
    def _parse_root_octave(name, root, octave):
        """takes the class's name and root input args
        and returns an OctaveNote object as root, integer as octave,
        and string or None object as chord_name"""
        # parse root and octave:
        if name is not None:
            assert root is None, f"ChordVoicing initialised with name string ({name}) as root, but also received mutually exclusive root keyword: {root}"
            assert octave is not None, f"ChordVoicing initialised with name string ({name}) as root but no octave arg provided"
            root_name, chord_name = parsing.note_split(name)
            root = Note.from_cache(root_name)
            if len(chord_name) == 0:
                chord_name = None
            return root, octave, chord_name
        else:
            if isinstance(root, OctaveNote):
                # if root is an OctaveNote, we accept that:
                root = root
                assert octave is None, f"ChordVoicing initialised with OctaveNote ({root}) as root but also received mutually exclusive octave keyword: {octave}"
                octave = root.octave
            elif isinstance(root, Note):
                assert octave is not None, f"ChordVoicing initialised with Note ({root}) as root but no octave arg provided"
                root = root.in_octave(octave)
                octave = octave
            elif isinstance(root, str):
                if root[-1].isnumeric():
                    # string that seems to be an OctaveNote
                    assert octave is None, f"ChordVoicing initialised with string denoting OctaveNote ({root}) but also received mutually exclusive octave keyword: {octave}"
                    root = OctaveNote(root)
                    octave = root.octave
                else:
                    assert octave is not None, f"ChordVoicing initialised with Note string ({root}) as root but no octave arg provided"
                    octave = octave
                    root = Note.from_cache(root).in_octave(octave)
            return root, octave, name
