### classes and methods for matching chords, scales, and keys.
### from partial sets or sequences of intervals, notes or chords

from .chords import *
from .scales import *
from .keys import *
from .progressions import *
from .qualities import Major, Minor
from .config import settings

from dataclasses import dataclass

# tonal quality distributions for major and minor tonalities:
major_qualdist = {0: 10,
                  1: -6,
                  2:  3,
                  3: -4,
                  4:  9,
                  5:  6,
                  6:  -1,
                  7:  7,
                  8:  0,
                  9:  2,
                  10: 0,
                  11: 2,}
minor_qualdist = {0: 10,
                  1: -4,
                  2:  3,
                  3:  8,
                  4: -2,
                  5:  5,
                  6: -1,
                  7:  6,
                  8:  2,
                  9:  0,
                  10: 2,
                  11: 0,}
                # or whatever

# specific scales to search once we have established a tonality:
major_scales = [NaturalMajor, HarmonicMajor, MelodicMajor,
                Mixolydian, Lydian, BluesMajor]

minor_scales = [NaturalMinor, HarmonicMinor, MelodicMinor,
                Dorian, Phrygian, BluesMinor,
                NeapolitanMinor, NeapolitanMajor, DoubleHarmonic]

@dataclass
class Tonality:
    tonic: Note
    quality: Quality

    @property
    def distribution(self):
        if self.quality.major:
            return major_qualdist
        elif self.quality.minor:
            return minor_qualdist
        else:
            raise Exception('Tonality should be either major or minor')

    def __truediv__(self, weighted_ivs: dict[Interval, float]):
        """ '/' operator: compute dot product with intervals and return score
        proportional to how those intervals match this tonality."""
        return sum(self * weighted_ivs)

    def __mul__(self, weighted_ivs: dict[Interval, float]):
        """ '*' operator: compute pairwise product with intervals and the scores
        at each point."""
        return [prior * weighted_ivs[iv]
                    if iv in weighted_ivs else 0
                    for iv, prior in self.distribution.items()]

    def __repr__(self):
        lb, rb = self.quality._brackets
        return f'{lb}Tonality: {self.tonic} {self.quality.full_name}{rb}'

    # we use Tonality as a dict key in places:
    def __hash__(self):
        return hash((self.tonic, self.quality))

def match_qualdist_to_intervals(ivs: IntervalList, weight_counts=True,
                                return_scores=False, verbose=True):
    """accepts a set of intervals with respect to some implicit tonic,
    and returns match stats for major and minor tonalities.

    input can either be an IntervalList, or a dict that keys Intervals to
        arbitrary float weights.
    if input is an IntervalList and weight_counts is True, will automatically
        weight intervals according to their occurrence frequency.
        otherwise, all intervals are weighted equally.
    if return_scores is True, returns the major and minor scores respectively.
        otherwise, return the Quality itself."""
    if isinstance(ivs, dict):
        weighted_ivs = ivs
        # is already a dict of intervals to weights
    else:
        # we will turn this into such a dict.
        # first, cast to IntervalList if not already one:
        if not isinstance(ivs, IntervalList):
            ivs = IntervalList(ivs)

        # ensure intervals are flattened to 0-12 range:
        if max(ivs) >= 12:
            ivs = ivs.flatten(duplicates=True)

        # weight by occurrence frequency if desired:
        if weight_counts:
            weighted_ivs = Counter(ivs)
        else:
            weighted_ivs = {iv: 1 for iv in ivs}

    # now: ivs is a dict of intervals to weights
    # so we can now iterate through each qualdist to check for matches:
    scores = []
    for qualname, qualdist in zip(['major', 'minor'], [major_qualdist, minor_qualdist]):
        # take dot product of qualdist and (weighted) input intervals
        weighted = [prior * weighted_ivs[iv]
                           if iv in weighted_ivs else 0
                           for iv, prior in qualdist.items()]
        if verbose:
            print(f'{qualname}: {list(enumerate(weighted))}')
        scores.append(sum(weighted))
    major_score, minor_score = scores
    if verbose:
        print(f'{major_score=}')
        print(f'{minor_score=}')
    if return_scores:
        return major_score, minor_score
    else:
        # return a Quality object
        if major_score >= minor_score:
            return Major
        else:
            return Minor



def notes_tonality(notes: NoteList):
    """accepts a set of notes, either as a NoteList (unweighted)
        or as a dict keying Notes to arbitrary float weightings.
    tries to find a tonality and tonic note that matches those notes,
        with higher-weighted notes having more impact on the final result.

    if input is a bare NoteList, and weight_counts is True, will weight
        the notes according to how often they occur in the list."""
    if isinstance(notes, dict):
        weighted_notes = notes
        # is already a dict of notesto weights
    else:
        # we will turn this into such a dict.
        # first, cast to NoteList if not already one:
        if not isinstance(notes, NoteList):
            notes = NoteList(notes)

        # weight by occurrence frequency if desired:
        if weight_counts:
            weighted_notes = Counter(notes)
        else:
            weighted_notes = {note: 1 for note in notes}

    # use all notes in the input as possible tonics:
    candidate_tonics = list(weighted_notes.keys())
    tonality_scores = {}
    for tonic in candidate_tonics:
        # input notes with respect to that tonic:
        weighted_intervals = {(note - tonic): weight for note, weight in weighted_notes.items()}
        for quality in Major, Minor:
            tonality = Tonality(tonic, quality)
            score = tonality / weighted_intervals
            tonality_scores[tonality] = score

    ranked_tonalities = sorted(tonality_scores.keys(), key=lambda t: -tonality_scores[t])
    ranked_scores = {t: tonality_scores[t] for t in ranked_tonalities}
    return ranked_scores


def chords_tonality(chords, chord_factor_weights = {1: 2, 3: 1.5}, weight_counts=True):
    """accepts a ChordList and returns a ranked list of matching tonalities"""
    if isinstance(chords, ChordProgression):
        # get chordlist from a chordprogression:
        chords = chords.chords
    weighted_notes = chords.weighted_note_counts(chord_factor_weights, ignore_counts=(not weight_counts))
    return notes_tonality(weighted_notes)

### SCALE MATCHING


def matching_scales(chords=None, intervals=None,
                    min_recall = 0.85, min_precision=0.0,
                    max_results=None, display=True, **kwargs):

    # uses tonality matching logic in loop over possible tonics

    if isinstance(chords, IntervalList):
        # quietly reparse intervals that are (mistakenly) passed as first input
        intervals = chords
        chords = None

    if chords is not None:
        if isinstance(chords, str):
            # assume a string of roman numerals:
            split_numerals = auto_split(chords)
            roman = True
        elif isinstance(chords[0], str):
            # assume a list of roman numerals
            split_numerals = chords
            roman = True
        else:
            # assume degree, chord pairs
            assert len(chords[0]) == 2, "expected input to matching_scales to be roman numerals or list of (degree, abs_chord) pairs"
            roman = False

        if roman:
            degrees, abs_chords = [], []
            for num in split_numerals:
                rn = RomanNumeral(num)
                deg, ch = rn.degree, rn.chord
                degrees.append(deg)
                abs_chords.append(ch)
        else:
            degrees = [d for d,ch in chords]
            abs_chords = [ch for d,ch in chords]


def old_matching_scales(chords=None, intervals=None, major_roots=None, min_recall=0.85, min_precision=0.0,
                    candidate_scales = [MajorScale, MinorScale,
                                        HarmonicMinor, MelodicMinor, ExtendedMinor, FullMinor,
                                        HarmonicMajor, MelodicMajor, ExtendedMajor, FullMajor,
                                        Lydian, Mixolydian, # note! these are the scales corresponding to adjacent major keys on the circle of fifths
                                        Dorian, Phrygian, # and these correspond to adjacent Co5 scales for minor keys
                                        Locrian],  # just for completeness although it will rarely turn up in practice
                    filter_redundancies = True,
                    max_results=None, display=True, **kwargs):
    """accepts either:
          chords: a list of roman numeral chords, e.g. ["i", "V7", "VII"]
                   or a string of the same, with clear separators, e.g.: "i - V7 - VII"
                or a list of degree-chord pairs, of the form: [(root degree, AbstractChord), etc.]
            or
          intervals: an IntervalList (or object that casts to IntervalList)
       and returns a list of matching Scales based on which intervals/factors correspond to those chords
    if major_roots is True, interpret chords like III and VII as being rooted on their major intervals
        (i.e. the major 3rd and major 7th), unless specified bIII and bVII etc.
    if major_roots is False, interpret those chords as rooted on their minor intervals,
        (i.e. the minor 3rd and 7th), unless specified #III and #VII.
    if major_roots is None, we make a best guess - use the tonic's quality if there, or
        assume major if not otherwise specified.

    if filter_redundant is True, avoids displaying extended/full scales if their base form
        is a better fit for the input intervals."""

    # keep in mind: a raised 7th (Interval(11)) is usually more indicative of
    # harmonic minor than it is of natural major, at least melodically

    # check if first arg is an intervallist, in which case silently correct and treat it as one:
    if isinstance(chords, IntervalList):
        intervals = chords
        chords = None

    if chords is not None:
        if isinstance(chords, str):
            # assume a string of roman numerals:
            split_numerals = auto_split(chords)
            roman = True
        elif isinstance(chords[0], str):
            # assume a list of roman numerals
            split_numerals = chords
            roman = True
        else:
            # assume degree, chord pairs
            assert len(chords[0]) == 2, "expected input to matching_scales to be roman numerals or list of (degree, abs_chord) pairs"
            roman = False

        if roman:
            degrees, abs_chords = [], []
            for num in split_numerals:
                rn = RomanNumeral(num)
                deg, ch = rn.degree, rn.chord
                degrees.append(deg)
                abs_chords.append(ch)
        else:
            degrees = [d for d,ch in chords]
            abs_chords = [ch for d,ch in chords]

        # determine if numeral degrees are relative to major or minor scale:
        if roman and (major_roots is None):
            # if any roots are flattened (e.g. bIII), we assume that those flats are relative to major scale:
            contains_flats = True in [parsing.contains_flat(num) for num in split_numerals]
            if contains_flats:
                major_roots = True
        if major_roots is None:
            # otherwise, try and guess from tonic if present:
            if 1 in degrees:
                which_1 = [i for i,d in enumerate(degrees) if d==1][0]
                tonic_chord = abs_chords[which_1]
                major_roots = not tonic_chord.quality.minor_ish # assume major for maj/aug/ind tonic chords
            else:
                major_roots = True # assume major since not otherwise specified

        if display: # expensively work out roman numerals of those pairs for table output
            root_scale = MajorScale if major_roots else MinorScale
            # ensure split numerals have proper superscripts etc. even if roman chords were given:
            # split_numerals = [ch.in_scale(root_scale, degree=d).mod_numeral for d,ch in zip(degrees, abs_chords)]
            scale_chords = [ch.in_scale(root_scale, degree=d) for d,ch in zip(degrees, abs_chords)]
            simple_numerals = [sch.simple_numeral for sch in scale_chords]
            mod_numerals = [sch.mod_numeral for sch in scale_chords]

        # determine intervals to match against
        # how far does each chord start from the scale tonic:
        if major_roots:
            root_intervals_from_tonic = [MajorScale._get_arbitrary_degree_interval(d) for d in degrees]
            minor_assumed = False
        else:
            root_intervals_from_tonic = [MinorScale._get_arbitrary_degree_interval(d) for d in degrees]
            minor_assumed = (3 in degrees or 6 in degrees or 7 in degrees)
        # how far is each note in each chord from the scale tonic:
        all_intervals_from_tonic = IntervalList()
        for ch, root_iv in zip(abs_chords, root_intervals_from_tonic):
            chord_intervals_from_tonic = ch.intervals + root_iv
            all_intervals_from_tonic.extend(chord_intervals_from_tonic.flatten())

        unique_intervals_from_tonic = IntervalList(all_intervals_from_tonic.flatten().unique())

    elif intervals is not None:
        # cast to IntervalList object if needed:
        intervals = IntervalList(intervals) if not isinstance(intervals, IntervalList) else intervals
        unique_intervals_from_tonic = intervals.unique()


    # main matching loop
    import numpy as np
    candidate_interval_grid = np.zeros((len(candidate_scales), 12))
    for i, cand in enumerate(candidate_scales):
        grid_row = [1  if i in cand else 0  for i in range(12) ]
        candidate_interval_grid[i] = grid_row
    input_intervals_set = unique_intervals_from_tonic
    input_interval_row = np.asarray([1  if i in input_intervals_set else 0  for i in range(12) ])

    perfect_matches = []
    candidate_scores = {}
    for i, cand in enumerate(candidate_scales):
        cand_interval_row = candidate_interval_grid[i]
        difference = cand_interval_row - input_interval_row
        # here 0s are matches, 1s are where input not in candidate, -1s are mismatches
        # or to put another way: (0,-1) are retrieved, (0) are relevant
        mismatches  = sum([d == -1 for d in difference])
        # a 'perfect' match can be partial, it simply has no mismatches:
        if mismatches == 0:
            perfect_matches.append(cand)
        # scores:
        matches = sum([d == 0 for d in difference])
        spares = sum([d == 1 for d in difference])
        num_retrieved = matches + spares
        num_relevant = matches
        rec, prec = precision_recall_scores(num_retrieved, num_relevant, 12, 12)
        # somewhere these became backwards relative to matching_keys etc...
        score = {'precision': round(prec,3), 'recall': round(rec,3)}
        candidate_scores[cand] = score

    # filter out extensions that are less precise than their bases
    if filter_redundancies:
        redundant_scales = []
        for base_scale, ext_scale in scale_extensions.items():
            # (i.e. no need for extended minor if natural minor is a perfect fit,
            # and likewise no need for full minor if extended minor is a perfect fit)
            ### TBI: could this be generalised with Scale.is_subset type methods instead of hardcoding?
            if base_scale in candidate_scores and ext_scale in candidate_scores:
                base_prec, ext_prec = candidate_scores[base_scale]['precision'], candidate_scores[ext_scale]['precision']
                if base_prec >= ext_prec:
                    redundant_scales.append(ext_scale)
        candidate_scores = {cand:score for cand,score in candidate_scores.items()
                            if cand not in redundant_scales}


    # filter scores by minimum precision:
    if min_recall > 0 or min_precision > 0:
        candidate_scores = {cand:score for cand,score in candidate_scores.items()
                            if score['recall'] >= min_recall
                            and score['precision'] >= min_precision}

    sorted_cands = sorted(candidate_scores.keys(),
                          key=lambda x: (-candidate_scores[x]['recall'],
                                         -candidate_scores[x]['precision']))
    sorted_scores = {cand:candidate_scores[cand] for cand in sorted_cands}

    # return matches and scores
    if not display:
        return {cand: candidate_scores[cand] for cand in sorted_cands}
    else:
        from src.display import DataFrame


        ilb, irb = settings.BRACKETS['IntervalList']
        out = settings.DIACRITICS['interval_not_in_input']

        # title: (including its own table for chords themselves)
        input_factors_str = ' '.join(unique_intervals_from_tonic.as_factors)


        if chords is not None:
            title = (f'Matching scales for chords: {"-".join(mod_numerals)}  (scale factors: {input_factors_str})')
            ### root intervals of each chord:
            chords_df = DataFrame(['Degree', 'Numeral', '', 'Intervals from root', ''])
            for ch, root_iv, num in zip(abs_chords, root_intervals_from_tonic, simple_numerals):
                flat_intervals_from_tonic = (ch.intervals + root_iv).flatten(sort=False).as_factors
                flat_intervals_str = ' '.join([f'{fiv:<2}' for fiv in flat_intervals_from_tonic])
                chords_df.append([num, ch.short_name, ilb[0], flat_intervals_str, irb])
            chords_df.show(header=False, header_char='-', title=title)
            if (not major_roots) and (minor_assumed):
                print(f'(assuming root degrees are relative to minor scale)')
            print('') # newline

        elif intervals is not None:
            print(f'Matching scales for intervals: {intervals}')

        # matches:


        df = DataFrame(['Scale', ''] + ['']*12   + # one column per possible semitone
                       ['', 'Miss.', '', 'Rec.', 'Prec.',
                        'Likl.', 'Cons.'])
        for cand, score in sorted_scores.items():
            prec, rec = score['precision'], score['recall']
            lik, cons = cand.likelihood, cand.consonance

            # work out which interval factors go in which column:
            semitone_ivs = [Interval(v) if v in cand.intervals else None for v in range(12)]
            factor_ivs = [f'{iv.factor_name:>2}' if iv is not None else f' .' for iv in semitone_ivs]

            # but mark the factors that aren't in the input:
            cand_iv_in_input =  [(iv in unique_intervals_from_tonic or iv is None) for iv in semitone_ivs]
            factor_ivs_marked = [fiv if cand_iv_in_input[i]    # don't underline in-input ivs
                                 else fiv + out
                                  for i,fiv in enumerate(factor_ivs)]

            missing_ivs = [iv for iv in unique_intervals_from_tonic if iv not in cand.intervals]
            missing_ivs_str = ','.join([f'{iv.factor_name:>2}' for iv in missing_ivs]) if len(missing_ivs) > 0 else ''

            df_row = [f'{cand._marker} {cand.name:<}', ilb[0]] + factor_ivs_marked + [irb, missing_ivs_str, ' ',
                                                                     f'{rec:.2f}', f'{prec:.2f}',
                                                                     f'{lik:.2f}', f'{cons:.3f}']

            df.append(df_row)
        df.show(max_rows=max_results, margin=' ', **kwargs)



### CHORD MATCHING

######### function for matching likely chords from unordered lists of note names (e.g. guitar fingerings)
# we cannot use intervals for this, because notes being in an arbitrary order means that
# their relative intervals are much less informative ,so we really must initialise every imaginable chord

def matching_chords(notes, display=True, return_scores=False,
                    invert=False, exact=False,
                    search_no5s=True,
                    min_recall=0.9, min_precision=0.85,
                    min_likelihood=0.5, min_consonance=0.35,
                    allow_fuzzy=True, size_cutoff=5,
                    whitelist=None, blacklist=None,
                    max_results=10, **kwargs):
    # re-cast input:
    if not isinstance(notes, NoteList):
        notes = NoteList(notes)

    # for chords with 5(?) notes or less, we can efficiently search all their permutations:
    if len(notes) <= size_cutoff:
        note_permutations = [NoteList(ns) for ns in itertools.permutations(notes)]
        interval_permutations = [nl.ascending_intervals() for nl in note_permutations]
    else:
        # # otherwise we'll search only the inversions instead of all permutations
        # #  which is faster but less complete:
        # note_permutations = [notes.rotate(i) for i in range(len(notes))]
        # interval_permutations = {notes[i]: note_permutations[i].ascending_intervals() for i in range(len(notes))}
        print(f'{len(notes)} is too many for exact permutation searching')
        if not exact:
            print(f'So falling back on fuzzy matching')
            if 'require_root' not in kwargs:
                kwargs['require_root'] = invert
            return fuzzy_matching_chords(notes, display=display, invert=invert, assume_root=invert, # require_root=invert,
                                         min_likelihood=min_likelihood, max_results=max_results, **kwargs)
        else:
            raise Exception(f'Set exact=False for notelists exceeding size_cutoff, or set size_cutoff higher than {size_cutoff}')


    candidate_names = []
    for notes_p, intervals_p in zip(note_permutations, interval_permutations):
        root = notes_p[0]
        if intervals_p in intervals_to_chord_names:
            candidate_names.append(f'{root.name}{intervals_to_chord_names[intervals_p]}')
        elif (search_no5s) and (P5 not in intervals_p):
            # this potential candidate lacks a 5, would it fit a named chord if it had one?
            added5_intervals = IntervalList(intervals_p)
            added5_intervals.append(P5)
            added5_intervals = added5_intervals.sorted()
            if added5_intervals in intervals_to_chord_names:
                candidate_names.append(f'{root.name}{intervals_to_chord_names[added5_intervals]}(no5)')

    if invert:
        note_list_root = notes[0]
        candidate_chords = [Chord(cn, bass=note_list_root) for cn in candidate_names]
    else:
        candidate_chords = [Chord.from_cache(cn) for cn in candidate_names]

    # filter chords by likelihood, consonance, and blacklist/whitelist
    if whitelist is None:
        whitelist_factors = []
    else:
        whitelist_factors = [AbstractChord(w).factors if type(w) is not AbstractChord else w.factors for w in whitelist]
    if blacklist is None:
        blacklist_factors = []
    else:
        blacklist_factors = [AbstractChord(b).factors if type(b) is not AbstractChord else b.factors for b in blacklist]

    filtered_chords = [ch for ch in candidate_chords
                        if (ch.likelihood >= min_likelihood
                            and ch.consonance >= min_consonance
                            and ch.factors not in blacklist_factors)
                        or ch.factors in whitelist_factors]

    sorted_cands = sorted(filtered_chords,
                          key=lambda c: (c.likelihood,
                                         c.consonance),
                          reverse=True)[:max_results]

    if len(sorted_cands) == 0:
        if not exact:
            print(f'No exact chord matches found for notes: {notes}')
            print(f'So falling back on fuzzy matching')
            return fuzzy_matching_chords(notes, display=display, invert=invert, assume_root=invert, require_root=invert,
                                         min_likelihood=min_likelihood, whitelist=whitelist, blacklist=blacklist,
                                         max_results=max_results, **kwargs)
        else:
            # return or display the zero exact matches we have
            pass

    # otherwise, we have found at least one perfect match, so display the results:
    if display:
        from src.display import DataFrame
        # print result as nice dataframe instead of returning a dict
        title = [f"Chord matches for notes: {notes}"]
        title = ' '.join(title)
        print(title)

        df = DataFrame(['Chord', '', 'Notes', '', 'Rec.', 'Prec.', 'Likl.', 'Cons.'])
        for cand in sorted_cands:
            # scores = candidate_chords[cand]
            lik, cons = cand.likelihood, cand.consonance
            # take right bracket off the notelist and add it as its own column:
            lb, rb = cand.notes._brackets
            # use chord.__repr__ method to preserve dots over notes: (and strip out note markers)
            notes_str = (f'{cand.__repr__()}'.split(rb)[0]).split(lb)[-1].replace(Note._marker, '')
            df.append([f'{cand._marker} {cand.name}', lb, notes_str, rb, 1.0, 1.0, f'{lik:.2f}', f'{cons:.3f}'])
        df.show(max_rows=max_results, margin=' ', **kwargs)

    elif return_scores:
        scored_cands = {c: (c.likelihood, c.consonance) for c in sorted_cands}
        return scored_cands

    else:
        # neither scores or display, just return bare list
        return sorted_cands

# old/deprecated function, but still useful if no exact matches for chords are found:
def fuzzy_matching_chords(note_list, display=True,
                    assume_root=False, require_root=False, invert=False,
                    upweight_third=True, downweight_fifth=True,
                    min_recall=0.8, min_precision=0.7, min_likelihood=0.5, min_consonance=0.25,
                    whitelist=None, blacklist=None, # overrides likl/cons filters, but not rec/prec filters
                    max_results=8, **kwargs):
    """from an unordered set of notes, return a dict of candidate chords that could match those notes.
    we make no assumptions about the note list, except in the case of assume_root, where we slightly
    privilege chords that have their root on the same note as the starting note in note_list.
    alternatively, if invert is True, we invert candidate chords to match the note_list's starting note.

    if weight_third, we place more emphasis on the candidate chords' third degrees for prec/recall statistics."""
    try:
        note_list = NoteList(note_list)
    except Exception as e:
        print(f'{note_list} does not appear to be a valid list of notes')
        raise e

    # determine whether to prefer sharps or flats:
    input_sharps, input_flats = 0,0
    for n in note_list:
        if parsing.is_flat(n.chroma[-1]):
            input_flats += 1
        elif parsing.is_sharp(n.chroma[-1]):
            input_sharps += 1
    if input_sharps == input_flats:
        # tiebreak on global default:
        prefer_sharps = settings.DEFAULT_SHARPS
        log(f'Decided to prefer sharps: {prefer_sharps}')
    else:
        prefer_sharps = input_sharps > input_flats
        log(f'Decided to prefer sharps: {prefer_sharps}')

    # filter chords by likelihood, consonance, and blacklist/whitelist; figure out those filtering factors here
    if whitelist is None:
        whitelist_factors = []
    else:
        whitelist_factors = [AbstractChord(w).factors if type(w) is not AbstractChord else w.factors for w in whitelist]
    if blacklist is None:
        blacklist_factors = []
    else:
        blacklist_factors = [AbstractChord(b).factors if type(b) is not AbstractChord else b.factors for b in blacklist]

    candidates = {} # we'll build a list of Chord object candidates as we go
    # keying candidate chord objs to (rec, prec, likelihood, consonance) tuples

    # we'll try building notes starting on every unique note in the note_list
    # (this implicitly means that we require the tonic to be in the input, which is fine)
    unique_notes = note_list.unique()

    for n in unique_notes:
        for rarity, chord_names in chord_names_by_rarity.items():

            # (no5) is already a missing degree, so we don't search chords that include it:
            # names_to_try = [n for n in chord_names if '(no5)' not in n]
            names_to_try = chord_names

            for chord_name in names_to_try:
                # init chord more efficiently than by name:
                cand_factors = chord_names_to_factors[chord_name]
                candidate = Chord(factors=cand_factors, root=n, prefer_sharps=prefer_sharps)

                likelihood = candidate.likelihood # float from 0.3 to 1.0

                # if candidate doesn't share the 'root', we can invert it:
                if (candidate.root != note_list[0]):
                    if invert and (note_list[0] in candidate.notes):
                        candidate = candidate.invert(bass=note_list[0])
                        # or otherwise just assume the note_list's root and make the non-inversion slightly less likely:
                    elif assume_root:
                        likelihood -= 0.15 # increase rarity by one-and-a-half steps

                weights = {}
                # upweight the third if asked for:
                if (upweight_third) and (3 in candidate.factors):
                    weights[candidate.factor_notes[3]] = 2
                # only downweight perfect fifths:
                if (downweight_fifth) and (5 in candidate.factors) and (candidate.factor_intervals[5]==7):
                    weights[candidate.factor_notes[5]] = 0.5
                # if require root, we only accept chords that share the bass note with the note_list:
                if (not require_root) or (candidate.bass == note_list[0]):
                    scores = precision_recall(unique_notes, candidate.notes, weights=weights)
                    precision, recall = scores['precision'], scores['recall']
                    consonance = candidate.consonance # float from ~0.4 to ~0.9, in principle

                    if recall >= min_recall and precision >= min_precision:
                        if (likelihood >= min_likelihood and consonance >= min_consonance) or (candidate.factors in whitelist_factors):
                            if candidate.factors not in blacklist_factors:
                                candidates[candidate] = {   'recall': round(recall,    2),
                                                         'precision': round(precision, 2),
                                                        'likelihood': round(likelihood,2),
                                                        'consonance': round(consonance,3)}

    # return sorted candidates dict:
    sorted_cands = sorted(candidates,
                          key=lambda c: (candidates[c]['recall'],
                                         candidates[c]['precision'],
                                         candidates[c]['likelihood'],
                                         candidates[c]['consonance']),
                          reverse=True)[:max_results]

    if display:
        from src.display import DataFrame
        # print result as nice dataframe instead of returning a dict
        title = [f"Chord matches for notes: {note_list}"]
        if assume_root:
            title.append(f'(assumed root: {note_list[0].name})')
        if not invert:
            title.append('(implicit inversions)')
        else:
            title.append('(explicit inversions)')
        title = ' '.join(title)
        print(title)

        df = DataFrame(['Chord', '', 'Notes', '', 'Rec.', 'Prec.', 'Likl.', 'Cons.'])
        for cand in sorted_cands:
            scores = candidates[cand]
            rec, prec, lik, cons = list(scores.values())
            # take right bracket off the notelist and add it as its own column:
            lb, rb = cand.notes._brackets
            # use chord.__repr__ method to preserve dots over notes: (and strip out note marker)
            notes_str = (f'{cand.__repr__()}'.split(rb)[0]).split(lb)[-1].replace(Note._marker, '')
            df.append([f'{cand._marker} {cand.name}', lb, notes_str, rb, rec, prec, lik, cons])
        df.show(max_rows=max_results, margin=' ', **kwargs)
        return

    else:
        return {c: candidates[c] for c in sorted_cands}
