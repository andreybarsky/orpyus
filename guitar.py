from . import notes as notes
from .notes import Note, OctaveNote, NoteList
from .chords import AbstractChord, Chord, most_likely_chord, matching_chords
from .scales import Scale, Subscale
from .keys import Key, Subkey, matching_keys
from . import parsing
from .util import log, test, auto_split
from .display import Fretboard
import pdb

class String(OctaveNote):
    def __call__(self, fret):
        return self + fret


tunings = {'standard':[String('E2'), String('A2'), String('D3'), String('G3'), String('B3'), String('E4')],
           'dropD':   [String('D2'), String('A2'), String('D3'), String('G3'), String('B3'), String('E4')],
           'dropC':   [String('C2'), String('G2'), String('C3'), String('F3'), String('A3'), String('D4')],
           'dropB':   [String('B1'), String('Gb2'), String('B2'), String('E3'), String('Ab3'), String('Db4')],
           'openE':   [String('E2'), String('B2'), String('E3'), String('G#3'), String('B3'), String('E4')],
           'openD':   [String('D2'), String('A2'), String('D3'), String('G3'), String('A3'), String('D4')], # aka DADGAD
           'openC':   [String('C2'), String('G2'), String('C3'), String('G3'), String('C4'), String('E4')],
           'openG':   [String('D2'), String('G2'), String('D3'), String('G3'), String('B3'), String('D4')],
           }

class Guitar:
    def __init__(self, tuning='standard', strings=6, capo=0, verbose=False):
        """tuning can be one of:
        a descriptive string: standard, dropD, openE, etc.
        or a six-character string like: EADGBE, DADGAD, etc."""

        assert isinstance(tuning, str) # for now

        self.num_strings = strings
        self.capo = capo

        # parse tuning string into internal list of OctaveNotes:
        if tuning in tunings.keys():
            self.tuned_strings = tunings[tuning]
            self.tuning = ''.join([s.chroma for s in self.tuned_strings])

        else:
            default_bass = String('E2')
            # separate out individual note chromas from the input string:
            tuning_chromas = NoteList([Note(n) for n in parsing.parse_out_note_names(tuning)])
            tuned_strings = tuning_chromas.force_octave(start_octave=2)
            self.tuned_strings = [String(s) for s in tuned_strings]
            self.tuning = ''.join([s.chroma for s in self.tuned_strings])


        # open strings are relative to capo instead of to the neck:
        self.open_strings = [s + self.capo for s in self.tuned_strings]

        self.verbose = verbose # for debugging

    def add_capo(self, capo):
        self.capo = capo
        self.open_strings = [s + self.capo for s in self.tuned_strings]
        print(self)

    def remove_capo(self):
        self.capo = 0
        self.open_strings = [s + self.capo for s in self.tuned_strings]
        print(self)


    def distance_from_standard(self):
        """how many semitones up/down must the strings of a standard guitar be tuned to get this tuning?"""
        distances = []
        for i, s in enumerate(self.open_strings):
            distances.append(s - tunings['standard'][i])
        return distances

    def pick(self, frets, pattern=None, *args, **kwargs):
        """plays the fretted notes as audio, arpeggiated into a melody.
        accepts optional 'pattern' arg as list of string indices,
        indicating a picking pattern that changes the order of notes"""
        notes = self[frets]
        if pattern is not None:
            notes = NoteList([notes[p] for p in pattern])
        notes.play(*args, delay=0.25, duration=3, **kwargs)

    def strum(self, frets, *args, **kwargs):
        """plays the fretted notes as audio, arpeggiated close together"""
        notes = self[frets]
        # notes.play(*args, arpeggio=False, **kwargs)
        notes.play(*args, delay=0.05, duration=3, **kwargs)

    def chord(self, frets, *args, **kwargs):
        """plays the fretted notes as audio, summed into a chord"""
        notes = self[frets]
        # notes.play(*args, arpeggio=False, **kwargs)
        notes.play(*args, duration=3, **kwargs)

    ### TBI: distinguish between fretting from neck and fretting from capo
    def fret(self, frets, from_capo=False):
        """simulates plucking each string according to the listed fret diagram, gets the
        resulting notes, and returns them as a NoteList."""
        string_notes = []

        fret_ints = parsing.parse_out_integers(frets)

        for s, f in enumerate(fret_ints):
            if isinstance(f, int):
                if from_capo:
                    # transpose the note that this string is tuned to upwards by f:
                    string_notes.append(self.open_strings[s] + f)
                else:
                    # from neck:
                    if f in {0, self.capo}: # 'open', i.e. sounded from capo position
                        string_notes.append(self.open_strings[s])
                    else:
                        if f < self.capo:
                            raise Exception(f"Tried to fret on {f}, but capo on {self.capo} - can't fret beneath capo!")
                        else:
                            # relative to neck position, not capo position:
                            string_notes.append(self.tuned_strings[s] + f)
            elif f is None:
                # don't sound this string
                pass
            else:
                raise ValueError(f'Passed iterable to Guitar.__call__, expected items to be ints or None, but received item #{s}: {type(fret)}')

        notes = NoteList(string_notes, strip_octave=False)
        return notes


    def __getitem__(self, frets):
        return self.fret(frets)

    def __contains__(self, item):
        return item in self.open_strings

    def __call__(self, frets):
        """accepts a fretting pattern, prints out sounded notes, detected chord,
        and the chord diagram showing what note each string is playing"""
        return self.query(frets)

        # TBI: find way to exclude frets from search? would need to modify precision_recall func probably
    def find_key(self, include=None, exclude=None, string=None, frets=None, tonic=None, show_fretboard=True):
        """for a specified string, and the specified fret numbers on that string
        return the list of keys that those fretted notes are a match for"""

        include_notes = []
        exclude_notes = []
        for dct, lst in zip([include, exclude], [include_notes, exclude_notes]):
            if dct is not None:
                # fill by dict that keys string to fret_list
                # assert string is None and frets is None
                for s,frets in dct.items():
                    this_string_notes = []
                    for f in frets:
                        this_string_notes.append(self.tuned_strings[s-1]+f)
                    lst.extend(this_string_notes)
                    print(f'String {self.tuned_strings[s-1]}, frets {frets}: {this_string_notes}')
            # else:
            #     # fill by single string and its frets
            #     # assert string is not None and frets is not None
            #     assert 0 < string <= self.num_strings, f"This guitar has no string {string}"
            #     include_notes = [self.tuned_strings[string-1]+f for f in frets]
            #     print(f'String {self.tuned_strings[string-1]}, frets {frets}: {include_notes}')


        if tonic is not None:
            if isinstance(tonic, int):
                assert string is not None
                tonic_note = (self.tuned_strings[string-1]+tonic).note
            elif isinstance(tonic, str):
                tonic_note = Note(tonic)
            elif isinstance(tonic, Note):
                tonic_note = tonic
            notes = [tonic_note] + [n.note for n in notes if n.note != tonic_note]

        # dynamically adjust min_precision by the number of notes provided
        min_precision = len(include_notes) / 7

        print(f'Requiring min_precision of: {min_precision}')
        matches = matching_keys(notes=include_notes, exclude=exclude_notes, min_precision=0, require_tonic=(tonic is not None), return_matches=True)

        if show_fretboard:
            # show fretboard on the first 3 matches
            for m in list(matches.keys())[:3]:
                print()
                self.show_key(m)

    def matching_chords(self, frets, *args, **kwargs):
        """analyses this set of frets and detects what chords they might represent"""
        notelist = self[frets]
        return matching_chords(notelist, *args, **kwargs)

    def most_likely_chord(self, frets, *args, **kwargs):
        """returns the most likely chord detected for this set of frets"""
        notelist = self[frets]
        return most_likely_chord(notelist, *args, **kwargs)

    def query(self, frets):
        """parses the frets passed, displays the sounded notes, the auto-detected chord,
        and shows the resulting fret diagram"""
        sounded_notes = self.fret(frets)
        print(f'Sounded notes: {sounded_notes}')
        sounded_chord = self.most_likely_chord(frets)
        print(f'Detected chord notes: {sounded_chord}')

        fret_ints = parsing.parse_out_integers(frets)
        mute = [s+1 for s in range(len(fret_ints)) if fret_ints[s] is None]
        string_contents = [(self.open_strings[s] + fret_ints[s]).chroma  if fret_ints[s] is not None  else None  for s in range(self.num_strings)]
        ### TBI: capo support?
        fret_cells = {(s+1,f):string_contents[s] for s,f in enumerate(fret_ints) if (f != 0 and f is not None)}
        Fretboard(fret_cells, mute=mute).disp()


    def locate_note(self, note, match_octave=False, min_fret=0, max_fret=13):
        """accepts a Note object, (or, if match_octave, an OctaveNote object)
        and returns a list of tuple (string,fret) locations where that note appears"""
        # keep a list of locations
        note_locs = []
        for s, string in enumerate(self.open_strings):
            # if this open/capo'd string corresponds to that note:
            if string.chroma == note.chroma:
                # add (s,0) or (s,capo) to the list:
                if not (match_octave and (string.value != note.value)):
                    note_locs.append((s+1,self.capo))
            else:
                next_chosen_note = string.next(note.chroma)
                distance_up = next_chosen_note - string # distance along the fretboard in intervals
                next_loc = int(distance_up + self.capo)
                if next_loc >= min_fret:
                    if not ((match_octave) and (string.value+next_loc) != note.value):
                        # if the note on this string isn't in the right octave (and we have asked to match octave), ignore it
                        note_locs.append((s+1, next_loc))
                    # if the NEXT highest is within our max fret, append that too:
                    if next_loc + 12 <= max_fret:
                        if not ((match_octave) and (string.value+next_loc+12) != note.value):
                            # if the note on this string isn't in the right octave, ignore it
                            note_locs.append((s+1, next_loc+12))
        return note_locs

    def show_octavenote(self, note, max_fret=13, min_fret=0, preserve_accidental=True, *args, **kwargs):
        if isinstance(note, str):
            note = OctaveNote(note, prefer_sharps=('#' in note) if preserve_accidental else None)
        note_locs = self.locate_note(note, match_octave=True, max_fret=max_fret, min_fret=min_fret)
        cells = {loc: note.name for loc in note_locs}
        Fretboard(cells, title=f'Note: {note.chroma} (octave {note.octave}) on {self}').disp(*args, **kwargs)

    def show_note(self, note, show_octave=True, max_fret=15, min_fret=0, preserve_accidental=True, *args, **kwargs):
        if isinstance(note, (str, OctaveNote)):
            # cast string to note, or discard octave information from octavenote:
            note = Note(note, prefer_sharps=('#' in note) if preserve_accidental else None)
        note_locs = self.locate_note(note, max_fret=max_fret, min_fret=min_fret)
        if show_octave:
            octavenotes = []
            for (s,fret) in note_locs:
                if fret == 0:
                    oct = self.open_strings[s-1]
                else:
                    oct = self.tuned_strings[s-1] + fret
                if preserve_accidental:
                    oct = OctaveNote(oct.value, prefer_sharps=note.prefer_sharps)
                octavenotes.append(oct)
            cells = {loc: oct.name for loc, oct in zip(note_locs, octavenotes)}
        else:
            cells = {loc: note.chroma for loc in note_locs}
        Fretboard(cells, title=f'Note: {note.name} on {self}').disp(*args, **kwargs)

    def show_chord(self, chord, intervals_only=False, notes_only=False, max_fret=13, min_fret=0, preserve_accidental=True, title=None, show_index=True, *args, **kwargs): # preserve accidentals?
        """for a given Chord object (or name that casts to Chord),
        show where the notes of that chord fall on the fretboard, starting from open."""
        if isinstance(chord, str):
            chord = Chord(chord, prefer_sharps=('#' in chord) if preserve_accidental else None)

        #### determine cell values:
        root_locs = self.locate_note(chord.root, min_fret=min_fret, max_fret=max_fret)
        cells = {}
        # loop across all the notes in chord, find all their locations:
        for iv, note in zip(chord.intervals, chord.notes):
            if intervals_only:
                cell_val = iv.factor_name
            elif notes_only:
                cell_val = note.name
            else: # both
                cell_val = f'{iv.factor_name:>3}:{note.name}'
            note_cells = {loc: cell_val for loc in self.locate_note(note, min_fret=min_fret, max_fret=max_fret)}
            cells.update(note_cells)

        #### determine index / string labels:
        if show_index:
            if intervals_only:
                # replace note with interval on index labels as well
                index = [f'{(chord.factor_intervals[chord.note_factors[string.note]].factor_name):>3}' if string.note in chord.notes else '' for s in self.tuned_strings ]
            elif notes_only:
                index = [string.chroma if string.chroma in chord.notes else '' for string in self.tuned_strings ]
            else: # notes AND intervals:
                index = [f'{(chord.factor_intervals[chord.note_factors[string.note]].factor_name):>3}:{string.chroma}'  if string.note in chord.notes  else ''  for string in self.tuned_strings ]
        else:
            index = ['']*self.num_strings # list of empty strings as index


        #### finalise:
        if title is None:
            title=f'Chord: {chord} on {self}'
        Fretboard(cells, index=index, highlight=root_locs, title=title).disp(*args, **kwargs)

    def show_key(self, key, intervals_only=False, notes_only=False, min_fret=0, max_fret=13, title=None, show_index=True, highlight_fifths=False, highlight_pentatonic=False, *args, **kwargs):
        """for a given Key object (or name that casts to key),
        show where the notes of that key fall on the fretboard, starting from open."""
        if isinstance(key, str):
            if 'blues' in key or 'pent' in key:
                # auto detect subkeys, as opposed to keys:
                key = Subkey(key)
            else:
                key = Key(key)

        #### determine highlighted frets
        # highlight tonics:
        highlights = self.locate_note(key.tonic, max_fret=max_fret)
        if not highlight_pentatonic:
            # and, optionally, fifths:
            if highlight_fifths:
                if (isinstance(key, Subkey) and 5 in key.base_degree_notes) or (type(key) == Key):
                    highlights.extend(self.locate_note(key.base_degree_notes[5], max_fret=max_fret))
        elif highlight_pentatonic and not key.is_subscale:
            # pick out the pentatonic notes to highlight
            this_pentatonic = key.pentatonic
            for n in this_pentatonic.notes[1:]:
                highlights.extend(self.locate_note(n, max_fret=max_fret))

        #### determine cell values:
        cells = {}
        for iv, note in zip(key.intervals.pad(), key.notes):
            if intervals_only: # then as notes
                cell_val = iv.factor_name
            elif notes_only:
                cell_val = note.name
            else:
                cell_val = f'{iv.factor_name:>3}:{note.name}'
            note_cells = {loc: cell_val for loc in self.locate_note(note, max_fret=max_fret)}
            cells.update(note_cells)

        #### determine index / string labels
        if show_index:
            if intervals_only:
                # replace note with interval on index labels as well
                index = [f'{(key.note_intervals[string.note].factor_name):>3}' if string.chroma in key.notes  else ''  for string in self.tuned_strings]
            elif notes_only:
                index = [s.chroma if s.chroma in key.notes else '' for s in self.tuned_strings ]
            else: # notes AND intervals:
                index = [f'{(key.note_intervals[string.note].factor_name):>3}:{string.chroma:>2}'  if string.chroma in key.notes  else ''  for string in self.tuned_strings]
        else:
            index = ['']*self.num_strings # list of empty strings as index

        #### finalise:
        if title is None:
            title = f'{key} on {self}'
        Fretboard(cells, index=index, highlight=highlights, title=title).disp(*args, fret_size=7, **kwargs)

    def show_abstract_chord(self, chord, *args, **kwargs):
        """for a given AbstractChord object (or name that casts to AbstractChord),
        show where the notes of that chord fall on the fretboard starting from an arbitrary fret"""
        # internally: we just re-use the show_chord method, but on a higher fret and we hide the labels/indices
        if isinstance(chord, str):
            chord = AbstractChord(chord)
        a_chord = chord.on_root('A')
        self.show_chord(a_chord, fret_labels=False, show_index=False, min_fret=4, max_fret=16, intervals_only=True, title=f'{chord} on {self}')

    def show_scale(self, scale, *args, **kwargs):
        """for a given abstract Scale object (or name that casts to Scale),
        show where the notes of that scale fall on the fretboard starting from an arbitrary fret"""
        if isinstance(scale, str):
            try:
                scale = Subscale(scale)
            except:
                try:
                    scale = Scale(scale)
                except Exception as e:
                    print(f'Could not cast string {scale} to Scale or Subscale object: {e}')
        a_scale = scale.on_tonic('C')
        self.show_key(a_scale, fret_labels=False, show_index=False, min_fret=3, max_fret=13, intervals_only=True, title=f'{scale} on {self})')

    def show(self, obj, *args, **kwargs):
        """wrapper around the show_note, show_chord, show_key etc. methods.
        accepts an arbitrary object and calls the relevant method to show it"""

        classes = [Subkey, Key, Subscale, Scale,
                   Chord, AbstractChord, OctaveNote, Note]
        funcs = [self.show_key, self.show_key, self.show_scale, self.show_scale,
                self.show_chord, self.show_abstract_chord, self.show_octavenote, self.show_note]
        names = ['Key', 'Key', 'Scale', 'Scale',
                 'Chord', 'Chord', 'Note', 'Note']

        found_type = False
        if not (isinstance(obj, str)): # for non strings, find the right class and function to use:
            for name, cls, func in zip(names, classes, funcs):
                if isinstance(obj, cls):
                    func(obj, *args, **kwargs)
                    break
        else: # for strings, we brute force it by Try block:
            succeeded = False
            obj_name = obj
            for name, cls, func in zip(names, classes, funcs):
                try:
                    obj = cls(obj_name)
                    func(obj)
                    # print(f'Showing {obj}')
                    succeeded = True
                    break
                except:
                    continue
            if not succeeded:
                raise TypeError(f"Could not understand string input to Guitar.show: {obj}")


    def __str__(self):
        tuning_letters = [string.chroma for string in self.tuned_strings]
        tuning_str = ''.join(tuning_letters)
        main_str = [f'Guitar | Tuning: {tuning_str} |']
        if self.capo == 0:
            return main_str[0]
        else:
            capo_letters = [string.chroma for string in self.open_strings]
            capo_str = ''.join(capo_letters)
            main_str.append(f'Capo on {self.capo}: {capo_str}')
            return ' '.join(main_str)

    def __repr__(self):
        return str(self)




standard = eadgbe = Guitar()
dadgad = Guitar('DADGAD')
dadgbe = dropD = dropd = Guitar('DADGBE')

if __name__ == '__main__':
    #
    # test(standard['022100'], NoteList('EBEAbBE').force_octave(2))
    # test(standard('022100'), Chord('E'))
    # test(dadgad('000000'), Chord('Dsus4'))

    # # open chord:
    # chord_diagram('x32010', tuning='DADGBE') # Cmaj
    # # high chord:
    # chord_diagram('07675x') # E7?
    # # extended chord:
    # chord_diagram('x1881x')

    standard.query('x1881x')
    standard.query('x32010')
