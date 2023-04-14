from intervals import Interval, IntervalList
from notes import Note, NoteList
from scales import Scale
from chords import Chord, AbstractChord
import parsing
from util import test, log
import pdb



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
            self.diatonic_notes = NoteList([self.tonic + i for i in self.diatonic_intervals.pad()])
            self.chromatic_notes = NoteList([self.tonic + i for i in self.chromatic_intervals])


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

    @property
    def name(self):
        suffix = self.suffix
        # leave a space between tonic and scale name if the scale name is a suffix:
        if suffix != super().name:
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
        return abstract_chord.on_root(root)

    def valid_abstract_chords(self, *args, **kwargs):
        """wrapper around Scale.get_valid_chords method"""
        return super().valid_chords(*args, **kwargs)

    def valid_chords(self, degree, *args, **kwargs):
        """wrapper around Scale.get_valid_chords but feeding it the appropriate root note from this Key"""
        return super().valid_chords(degree, *args, _root_note = self.degree_notes[degree], **kwargs)

    def __contains__(self, item):
        """if item is an Interval, does it fit in our list of degree-intervals plus chromatic-intervals?"""
        if isinstance(item, (Interval, int)):
            return Interval(item) in self.intervals
        elif isinstance(item, Note) or (isinstance(item, str) and parsing.is_valid_note_name(item)):
            return item in self.notes
        elif isinstance(item, (Chord, str)):
            # accept objects that cast to Chords:
            if isinstance(item, str):
                item = Chord(item)
            assert isinstance(item, Chord)
            if item.root not in self.notes:
                return False # easy early pruning
            # initialise a new Chord on the scale degree corresponding to the query Chord's root
            deg = self.note_degrees[item.root] # the degree of this key that we are building from
            val_chord = self.chord(deg, item.order).invert(item.inversion)
            if item == val_chord:
                return True
            else:
                # query chord is not the default triad/tetrad etc. built on its note-degree,
                # but we try one more thing: is it in the set of all valid chords that could be built
                # from this note degree?
                require_inversions = (item.inversion != 0)
                val_abstract_chords = self.valid_abstract_chords(deg, max_order=item.order, display=False,
                                                                inversions=require_inversions, min_likelihood=0, min_consonance=0)
                return item.abstract() in val_abstract_chords
        else:
            raise TypeError(f'Scale.__contains__ not defined for items of type: {type(item)}')

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

if __name__ == '__main__':
    unit_test()
