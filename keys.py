from .intervals import Interval, IntervalList
from .notes import Note, NoteList, sharp_major_tonics, sharp_minor_tonics, flat_major_tonics, flat_minor_tonics, relative_majors, relative_minors
from .scales import Scale, Subscale, interval_mode_names, parallels
from .chords import Chord, AbstractChord
from . import parsing
from .util import check_all, precision_recall, reverse_dict, test, log

from collections import Counter
import pdb

# natural notes in order of which are flattened/sharpened in a key signature:
flat_order = ['B', 'E', 'A', 'D', 'G', 'C', 'F']
sharp_order = ['F', 'C', 'G', 'D', 'A', 'E', 'B']

# circle of 5ths in both directions as linked lists:
co5s_clockwise = {Note('C')+(7*i) : Note('C')+(7*(i+1)) for i in range(12)}
co5s_counterclockwise = {Note('C')-(7*i) : Note('C')-(7*(i+1)) for i in range(12)}

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
        self.interval_notes = reverse_dict(self.note_intervals)
        # self.interval_notes = {padded_intervals[i]: self.notes[i] for i in range(7)}

        self.degree_notes = {d: self.notes[d-1] for d in range(1,8)}
        self.note_degrees = reverse_dict(self.degree_notes)
        # self.note_degrees = {self.notes[d-1]: d for d in range(1,8)}

        # these are the same for Key objects, but may differ for Subkeys:
        self.base_degree_notes = self.degree_notes
        self.note_base_degrees = self.note_degrees

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
        """detect if this key's tonic note should prefer sharp or flat labelling
        depending on its chroma and quality"""
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
            # detect from tonic and quality
            prefer_sharps = self._detect_sharp_preference()

        self.tonic._set_sharp_preference(prefer_sharps)
        # by default, the Key's prefer_sharps attribute is the same as the tonic:
        self.prefer_sharps = prefer_sharps

        # but in general, flat/sharp preference of a Key is decided by having one note letter per degree of the scale:

        if self.is_natural or self.is_subscale:
            # computation not needed for non-natural scales; and no idea how to handle subscales yet
            # just assign same sharp preference as tonic to every note:
            for n in self.notes:
                n._set_sharp_preference(prefer_sharps)

        else:
            # compute flat/sharp preference by assigning one note to each natural note name
            tonic_nat = self.tonic.chroma[0] # one of the few cases where note sharp preference matters
            next_nat = parsing.next_natural_note[tonic_nat]
            for d in range(2,8):
                n = self.degree_notes[d]
                if n.name == next_nat:
                    # this is a natural note, so its sharp preference shouldn't matter,
                    # but set it to the tonic's anyway for consistency
                    n._set_sharp_preference(prefer_sharps)
                else:
                    # which accidental would make this note's chroma include the next natural note?
                    if n.flat_name[0] == next_nat:
                        n._set_sharp_preference(False)
                    elif n.sharp_name[0] == next_nat:
                        n._set_sharp_preference(True)
                    else:
                        # this note needs to be a double sharp or double flat or something
                        log(f'Found a possible case for a double-sharp or double-flat: degree {d} ({n}) in scale: {self}')
                        # fall back on same as tonic:
                        n._set_sharp_preference(prefer_sharps)
                next_nat = parsing.next_natural_note[next_nat]


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

    def rotate(self, mode):
        """rotates this Key to produce another mode of this Key's base scale, on the same tonic"""
        rotated_scale = Scale.rotate(self, mode)
        rotated_key = rotated_scale.on_tonic(self.tonic)
        return rotated_key

    # @property
    # def modes(self):
    #     return [self.rotate(m) for m in range(1,8)]

    # return all the modes of this scale, starting from wherever it is:
    @property
    def parallel_modes(self):
        """the 'parallel' modes of a Key are all its modes that start on the same tonic"""
        return [self.rotate(m) for m in range(1,8)]

    @property
    def modes(self):
        """the modes of a Key are the relative keys that share its notes but start on a different tonic
        i.e. modes of C major are D dorian, E phrygian, etc."""
        return [Key(notes=Key('C').notes.rotate(i)) for i in range(1,8)]

    def subscale(self, degrees=None, omit=None, chromatic_intervals=None, name=None):
        """as Scale.subscale, but adds this key's tonic as well and initialises a Subkey instead"""
        return Subkey(parent_scale=self, degrees=degrees, omit=omit, chromatic_intervals=chromatic_intervals, assigned_name=name, tonic=self.tonic) # [self[s] for s in degrees]


    @property
    def parallel_minor(self):
        if not self.quality.major:
            raise Exception(f'{self.name} is not major, and therefore has no parallel minor')


    @property
    def relative_minor(self):
        # assert not self.minor, f'{self} is already minor, and therefore has no relative minor'
        assert self.quality.major, f'{self} is not major, and therefore has no relative minor'
        rel_tonic = relative_minors[self.tonic.name]
        if self.rotation == 1 or 'major' in self.scale_name: # i.e. not a mode
            rel_scale = self.scale_name.replace('major', 'minor') # a kludge but it works
            return Key(rel_scale, tonic=rel_tonic)
        else:
            raise Exception('Relative major/minor not defined for non-natural Keys')
            # figure out what to do here - what are the relative minors/majors of non-natural scales?
            # just try lowering the third and see what happens?
            # rel_intervals = IntervalList([i for i in self.intervals])
            # rel_intervals[1] = Interval(rel_intervals[1]-1, degree=rel_intervals[1].degree)
            # return Key(tonic=rel_tonic, intervals=rel_intervals)

    @property
    def relative_major(self):
        # assert not self.minor, f'{self} is already minor, and therefore has no relative minor'
        assert self.quality.minor, f'{self} is not minor, and therefore has no relative major'
        rel_tonic = relative_majors[self.tonic.name]
        if self.rotation == 1 or 'minor' in self.scale_name: # i.e. not a mode
            rel_scale = self.scale_name.replace('minor', 'major') # a kludge but it works
            return Key(rel_scale, tonic=rel_tonic)
        else:
            raise Exception('Relative major/minor not defined for non-natural Keys')


    @property
    def relative(self):
        if self.quality.major:
            return self.relative_minor
        elif self.quality.minor:
            return self.relative_major
        else:
            raise Exception(f'Key of {self.name} is neither major or minor, and therefore has no relative')

    @property
    def parallel_minor(self):
        if self.quality.major and self.is_natural:
            return

    @property
    def parallel(self):
        if self.quality.major and self.is_natural:
            return self.parallel_minor
        elif self.quality.minor and self.is_natural:
            return self.parallel_major
        else:
            raise Exception('Parallel major/minor not defined for non-natural Keys')

    def __invert__(self):
        """~ operator returns the parallel major/minor of a key"""
        return self.parallel

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
        # plays the notes in this key (we also add an octave over root on top for resolution)
        played_notes = NoteList([n for n in self.notes] + [self.tonic])
        played_notes.play(*args, **kwargs)


class Subkey(Key, Subscale):
    """a Key that is built on a Subscale rather than a scale. Initialised as Subscale but also with a tonic."""
    # def __init__(self, subscale_name=None, intervals=None, tonic=None, notes=None, mode=1, chromatic_intervals=None, stacked=True):
    def __init__(self, subscale_name=None, parent_scale=None, degrees=None, omit=None, chromatic_intervals=None, assigned_name=None, tonic=None):

        # get correct tonic and scale name from (key_name, tonic) input args:
        self.tonic, subscale_name = self._parse_tonic(subscale_name, tonic)



        # as Subscale.init:
        super(Key, self).__init__(subscale_name, parent_scale, degrees, omit, chromatic_intervals, assigned_name)
        # (this sets self.base_scale_name, .quality, .intervals, .diatonic_intervals, .chromatic_intervals, .rotation)

        self.base_degree_notes = {d:self.tonic + iv for d,iv in self.base_degree_intervals.items()}
        self.note_base_degrees = reverse_dict(self.base_degree_notes)

        # set Subkey-specific attributes: notes, degree_notes, etc.
        # as in Key.init:
        padded_diatonic_intervals = self.diatonic_intervals.pad()
        self.diatonic_notes = NoteList([self.tonic + i for i in padded_diatonic_intervals])
        self.diatonic_note_intervals = {self.diatonic_notes[i]: padded_diatonic_intervals[i] for i in range(len(self.diatonic_notes))}
        self.diatonic_interval_notes = {padded_diatonic_intervals[i]: self.diatonic_notes[i] for i in range(len(self.diatonic_notes))}

        self.degree_notes = {d+1: self.diatonic_notes[d] for d in range(len(self.degree_intervals))}
        self.note_degrees = {self.diatonic_notes[d]: d+1 for d in range(len(self.degree_intervals))}

        # TBI: this could use refactoring? no need to pad if we can just append/update dicts

        padded_intervals = self.intervals.pad()
        self.notes = NoteList([self.tonic + i for i in padded_intervals])
        self.note_intervals = {self.notes[i]: padded_intervals[i] for i in range(len(self.notes))}
        self.interval_notes = {padded_intervals[i]: self.notes[i] for i in range(len(self.notes))}

        # used only for Keys with strange chromatic notes not built on integer degrees, like blues notes
        if self.chromatic_intervals is not None:
            self.chromatic_notes = NoteList([self.tonic + i for i in self.chromatic_intervals])
            # self.diatonic_notes = NoteList([self.tonic + i for i in self.diatonic_intervals.pad()])

        # take the tonic out of assigned name if one has been given:
        if assigned_name is not None:
            _, assigned_name = self._parse_tonic(assigned_name, None)
            self.assigned_name = assigned_name

        # update this Subkey's notes to prefer sharps/flats depending on its tonic (and maj/min/null quality):
        self.is_natural = False
        self._set_sharp_preference()
        assert self.is_subscale

    @property
    def name(self):
        subscale_name = Subscale.get_name(self)
        return f'{self.tonic.name} {subscale_name}'

    def __str__(self):
        return f'𝄲 Key of {self.name}  {self.notes}'

# subscale init:
    # def __init__(self, subscale_name=None, parent_scale=None, degrees=None, omit=None, chromatic_intervals=None, assigned_name=None):





def matching_keys(chords=None, notes=None, exclude=None,
                    display=True, return_matches=False,
                    assume_tonic=False, require_tonic=True,
                    upweight_chord_roots=True, upweight_key_tonics=True, upweight_pentatonics=False, # upweight_pentatonics might be broken
                    min_recall=0.8, min_precision=0.7, min_likelihood=0.5, max_results=5):
    """from an unordered set of chords, return a dict of candidate keys that could match those chord.
    we make no assumptions about the chord list, except in the case of assume_tonic, where we slightly
    privilege keys that have their tonic on the root of the starting chord in chord list."""

    # TBI: if this needs to be made faster, could we check across all Scale intervals, rather than across all Key notes?

    if chords is not None:
        assert isinstance(chords, (list, tuple)), f'chord list input to matching_keys must be an iterable, but got: {type(chords)}'
        chords = [Chord(c) if isinstance(c, str) else c for c in chords]

        assert check_all(chords, 'isinstance', Chord), f"chord list input to matching_keys must be a list of Chords (or strings that cast to Chords), but got: {[type(c) for c in chords]}"

        # keep track of the number of times each note appears in our chord list,
        # which will be the item weights to our precision_recall function:
        note_counts = Counter()

        for chord in chords:
            note_counts.update(chord.notes)
            if upweight_chord_roots:
                # increase the weight of the root note too:
                note_counts.update([chord.root])

        if assume_tonic:
            # upweight all the notes of the first and last chord
            note_counts.update(chords[0].notes)
            note_counts.update(chords[-1].notes)
    elif notes is not None:
        # just use notes directly
        notes = NoteList(notes)
        note_counts = Counter(notes)
        if assume_tonic:
            note_counts.update([notes[0]])
    else:
        raise Exception(f'matching_keys requires one list of either: chords or notes')

    if exclude is None:
        exclude = [] # but should be a list of Note objects
    elif exclude is not None and len(exclude) > 0:
        assert isinstance(exclude[0], (str, Note)), "Objects to exclude must be Notes, or strings that cast to notes"
        exclude = NoteList(exclude)

    unique_notes = list(note_counts.keys())

    # set min precision to be at least the fraction of unique notes that have been given
    min_precision = min([min_precision, len(unique_notes) / 7]) # at least the fraction of unique notes that have been given

    candidates = {} # we'll build a list of Key object candidates as we go
    # keying candidate Key objs to (rec, prec, likelihood, consonance) tuples

    if require_tonic:
        # we only try building scales with their tonic on a root or bass of a chord in the chord list
        if chords is not None:
            candidate_tonics = list(set([c.root for c in chords] + [c.bass for c in chords]))
        else: # or the first note in the note list
            candidate_tonics = [notes[0]]
    else:
        # we try building keys on any note that occurs in the chord list:
        candidate_tonics = unique_notes

    for t in candidate_tonics:
        for intervals, mode_names in interval_mode_names.items():
            candidate_notes = [t] + [t + i for i in intervals]

            does_not_contain_exclusions = True
            for exc in exclude:
                if exc in candidate_notes:
                    does_not_contain_exclusions = False
                    break
            if does_not_contain_exclusions:
                # initialise candidate object:
                # (this can be removed for a fast method; it's mostly for upweighting key fifths)
                candidate = Key(notes=candidate_notes)
                this_cand_weights = dict(note_counts)
                if upweight_key_tonics:
                    # count the key's tonic once more, because it's super important
                    this_cand_weights.update({candidate.tonic: 1})
                if upweight_pentatonics:
                    # count the notes in this key's *pentatonic* scale as extra:
                    this_cand_weights.update({n:1 for n in candidate.pentatonic.notes})

                precision, recall = precision_recall(unique_notes, candidate_notes, weights=this_cand_weights)

                if recall >= min_recall and precision >= min_precision:

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
        if chords is not None:
            title = [f"Key matches for chords: {', '.join([c.name for c in chords])}"]
            if assume_tonic:
                title.append(f'(upweighted first and last chords: {chords[0].name}, {chords[-1].name})')
            if upweight_pentatonics:
                title.append('(and upweighted pentatonics)')
        elif notes is not None:
            title = [f"Key matches for notes: {', '.join([n.name for n in notes])}"]

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
    if return_matches:
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

    matching_keys(['C', Chord('F'), 'G7', 'Bdim'], upweight_pentatonics=False)

    matching_keys(['Dm', 'Dsus4', 'Am', 'Asus4', 'E', 'E7', 'Asus4', 'Am7'], assume_tonic=True, upweight_pentatonics=True)


if __name__ == '__main__':
    unit_test()
