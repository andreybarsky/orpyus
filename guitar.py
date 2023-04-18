import notes as notes
from notes import Note, OctaveNote, NoteList
from chords import Chord, most_likely_chord, matching_chords
from parsing import parse_out_note_names
from util import test, transpose_nested_list
import pdb

class String(OctaveNote):
    pass

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
        else:
            default_bass = String('E2')
            tuning = tuning.strip()
            # separate out individual note chromas from the input string:
            tuning_chromas = NoteList([Note(n) for n in parse_out_note_names(tuning)])
            tuned_strings = tuning_chromas.force_octave(start_octave=2)
            self.tuned_strings = [String(s) for s in tuned_strings]

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
        resulting notes, and returns them as a NoteList together with the
        appropriate auto-detected Chord object"""
        string_notes = []

        if isinstance(frets, (list, tuple)):
            for s, f in enumerate(frets):
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
        elif isinstance(frets, str):
            # re-cast and call recursively:
            frets_list = [int(f) if f.isdigit() else None for f in frets]
            return self.fret(frets_list)
            # for s, f in enumerate(frets):
            #     if f.isdigit():
            #         # transpose the note that this string is tuned to upwards by f:
            #         string_notes.append(self.open_strings[s] + int(f))
            #     else:
            #         # don't sound this string
            #         pass
        else:
            raise TypeError(f'Guitar.fret() expected string or list of fret positions, but got: {type(frets)}')


    def __getitem__(self, frets):
        return self.fret(frets)

    def __contains__(self, item):
        return item in self.open_strings

    def __call__(self, frets):
        """accepts a fretting pattern, prints out sounded notes, detected chord,
        and the chord diagram showing what note each string is playing"""
        return chord_diagram(frets, tuning=self)

    def matching_chords(self, frets, *args, **kwargs):
        """analyses this set of frets and detects what chords they might represent"""
        notelist = self[frets]
        return matching_chords(notelist, *args, **kwargs)

    def most_likely_chord(self, frets, *args, **kwargs):
        """returns the most likely chord detected for this set of frets"""
        notelist = self[frets]
        return most_likely_chord(notelist, *args, **kwargs)

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




def chord_diagram(frets, fingerings=None, title=None, tuning='EADGBE', orientation='right', chars_between_frets=3):
    """just takes list of frets as a single string
    and outputs a nice ASCII chord diagram over six lines.

    frets should be a string of six characters, either numeric or 'x' to indicate muted string
    fingerings is an optional iterable of numerics, of the same length as non-muted strings.
      if given, we place the fingering numbers into the diagram at the corresponding frets.
      if not, we place the note names instead.

    title is an optional string to display as the title of the diagram.
      if None, it auto-detects the chord and displays its names as the title.
      if you want no title, use '' instead.

    orientation should be one of 'down' or 'right',
    controls the direction of strings (from nut to bridge)"""

    # if 'tuning' arg is a tuning str, instantiate it:
    if isinstance(tuning, str):
        guitar = Guitar(tuning)
    # otherwise, if it is an existing guitar object, just use it:
    elif isinstance(tuning, Guitar):
        guitar = tuning

    sounded_notes = guitar.fret(frets)
    sounded_chord = guitar.most_likely_chord(frets)

    print(f'\nFret positions: [{frets}] in tuning: {tuning}')
    print(f'Sounded notes: {sounded_notes}')
    if sounded_chord is not None:
        print(f'  (detected chord: {sounded_chord})\n')
        # set sharp preference of sounded notes accordingly:
        for n in sounded_notes:
            n._set_sharp_preference(sounded_chord.prefer_sharps)
    else:
        print(f'  (unknown chord)\n')

    tuning_notenames = parse_out_note_names(tuning)
    longest_tuning_note = max([len(n) for n in tuning_notenames]) # do we need 1 or 2 characters per string

    left_margin_size = longest_tuning_note+1

    sounded_notenames = [n.chroma for n in sounded_notes]
    longest_sounded_note = max([len(n) for n in sounded_notenames])

    ### parse fretting position numbers:
    int_frets = []
    fret_list = []
    for fret in frets:
        if fret.isdigit():
            int_frets.append(int(fret))
            fret_list.append(int(fret))
        else:
            fret_list.append(None)

    ### get min and max extent of fretting positions, but be sensitive to all 0s:
    fret_max = max(int_frets)
    fret_min = 0 if fret_max == 0 else min([f for f in int_frets if f != 0]) # minimum nonzero fret
    num_open_strings = sum([f==0 for f in int_frets])

    ### determine length of diagram:
    # open chords:
    if fret_max <= 4:
        num_frets_shown = max([fret_max, 3]) # diagram is at least 3 long, or 4 if we use the 4th fret
        start_fret = 1

    # chords high on the neck:
    elif fret_min >= 4:
        # truncate length of diagram
        num_frets_shown = max([(fret_max - fret_min) + 1, 3]) # at least 3
        start_fret = fret_min
    # chords that span the whole fretboard for some reason:
    else:
        num_frets_shown = fret_max
        start_fret = 1

    if start_fret == 1:
        open_leftborder    = '|'
        played_leftborder  = '|'
        muted_leftborder   = 'X'
        index_leftborder   = ' '
    else:
        open_leftborder    = '--|'
        played_leftborder  = '  |'
        muted_leftborder   = 'X |'
        # index_leftborder   = f' {start_fret-1:2}'    ### this one can be confusing
                                                       #  as it puts muted Xs on the same
                                                       # fret as the index label
        index_leftborder   = '   '

    sounded_rightborder = '--'
    muted_rightborder   = '  '

    # maybe a parameter?
    # chars_between_frets = 3
    # indices to control where fret labels get displayed:
    fret_label_idx = round(chars_between_frets / 2) - 1
    fret_label_len = chars_between_frets - fret_label_idx

    empty_fret =   ' ' * chars_between_frets + '|'
    sounded_fret = '-' * chars_between_frets + '|'
    empty_idx =    ' ' * (chars_between_frets+1)

    # note_pos is a downward counting iterator:
    note_pos = len(sounded_notes)-1
    rows = []

    # loop backwards through strings/frets:
    for s in range(5,-1,-1):

        # start the list that will become the full string row string:
        open_string_name = tuning_notenames[s]

        left_margin = f'{open_string_name:{left_margin_size}}'

        this_string = [left_margin]


        # loop through strings backward
        if fret_list[s] is None:
            # muted string
            this_string.append(muted_leftborder)
            for f in range(num_frets_shown):
                this_string.append(empty_fret)
            this_string.append(muted_rightborder)

        elif fret_list[s] == 0:
            # open string
            this_string.append(open_leftborder)
            for f in range(num_frets_shown):
                this_string.append(sounded_fret)
            this_string.append(sounded_rightborder)

            # this is a sounded note, so decrement the count:
            note_pos -= 1

        else:
            # fretted string
            fret_num = fret_list[s]

            # start building the string string:
            this_string.append(played_leftborder)
            for f in range(start_fret, start_fret+num_frets_shown):
                if f < fret_num:
                    # string up to the fretting position is muted
                    this_string.append(empty_fret)
                elif f == fret_num:
                    # create a list of chars that is the displayed fret here:
                    disp_fret = list(empty_fret)
                    if fingerings is not None:
                        disp_char = f'{fingerings[note_pos]:{fret_label_len}}'
                    else:
                        disp_char = f'{sounded_notenames[note_pos]:{fret_label_len}}'

                    note_pos -= 1
                    disp_list = list(disp_char)

                    # slice replacement char (as list of char/s) into disp_fret list:
                    disp_fret[fret_label_idx : chars_between_frets] = disp_char
                    # and convert back to string before appending:
                    this_string.append(''.join(disp_fret))

                elif f > fret_num:
                    # rest of the string is sounded
                    this_string.append(sounded_fret)
            this_string.append(sounded_rightborder)
        rows.append(''.join(this_string))

    # finally add the index:

    index_leftmargin = ' '*left_margin_size

    index = [index_leftborder, index_leftmargin]
    for f in range(start_fret, start_fret + num_frets_shown):
        # convert strings to lists for slice replacement:
        index_fret = list(empty_idx)
        disp_f = list(f'{f:{fret_label_len}}')
        # slice replace:
        index_fret[fret_label_idx-1 : chars_between_frets-1] = disp_f
        index.append(''.join(index_fret))
    rows.append(''.join(index))

    # finally, display:
    if orientation == 'right':
        pass # default behaviour
    elif orientation == 'down':
        rows = transpose_nested_list(rows)
    else:
        raise Exception("orientation must be one of: 'right' or 'down'")

    disp = '\n'.join(rows)
    print(disp)


# example:
### open chord:
#        E |---|---|---|--
#        B | C |---|---|--
#        G |---|---|---|--
#        D |   | E |---|--
#        A |   |   | C |--
#        E X   |   |   |--
#            1   2   3
#
#        ### high chord: x5453x
#        E --|---|---|---|--
#        B   | C |---|---|--
#        G   |   |   | C |--
#        D   |   | F#|---|--
#        A   |   |   | D |--
#        E X |   |   |   |--
#              3   4   5

standard = eadgbe = Guitar()
dadgad = Guitar('DADGAD')
dadgbe = dropD = dropd = Guitar('DADGBE')

if __name__ == '__main__':
    #
    # test(standard['022100'], NoteList('EBEAbBE').force_octave(2))
    # test(standard('022100'), Chord('E'))
    # test(dadgad('000000'), Chord('Dsus4'))

    # open chord:
    chord_diagram('x32010', tuning='DADGBE') # Cmaj
    # high chord:
    chord_diagram('07675x') # E7?
    # extended chord:
    chord_diagram('x1881x')
