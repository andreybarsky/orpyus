### classes and methods for matching chords, scales, and keys.
### from partial sets or sequences of intervals, notes or chords

from .chords import *
from .scales import *
from .keys import *
from .progressions import *
from .qualities import Major, Minor

from dataclasses import dataclass

# tonal quality distributions for major and minor tonalities:
major_qualdist = {0: 10, 1: -4,  2: 7,  3: -5,  4: 7,  5: 8,  6: -1,
                  7:  9,  8: 0,  9: 5,  10: 0,  11: 5,}
minor_qualdist = {0: 10, 1: -3,  2: 6,  3: 7,  4: -9,  5: 8,  6: -2,
                  7:  7,  8: 5,  9: 0,  10: 5,  11: 0,}
                # or whatever

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
        """compute dot product with intervals and return score
        proportional to how those intervals match this tonality."""
        return sum(self * weighted_ivs)

    def __mul__(self, weighted_ivs: dict[Interval, float]):
        """compute pairwise product with intervals and the scores at each point."""
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
    for qualdist in major_qualdist, minor_qualdist:
        # take dot product of qualdist and (weighted) input intervals
        scores.append(sum([prior * weighted_ivs[iv]
                           if iv in weighted_ivs else 0
                           for iv, prior in qualdist.items()]))
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
        prefer_sharps = _settings.DEFAULT_SHARPS
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
