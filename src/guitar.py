from . import notes as notes
from .notes import Note, OctaveNote, NoteList
from .chords import AbstractChord, Chord, ChordList, most_likely_chord, matching_chords
from .scales import Scale
from .keys import Key, matching_keys
from .util import log, reverse_dict
from .display import Fretboard
from . import parsing, _settings

### TBI: special cases for other stringed instruments?
### i.e. ukelele/banjo/mandolin tunings, with extensions for half capos etc.

class String(OctaveNote):
    """a String is just an OctaveNote that can be called with an offset ('fret')
    to 'play' it higher by that many semitones"""
    def __call__(self, fret):
        return self + fret

tuning_note_names = {   # names/aliases for common tunings:
        'standard': ( 'E2',  'A2',  'D3',  'G3',  'B3',  'E4' ),
       'half-step': ( 'Eb2', 'Ab2', 'Db3', 'Gb3', 'Bb3', 'Eb4'), # the GnR tuning
           'dropD': ( 'D2',  'A2',  'D3',  'G3',  'B3',  'E4' ),
           'dropC': ( 'C2',  'G2',  'C3',  'F3',  'A3',  'D4' ),
           'dropB': ( 'B1',  'Gb2', 'B2',  'E3',  'Ab3', 'Db4'),
           'openE': ( 'E2',  'B2',  'E3',  'G#3', 'B3',  'E4' ),
          'celtic': ( 'D2',  'A2',  'D3',  'G3',  'A3',  'D4' ), # openDsus4, better known as DADGAD
           'openD': ( 'D2',  'A2',  'D3',  'F#3', 'A3',  'D4' ),
           'openC': ( 'C2',  'G2',  'C3',  'G3',  'C4',  'E4' ),
           'openG': ( 'D2',  'G2',  'D3',  'G3',  'B3',  'D4' ),
               }

# cast string names into OctaveNote objects:
tuning_strings = {name: tuple([String(nt) for nt in notes]) for name, notes in tuning_note_names.items()}
tuning_aliases = reverse_dict(tuning_strings)

class Guitar:
    def __init__(self, tuning='standard', strings=6, capo=0, verbose=False):
        """tuning can be one of:
        a descriptive string: standard, dropD, openE, etc.
        or a six-character string of notes like: EADGBE, DADGAD, etc."""

        assert isinstance(tuning, str), "Guitar tuning must be a string, like 'standard' or 'EADGBE'"

        self.num_strings = strings
        self.capo = capo

        # parse tuning string into internal list of OctaveNotes:

        if tuning in tuning_strings.keys(): # interpret an  alias, like 'standard'
            # what each string is tuned to, before capo:
            self.tuned_strings = tuning_strings[tuning]
            # string describing the tuning, such as EADGBE or DADGAD
            self.tuning = ''.join([s.chroma for s in self.tuned_strings])

        else:
            # interpret a string that casts to a NoteList, like 'EADGBE'

            # separate out individual note chromas from the input string:
            tuning_chromas = NoteList([Note(n) for n in parsing.parse_out_note_names(tuning)])
            # make into a strictly ascending series of OctaveNotes:
            tuned_strings = tuning_chromas.force_octave(start_octave=2)
            self.tuned_strings = [String(s) for s in tuned_strings]
            self.tuning = ''.join([s.chroma for s in self.tuned_strings])

        self.verbose = verbose # for debugging

    # open strings are relative to capo instead of to the nut:
    @property
    def open_strings(self):
        return [s + self.capo for s in self.tuned_strings]

    @property
    def distance_from_standard(self):
        """how many semitones up/down must the strings of a standard guitar be tuned to get this tuning?"""
        distances = []
        for i, s in enumerate(self.open_strings):
            distances.append(s - tunings['standard'][i])
        return distances

    def tuning_is_natural(self):
        """returns True if tuned strings contain only natural notes, otherwise False"""
        if sum([not s.is_natural() for s in self.tuned_strings]) > 0:
            return False
        else:
            return True

    def open_is_natural(self):
        """returns True if open strings (i.e. on capo) contain only natural notes, otherwise False"""
        if sum([not s.is_natural() for s in self.open_strings]) > 0:
            return False
        else:
            return True

    def pick(self, frets, pattern=None, *args, **kwargs):
        """plays the fretted notes as audio, arpeggiated into a melody.
        accepts optional 'pattern' arg as list of string indices, e.g. [1,4,3,4]
        indicating a picking pattern that changes the order of notes"""
        notes = self[frets]
        if pattern is not None:
            notes = NoteList([notes[p] for p in pattern])
        notes.play(*args, delay=0.25, duration=3, **kwargs)

    def strum(self, frets, *args, **kwargs):
        """plays the fretted notes as audio, arpeggiated close together"""
        notes = self[frets]
        notes.play(*args, delay=0.05, duration=3, **kwargs)

    def chord(self, frets, *args, **kwargs):
        """plays the fretted notes as audio, summed into a chord"""
        notes = self[frets]
        notes.play(*args, duration=3, **kwargs)

    ### TBI: distinguish between fretting from nut and fretting from capo
    def fret(self, frets, from_capo=True):
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
                    # from nut: (unlikely anyone will ever use this)
                    if f in {0, self.capo}: # 'open', i.e. sounded from capo position
                        string_notes.append(self.open_strings[s])
                    else:
                        if f < self.capo:
                            raise Exception(f"Tried to fret on {f}, but capo on {self.capo} - can't fret beneath capo!")
                        else:
                            # increment relative to nut position, not capo position:
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
        """a Guitar object 'contains' a note if that note is in its open strings"""
        return item in self.open_strings

    def __call__(self, frets):
        """accepts a fretting pattern, prints out sounded notes, detected chord,
            and the chord diagram showing what note each string is playing"""
        return self.query(frets, return_chord=False)

    def find_key(self, include=None, exclude=None, tonic=None, display=True):
        """accepts dict arguments for 'include' and 'exclude', both of the same form,
            denoting which frets on which strings are respectively in and out of a key,
            and tries to find a key that fits those constraints.
        for example, the argument: include={1: [2,3,5], 2:[0,2]}
            means that frets 2,3,5 on the 1st string, and frets 0,2 on the 2nd string
            are to be considered 'in-key'
        optionally accepts a 'tonic' argument, which can be a Note
            or a dict with one key:value pair denoting string:fret,
            which indicates that the key's tonic is known and restricts the
            search only to keys that originate on that tonic.
        """

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

        if tonic is not None:
            if isinstance(tonic, dict):
                assert len(tonic) == 1, "if tonic arg is a dict, it must contain exactly one string:fret pair"
                for s,fret in tonic.items(): # looks hacky but is the neatest way to unpack this
                    tonic_note = (self.tuned_strings[s-1]+fret).note
            elif isinstance(tonic, str):
                tonic_note = Note(tonic)
            elif isinstance(tonic, Note):
                tonic_note = tonic
            include_notes = [tonic_note] + [n.note for n in include_notes if n.note != tonic_note]

        # dynamically adjust min_precision by the number of notes provided
        min_precision = len(include_notes) / 7

        log(f'Requiring min_precision of: {min_precision}')
        matches = matching_keys(notes=include_notes, exclude=exclude_notes, min_precision=0, tonic=tonic, display=False)

        if display:
            matching_keys(notes=include_notes, exclude=exclude_notes, min_precision=0, tonic=tonic, display=True, max_results=3)
            # show fretboard on the first 3 matches
            for m in list(matches.keys())[:3]:
                print() # i.e. newline
                self.show_key(m)
        else:
            # just return the matches themselves
            return matches

    def matching_chords(self, frets, *args, **kwargs):
        """analyses this set of frets and detects what chords they might represent"""
        notelist = self[frets]
        return matching_chords(notelist, *args, **kwargs)

    def most_likely_chord(self, frets, *args, **kwargs):
        """returns the most likely chord detected for this set of frets"""
        notelist = self[frets]
        return most_likely_chord(notelist, *args, **kwargs)

    def query(self, frets, return_notes=False, return_chord=True):
        """parses the frets passed, displays the sounded notes, the auto-detected chord,
        and shows the resulting fret diagram"""
        sounded_notes = self.fret(frets)
        print(f'Sounded notes: {sounded_notes}')
        sounded_chord = self.most_likely_chord(frets)
        print(f'Detected chord: {sounded_chord}')

        # construct Fretboard object for display:
        fret_ints = parsing.parse_out_integers(frets)
        mute = [s+1 for s in range(len(fret_ints)) if fret_ints[s] is None]
        string_contents = [(self.open_strings[s] + fret_ints[s]).chroma  if fret_ints[s] is not None  else None  for s in range(self.num_strings)]
        fret_cells = {(s+1,f):string_contents[s] for s,f in enumerate(fret_ints) if (f != 0 and f is not None)}
        Fretboard(fret_cells, index=self.tuning, mute=mute, title=f'Frets: {frets}').disp(continue_strings=True)

        if return_notes:
            return sounded_notes
        elif return_chord:
            return sounded_chord


    def locate_note(self, note, match_octave=False, min_fret=0, max_fret=13):
        """accepts a Note object, (or, if match_octave, an OctaveNote object)
        and returns a list of tuple (string,fret) locations where that note appears"""
        # keep a list of locations:
        note_locs = []
        assert isinstance(note, OctaveNote if match_octave else Note), "arg to locate_note must be a Note or OctaveNote object"
        for s, string in enumerate(self.open_strings):
            # if this open/capo'd string corresponds to that note:
            if string.chroma == note.chroma:
                # add (s,0) or (s,capo) to the list:
                if not (match_octave and (string.value != note.value)):
                    # (i.e. if match_octave is true, only add this note if its value is exactly what is desired)
                    note_locs.append((s+1,self.capo))
                # add (s,12) or (s,capo+12 to the list as well if it fits):
                if max_fret >= 12:
                    if not (match_octave and ((string.value + 12) != note.value)):
                        note_locs.append((s+1, self.capo+12))
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


    ### various methods for displaying various orpyus objects as frets:
    ### (some copy/paste here but each method has its own requirements so be kind)

    def show_octavenote(self, note, max_fret=13, min_fret=0, preserve_accidental=True, **kwargs):
        if isinstance(note, str):
            note = OctaveNote(note, prefer_sharps=('#' in note) if preserve_accidental else None)
        note_locs = self.locate_note(note, match_octave=True, max_fret=max_fret, min_fret=min_fret)
        cells = {loc: note.name for loc in note_locs}
        Fretboard(cells, title=f'Note: {note.chroma} (octave {note.octave}) on tuning:{self.name}').disp(**kwargs)

    def show_note(self, note, show_octave=True, max_fret=15, min_fret=0, preserve_accidental=True, **kwargs):
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
        Fretboard(cells, title=f'Note: {note.name} on tuning:{self.name}').disp(**kwargs)

    def show_notes(self, notes, show_octave=True, max_fret=15, min_fret=0, title=None, **kwargs):
        if not isinstance(notes, NoteList):
            notes = NoteList(notes)
        # make list of all the places where all these notes occur:
        note_locs = []
        for nt in notes:
            note_locs.extend(self.locate_note(nt, min_fret=min_fret, max_fret=max_fret))
        # populate dict of cells:
        cells = {}
        for loc in note_locs:
            string, fret = loc
            str_note = self.tuned_strings[string-1] + fret
            # show octave if desired, otherwise just the note letter itself:
            cells[loc] = str_note.name if show_octave else str_note.chroma

        #### finalise:
        if title is None:
            title=f'Notes: {notes} on tuning:{self.name}'
        Fretboard(cells, title=title).disp(**kwargs)


    def show_chord(self, chord, intervals_only=False, notes_only=False, max_fret=13, min_fret=0, preserve_accidental=True, title=None, show_index=True, **kwargs): # preserve accidentals?
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
            # determine how much space to leave for note names on index, by seeing if tuned strings contain accidentals:
            note_space = 2 if self.tuning_is_natural() else 3

            if intervals_only:
                # replace note with interval on index labels as well
                index = [f'{(chord.factor_intervals[chord.note_factors[string.note]].factor_name):>3}'
                         if string.note in chord.notes
                         else ' '*3
                         for string in self.tuned_strings ]
            elif notes_only:
                index = [f'{string.chroma:>{note_space}}'
                         if string.chroma in chord.notes
                         else ' '*note_space
                         for string in self.tuned_strings ]
            else: # notes AND intervals:
                index = [f'{(chord.factor_intervals[chord.note_factors[string.note]].factor_name):>3}:{string.chroma:<{note_space}}'
                         if string.note in chord.notes
                         else ' '*(3+note_space)
                         for string in self.tuned_strings ]

        else:
            index = [' '] * self.num_strings # list of empty strings as index



        #### finalise:
        if title is None:
            title=f'Chord: {chord} on tuning:{self.name}'
        Fretboard(cells, index=index, highlight=root_locs, title=title).disp(**kwargs)

    def show_abstract_chord(self, chord, **kwargs):
        """for a given AbstractChord object (or name that casts to AbstractChord),
        show where the notes of that chord fall on the fretboard starting from an arbitrary fret"""
        # internally: we just re-use the show_chord method, but on a higher fret and we hide the labels/indices
        if isinstance(chord, str):
            chord = AbstractChord(chord)
        a_chord = chord.on_root('A')
        self.show_chord(a_chord, fret_labels=False, show_index=False, min_fret=4, max_fret=16, intervals_only=True, title=f'{chord} on tuning:{self.name}', **kwargs)


    def show_key(self, key, intervals_only=False, notes_only=False, min_fret=0, max_fret=13, title=None, show_index=True, highlight_fifths=False, highlight_pentatonic=False, **kwargs):
        """for a given Key object (or name that casts to key),
        show where the notes of that key fall on the fretboard, starting from open."""
        if isinstance(key, str):
                key = Key(key)

        #### determine highlighted frets
        # highlight tonics:
        highlights = self.locate_note(key.tonic, max_fret=max_fret)
        if not highlight_pentatonic:
            # and, optionally, fifths:
            if highlight_fifths:
                if (5 in key.factors):
                    highlights.extend(self.locate_note(key.factor_notes[5], max_fret=max_fret))
        elif highlight_pentatonic and not key.is_pentatonic():
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
                index = [f'{(key.note_intervals[string.note].factor_name):>3}:{string.chroma}'  if string.chroma in key.notes  else ''  for string in self.tuned_strings]
        else:
            index = ['']*self.num_strings # list of empty strings as index

        #### finalise:
        if title is None:
            title = f'{key} on tuning:{self.name}'
        Fretboard(cells, index=index, highlight=highlights, title=title).disp(fret_size=7, **kwargs)

    def show_scale(self, scale, **kwargs):
        """for a given abstract Scale object (or name that casts to Scale),
        show where the notes of that scale fall on the fretboard starting from an arbitrary fret"""
        if isinstance(scale, str):
            try:
                scale = Scale(scale)
            except Exception as e:
                print(f'Could not cast string {scale} to Scale object: {e}')
        a_scale = scale.on_tonic('A')
        self.show_key(a_scale, fret_labels=False, show_index=False, min_fret=3, max_fret=13, intervals_only=True, title=f'{scale} on tuning:{self.name}', **kwargs)


    def show_progression(self, progression, **kwargs):
        from src.progressions import Progression
        # try casting to Progression type if it is not one:
        if type(progression) != Progression:
            progression = Progression(Progression)
        # we pick an arbitrary key as the tonic's root,
        # freeze the fretboard min/max display parameters,
        # and display with respect to that:
        tonic_root = Note('A')
        chord_roots = [(tonic_root + iv) for iv in progression.chord_root_intervals_from_tonic]
        abs_chords = progression.chords
        specific_chords = [c.on_root(r) for c,r in zip(progression.chords, chord_roots)]
        for numeral, ac, sc in zip(progression.as_numerals(sep=None), abs_chords, specific_chords):
            # title = f'\n{ac.short_name} on degree {numeral} of {progression.scale.name} on tuning:{self.name}'
            title = str(ac)
            self.show_chord(c, fret_labels=False, show_index=False, min_fret=4, max_fret=16, fret_size=6, intervals_only=True, title=title, **kwargs)

    def show_chord_progression(self, progression, end_fret=13, **kwargs):
        from src.progressions import ChordProgression
        # try casting to ChordProgression type if it is not one:
        if type(progression) != ChordProgression:
            progression = ChordProgression(progression)
        # just display chords in sequence:
        if 'fret_size' not in kwargs:
            kwargs['fret_size'] = 6
        print(f'{progression} on tuning:{self.name}')
        for numeral, chord in zip(progression.as_numerals(sep=None), progression.chords):
            # title=f'\n{numeral} Chord: {chord}'
            title = str(chord)
            self.show_chord(chord, title=title, end_fret=end_fret, **kwargs)

    def show(self, obj, *args, **kwargs):
        """wrapper around the show_note, show_chord, show_key etc. methods.
            accepts an arbitrary object and calls the relevant method to show it,
            with some string-parsing logic to try and understand intent"""
        from src.progressions import Progression, ChordProgression

        # we will go down this list and see if the supplied object matches any of these classes:
        classes = [ Chord, AbstractChord,
                    Key, Scale,
                    ChordProgression, Progression, ChordList,
                    Note, OctaveNote, NoteList]
        funcs = [self.show_chord, self.show_abstract_chord,
                 self.show_key, self.show_scale,
                 self.show_chord_progression, self.show_progression, self.show_chord_progression,
                 self.show_note, self.show_octavenote, self.show_notes]
        names = ['Chord', 'Chord',
                 'Key', 'Scale',
                 'Progression', 'Progression', 'Chords',
                 'Note', 'Note', 'Notes']

        found_type = False
        if not (isinstance(obj, str)): # for non strings, find the right class and function to use:
            for name, cls, func in zip(names, classes, funcs):
                if isinstance(obj, cls):
                    func(obj, *args, **kwargs)
                    break
        else: # for strings, try and figure out what they could be by disambiguating information
            if 'chord' in obj.lower():
                # could be something like 'Em chord' or 'Chord of F', so do a bunch of reps:
                for rep in ['chord', 'Chord', 'of']:
                    obj = obj.replace(rep, '')
                obj = obj.strip()
                self.show_chord(obj)
            elif 'key' in obj.lower():
                # similar, we account for 'Key of Em', or ''
                for rep in ['key', 'Key', 'of']:
                    obj = obj.replace(rep, '')
                obj = obj.strip()
                self.show_key(obj)
            else:
                # otherwise, we brute force it by Try block:
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

    #### display methods:
    @property
    def name(self):
        """uses alias like 'standard' or 'dropD' if defined, otherwise spells out the tuning"""
        if tuple(self.tuned_strings) in tuning_aliases:
            return tuning_aliases[tuple(self.tuned_strings)]
        else:
            return self.tuning

    def __str__(self):
        tuning_letters = [string.chroma for string in self.tuned_strings]
        tuning_str = ''.join(tuning_letters)
        lb, rb = self._brackets
        main_str = [f'{lb}Guitar: {tuning_str}{rb}']
        if self.capo == 0:
            return f'{lb}Guitar: {tuning_str}{rb}'
        else:
            capo_letters = [string.chroma for string in self.open_strings]
            capo_str = ''.join(capo_letters)
            return f'{lb}Guitar: {tuning_str}+{self.capo}: {capo_str}{rb}'

    def __repr__(self):
        return str(self)

    _brackets = _settings.BRACKETS['Guitar']


# some predefined common tunings:
standard = eadgbe = Guitar()
dadgad = Guitar('DADGAD')
dadgbe = dropD = dropd = Guitar('DADGBE')

# set of 'easy' open chords that can be played on standard tuning without barre:
# (subjective and personal, but the main use is for the Progression.transpose_for_guitar method)
standard_open_chord_names = {
                'A', 'Am', 'A7', 'Am7', 'Amaj7', 'Asus2', 'Asus4',
                 'B7', 'Bm7',
                 'C', 'C7', 'Cmaj7', 'Csus2', 'Cadd9',
                 'D', 'Dm', 'D7', 'Dm7', 'Dmaj7', 'Dsus2', 'Dsus4',
                 'E', 'Em', 'E7', 'Em7', 'Emaj7', 'Esus4',
                 'Fmaj7', # I still have trouble even with partial bars on Fmaj
                 'G', 'G7', 'Gmaj7',
                            }
standard_open_chords = set([Chord(c) for c in standard_open_chord_names])
