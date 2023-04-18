from intervals import Interval, IntervalList
from notes import Note, NoteList, sharp_major_tonics, sharp_minor_tonics, flat_major_tonics, flat_minor_tonics, relative_majors, relative_minors
from scales import Scale, Subscale, interval_mode_names
from chords import Chord, AbstractChord
import parsing
from util import check_all, precision_recall, test, log

from collections import Counter
import pdb

# natural notes in order of which are flattened/sharpened in a key signature:
flat_order = ['B', 'E', 'A', 'D', 'G', 'C', 'F']
sharp_order = ['F', 'C', 'G', 'D', 'A', 'E', 'B']

class Key(Scale):
    """a Scale that is also rooted on a tonic, and therefore associated with a set of notes"""
    def __init__(self, scale_name=None, intervals=None, tonic=None, notes=None, mode=1, chromatic_intervals=None, stacked=True):
        """Initialised in one of three ways:

        1. from 'notes' arg, as a list or string of Notes or Note-like objects,
        in which case we parse the tonic and intervals from there

        2. from 'scale_name' arg, when as a proper Key name (like "C#" or "Bb harmonic minor" or "Gbb lydian b5"),
            in which case we extract the tonic note from the string and initialise the rest as with Scale class.

        3. from 'tonic' arg, as a Note or string that casts to Note,
            in combination with any other args that would initialise a valid Scale object.
            i.e. one of 'scale_name' or 'intervals'."""

        # if notes have been provided, parse them into tonic and intervals:
        if notes is not None:
            # ignore intervals/factors/root inputs
            assert tonic is None and intervals is None and scale_name is None
            note_list = NoteList(notes)
            assert len(note_list) == 7, f"a Key must have exactly 7 notes, but there are {len(note_list)} in: {note_list}"
            # recover intervals and tonic, and continue to init as normal:
            intervals = NoteList(notes).ascending_intervals()
            tonic = note_list[0]

        # get correct tonic and scale name from (key_name, tonic) input args:
        self.tonic, scale_name = self._parse_tonic(scale_name, tonic)

        # initialise everything else as Scale class does:
        super().__init__(scale_name, intervals, mode, chromatic_intervals, stacked)
        # (this sets self.base_scale, .quality, .intervals, .diatonic_intervals, .chromatic_intervals, .rotation)

        # set Key-specific attributes: notes, degree_notes, etc.
        self.notes = NoteList([self.tonic] + [self.tonic + i for i in self.diatonic_intervals])

        # we don't store the unison interval in .interval attr, because of mode rotation
        padded_intervals = [Interval(0)] + self.diatonic_intervals
        self.note_intervals = {self.notes[i]: padded_intervals[i] for i in range(7)}
        self.interval_notes = {padded_intervals[i]: self.notes[i] for i in range(7)}

        self.degree_notes = {d: self.notes[d-1] for d in range(1,8)}
        self.note_degrees = {self.notes[d-1]: d for d in range(1,8)}

        # used only for Keys with strange chromatic notes not built on integer degrees, like blues notes
        if self.chromatic_intervals is not None:
            self.chromatic_notes = NoteList([self.tonic + i for i in self.chromatic_intervals])
            self.diatonic_notes = NoteList([self.tonic + i for i in self.diatonic_intervals.pad()])

        # update this Key's notes to prefer sharps/flats depending on its tonic:
        self._set_sharp_preference()


    @staticmethod
    def _parse_tonic(name, tonic):
        """takes the class's name and root args, and determines which has been given.
        returns root as a Note object, and scale name as string or None"""
        if name is not None:
            if parsing.begins_with_valid_note_name(name):
                # parse as the name of a Key:
                assert tonic is None, f'Key object initiated by Key name ({name}) but provided conflicting tonic arg ({tonic})'
                tonic, scale_name = parsing.note_split(name)
                scale_name = scale_name.strip()
            else:
                assert tonic is not None, f'Key object initiated by Scale name ({name}) but no tonic note provided'
                scale_name = name
            tonic = Note(tonic)
        elif tonic is not None:
            tonic = Note(tonic)
            scale_name = name # i.e. None
        else:
            raise Exception('neither scale_name nor tonic provided to Key init, we need one or the other!')
        return tonic, scale_name

    def _detect_sharp_preference(self, default=False):
        """detect if a chord should prefer sharp or flat labelling
        depending on its tonic and quality"""
        if (self.quality.major and self.tonic in sharp_major_tonics) or (self.quality.minor and self.tonic in sharp_minor_tonics):
            return True
        elif (self.quality.major and self.tonic in flat_major_tonics) or (self.quality.minor and self.tonic in flat_minor_tonics):
            return False
        else:
            return default

    def _set_sharp_preference(self, prefer_sharps=None):
        """set the sharp preference of this Key,
        and of all notes inside this Key"""
        if prefer_sharps is None:
            # detect from object attributes
            prefer_sharps = self._detect_sharp_preference()

        self.prefer_sharps = prefer_sharps
        self.tonic._set_sharp_preference(prefer_sharps)
        for n in self.notes:
            n._set_sharp_preference(prefer_sharps)


    @property
    def scale_name(self):
        """a Key's scale_name is whatever name it would get as a Scale:
        the last entry in interval_mode_names for its intervals"""
        return Scale.get_name(self) # inherits from Scale

    @property
    def name(self):
        suffix = Scale.get_suffix(self)
        # leave a space between tonic and scale name if the scale name is a suffix:
        if suffix != self.scale_name:
            gap = ''
        else:
            gap = ' '
        return f'{self.tonic.name}{gap}{suffix}'

    def __str__(self):
        return f'𝄞 Key of {self.name}  {self.notes}'

    def chord(self, degree, order=3, qualifiers=None):
        """overwrites Scale.chord, returns a Chord object instead of an AbstractChord"""
        abstract_chord = super().chord(degree, order, qualifiers)
        root = self.degree_notes[degree]
        chord_obj = abstract_chord.on_root(root)
        # initialised chords inherit this key's sharp preference:
        chord_obj._set_sharp_preference(self.prefer_sharps)
        return chord_obj

    def chords(self, order=3):
        """returns the list of chords built on every degree of this Key"""
        chord_list = []
        for d, note in self.degree_notes.items():
            chord_list.append(self.chord(d, order=order))
        return chord_list

    def valid_abstract_chords(self, *args, **kwargs):
        """wrapper around Scale.get_valid_chords method"""
        return super().valid_chords(*args, **kwargs)

    def valid_chords(self, degree, *args, **kwargs):
        """wrapper around Scale.get_valid_chords but feeding it the appropriate root note from this Key"""
        return super().valid_chords(degree, *args, _root_note = self.degree_notes[degree], **kwargs)

    def clockwise(self, value=1):
        """fetch the next key from clockwise around the circle of fifths,
        or if value>1, go clockwise that many steps"""
        reference_key = self if self.major else self.relative_major
        new_co5s_pos = (co5s_positions[reference_key] + value) % 12
        # instantiate new key object: (just in case???)
        new_key = co5s[new_co5s_pos]
        new_key = new_key if self.major else new_key.relative_minor
        pdb.set_trace()
        return Key(new_key.tonic, new_key.suffix)

    def counterclockwise(self, value=1):
        return self.clockwise(-value)

    def subscale(self, degrees=None, omit=None, chromatic_intervals=None, name=None):
        """as Scale.subscale, but adds this key's tonic as well and initialises a Subkey instead"""
        return Subkey(parent_scale=self, degrees=degrees, omit=omit, chromatic_intervals=chromatic_intervals, assigned_name=name, tonic=self.tonic) # [self[s] for s in degrees]


    # @property
    # def pentatonic(self):
    #     """returns the pentatonic subscale of the natural major or minor scales.
    #     will function for other scales, though is not well-defined."""
    #     if self.quality.major and self.is_natural:
    #         return self.subscale(degrees=[1,2,3,5,6])
    #     elif self.quality.minor and self.is_natural:
    #         return self.subscale(degrees=[1,3,4,5,7])
    #     else:
    #         ordered_pent_scales = self.compute_pentatonics()
    #         preferred = list(ordered_pent_scales.keys())[0]
    #         return self.subscale(omit=preferred.omit, name=f'{self.name} pentatonic')


    @property
    def relative_minor(self):
        # assert not self.minor, f'{self} is already minor, and therefore has no relative minor'
        assert self.quality.major, f'{self} is not major, and therefore has no relative minor'

        rel_tonic = relative_minors[self.tonic.name]
        if self.rotation == 1: # i.e. not a mode
            rel_scale = self.scale_name.replace('major', 'minor') # a kludge but it works
            return Key(rel_scale, tonic=rel_tonic)
        else:
            raise Exception('figure out what to do here - what are the relative minors/majors of non-natural scales?')
            # just try lowering the third and see what happens
            rel_intervals = IntervalList([i for i in self.intervals])
            rel_intervals[1] = Interval(rel_intervals[1]-1, degree=rel_intervals[1].degree)
            return Key(tonic=rel_tonic, intervals=rel_intervals)

        # new_factors = ChordFactors(self.factors)
        # new_factors[3] -= 1 # flatten third
        # return Chord(factors=new_factors, root=rel_root, inversion=self.inversion)

    # @property
    # def relative_major(self):
    #     # assert not self.major, f'{self} is already major, and therefore has no relative major'
    #     assert self.quality.minor, f'{self} is not minor, and therefore has no relative major'
    #     rel_root = relative_majors[self.tonic.name]
    #     new_factors = ChordFactors(self.factors)
    #     new_factors[3] += 1 # raise third
    #     return Chord(factors=new_factors, root=rel_root, inversion=self.inversion)

    @property
    def relative(self):
        if self.quality.major:
            return self.relative_minor
        elif self.quality.minor:
            return self.relative_major
        else:
            raise Exception(f'Chord {self} is neither major or minor, and therefore has no relative')

    # def __invert__(self):
    #     """~ operator returns the relative major/minor of a key"""
    #     if self.major:
    #         return self.relative_minor
    #     elif self.minor:
    #         return self.relative_major
    #     else:
    #         return self

    def __contains__(self, item):
        """if item is an Interval, does it fit in our list of degree-intervals plus chromatic-intervals?
        if it is a Chord, can it be made using the notes in this key?"""
        if isinstance(item, (Interval, int)):
            return Interval(item) in self.intervals
        elif isinstance(item, Note) or (isinstance(item, str) and parsing.is_valid_note_name(item)):
            return item in self.notes
        elif isinstance(item, (Chord, str)):
            # accept objects that cast to Chords:
            if isinstance(item, str):
                item = Chord(item)
            assert isinstance(item, Chord)

            # chord is 'in' this Key if all ofits notes are:
            if item.root not in self.notes:
                return False # easy early pruning
            else:
                for note in item.notes:
                    if note not in self.notes:
                        return False
            return True

        else:
            raise TypeError(f'Key.__contains__ not defined for items of type: {type(item)}')

    def __eq__(self, other):
        if isinstance(other, Key):
            return self.notes == other.notes
        else:
            raise TypeError(f'__eq__ not defined between Key and {type(other)}')

    def __hash__(self):
        return hash((self.notes, self.diatonic_intervals, self.intervals, self.chromatic_intervals))

    def play(self, *args, **kwargs):
        # add an octave over the top for playback:
        full_notes = NoteList(list(self.notes) + [self.tonic])
        full_notes.play(*args, **kwargs)


class Subkey(Key, Subscale):
    """a Key that is built on a Subscale rather than a scale. Initialised as Subscale but also with a tonic."""
    # def __init__(self, subscale_name=None, intervals=None, tonic=None, notes=None, mode=1, chromatic_intervals=None, stacked=True):
    def __init__(self, subscale_name=None, parent_scale=None, degrees=None, omit=None, chromatic_intervals=None, assigned_name=None, tonic=None):

        # get correct tonic and scale name from (key_name, tonic) input args:
        self.tonic, subscale_name = self._parse_tonic(subscale_name, tonic)

        # as Subscale.init:
        super(Key, self).__init__(subscale_name, parent_scale, degrees, omit, chromatic_intervals, assigned_name)
        # (this sets self.base_scale, .quality, .intervals, .diatonic_intervals, .chromatic_intervals, .rotation)

        # set Subkey-specific attributes: notes, degree_notes, etc.
        # as in Key.init:
        padded_diatonic_intervals = self.diatonic_intervals.pad()
        self.diatonic_notes = NoteList([self.tonic + i for i in padded_diatonic_intervals])
        self.diatonic_note_intervals = {self.diatonic_notes[i]: padded_diatonic_intervals[i] for i in range(len(self.diatonic_notes))}
        self.diatonic_interval_notes = {padded_diatonic_intervals[i]: self.diatonic_notes[i] for i in range(len(self.diatonic_notes))}

        self.degree_notes = {d: self.diatonic_notes[d-1] for d in range(len(self.degree_intervals))}
        self.note_degrees = {self.diatonic_notes[d-1]: d for d in range(len(self.degree_intervals))}

        # TBI: this could use refactoring? no need to pad if we can just append/update dicts

        padded_intervals = self.intervals.pad()
        self.notes = NoteList([self.tonic + i for i in padded_intervals])
        self.note_intervals = {self.notes[i]: padded_intervals[i] for i in range(len(self.notes))}
        self.interval_notes = {padded_intervals[i]: self.notes[i] for i in range(len(self.notes))}

        # used only for Keys with strange chromatic notes not built on integer degrees, like blues notes
        if self.chromatic_intervals is not None:
            self.chromatic_notes = NoteList([self.tonic + i for i in self.chromatic_intervals])
            # self.diatonic_notes = NoteList([self.tonic + i for i in self.diatonic_intervals.pad()])

        # update this Subkey's notes to prefer sharps/flats depending on its tonic (and maj/min/null quality):
        self._set_sharp_preference()

    @property
    def name(self):
        subscale_name = Subscale.get_name(self)
        return f'{self.tonic.name} {subscale_name}'

    def __str__(self):
        return f'𝄲 Key of {self.name}  {self.notes}'

# subscale init:
    # def __init__(self, subscale_name=None, parent_scale=None, degrees=None, omit=None, chromatic_intervals=None, assigned_name=None):





def matching_keys(chord_list=None, note_list=None, display=True,
                    assume_tonic=False, require_tonic=True,
                    upweight_roots=True,
                    # upweight_third=True, downweight_fifth=True,
                    min_recall=0.8, min_precision=0.7, min_likelihood=0.5, max_results=5):
    """from an unordered set of chords, return a dict of candidate keys that could match those chord.
    we make no assumptions about the chord list, except in the case of assume_tonic, where we slightly
    privilege keys that have their tonic on the root of the starting chord in chord_list."""

    # TBI: if this needs to be made faster, could we check across all Scale intervals, rather than across all Key notes?

    if chord_list is not None:
        assert isinstance(chord_list, (list, tuple)), f'chord_list input to matching_keys must be an iterable, but got: {type(chord_list)}'
        chord_list = [Chord(c) if isinstance(c, str) else c for c in chord_list]

        assert check_all(chord_list, 'isinstance', Chord), f"chord_list input to matching_keys must be a list of Chords (or strings that cast to Chords), but got: {[type(c)] for c in chord_list}"

        # keep track of the number of times each note appears in our chord_list,
        # which will be the item weights to our precision_recall function:
        note_counts = Counter()

        for chord in chord_list:
            note_counts.update(chord.notes)
            if upweight_roots:
                # increase the weight of the root note too:
                note_counts.update([chord.root])

        if assume_tonic:
            # upweight all the notes of the first and last chord
            note_counts.update(chord_list[0].notes)
            note_counts.update(chord_list[-1].notes)
    elif note_list is not None:
        # just use notes directly
        note_list = NoteList(note_list)
        note_counts = Counter(note_list)
    else:
        raise Exception(f'matching_keys requires one of: chord_list or note_list')


    unique_notes = list(note_counts.keys())

    candidates = {} # we'll build a list of Key object candidates as we go
    # keying candidate Key objs to (rec, prec, likelihood, consonance) tuples

    if require_tonic:
        # we only try building scales with their tonic on a root or bass of a chord in the chord_list
        if chord_list is not None:
            candidate_tonics = list(set([c.root for c in chord_list] + [c.bass for c in chord_list]))
        else: # or the first note in the note list
            candidate_tonics = [note_list[0]]
    else:
        # we try building keys on any note that occurs in the chord_list:
        candidate_tonics = unique_notes

    for t in candidate_tonics:
        for intervals, mode_names in interval_mode_names.items():
            candidate_notes = [t] + [t + i for i in intervals]

            precision, recall = precision_recall(unique_notes, candidate_notes, weights=note_counts)

            if recall >= min_recall and precision >= min_precision:
                candidate = Key(notes=candidate_notes)

                likelihood = candidate.likelihood
                consonance = candidate.consonance
                if likelihood >= min_likelihood:
                    candidates[candidate] = {'precision': round(precision, 2),
                                            'likelihood': round(likelihood,2),
                                                'recall': round(recall,    2),
                                            'consonance': round(consonance,3)}


    # return sorted candidates dict: (note that unlike in matching_chords we sort by precision rather than recall first)
    sorted_cands = sorted(candidates,
                          key=lambda c: (candidates[c]['precision'],
                                         candidates[c]['likelihood'],
                                         candidates[c]['recall'],
                                         candidates[c]['consonance']),
                          reverse=True)[:max_results]


    if display:
        # print result as nice dataframe instead of returning a dict
        if chord_list is not None:
            title = [f"Key matches for chords: {', '.join([c.name for c in chord_list])}"]
            if assume_tonic:
                title.append(f'(upweighted first and last chords: {chord_list[0].name}, {chord_list[-1].name})')
        elif note_list is not None:
            title = [f"Key matches for notes: {', '.join([n.name for n in note_list])}"]

        title = ' '.join(title)
        print(title)

        # we'll figure out how long we need to make each 'column' by iterating through cands:
        key_name_parts = []
        note_list_parts = []
        for cand in sorted_cands:
            # break key string up for nice viewing:
            key_name_parts.append(cand.name)
            note_list_parts.append(str(cand.notes))
        longest_name_len = max([len(str(s)) for s in (key_name_parts + ['  key name'])])+3
        longest_notes_len = max([len(str(s)) for s in (note_list_parts + ['    notes'])])+3

        left_header =f"{'  key name':{longest_name_len}} {'    notes':{longest_notes_len}}"
        score_parts = ['precision', 'lklihood', 'recall', 'consonance']
        hspace = 8
        right_header = ' '.join([f'{h:{hspace}}' for h in score_parts])
        out_list = [left_header + right_header]


        for i, cand in enumerate(sorted_cands):
            scores = candidates[cand]
            prec, lik, rec, cons = list(scores.values())
            name_str, notes_str = key_name_parts[i], note_list_parts[i]

            descriptor = f'{name_str:{longest_name_len}} {notes_str:{longest_notes_len}}'
            scores = f' {str(prec):{hspace}} {str(lik):{hspace}}  {str(rec):{hspace}}  {cons:.03f}'
            out_list.append(descriptor + scores)
        print('\n'.join(out_list))
    else:
        return {c: candidates[c] for c in sorted_cands}





def unit_test():
    # 3 types of initialisation:
    test(Key(scale_name='natural minor', tonic='B'), Key('Bm'))
    test(Key(intervals=[2,4,5,7,9,11], tonic='C'), Key(notes='CDEFGAB'))


    test(Key('Cm').intervals, Scale('natural minor').intervals)

    print('Test Key __contains__:')
    # normal scale-degree triads/tetrads:
    test(Chord('Dm') in Key('C'), True)
    test(Chord('D') in Key('C'), False)
    test(Chord('G7') in Key('C'), True)
    test(Chord('Bdim') in Key('C'), True)
    test(Chord('Fdim7') in Key('C'), False)

    # disqualification by non-matching root:
    test(Chord('D#') in Key('C'), False)


    # non-triadic chords that are still valid:
    test(Chord('D13sus4') in Key('C'), True)
    # or not:
    test(Chord('Fmmaj11') in Key('C'), False)

    matching_keys(['C', Chord('F'), 'G7', 'Bdim'])

    matching_keys(['Dm', 'Dsus4', 'Am', 'Asus4', 'E', 'E7', 'Asus4', 'Am7'], assume_tonic=True)


if __name__ == '__main__':
    unit_test()
