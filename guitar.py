import muse.notes as notes
from muse.notes import OctaveNote, NoteList
from muse.chords import Chord, most_likely_chord
from muse.parsing import parse_out_note_names
from muse.util import test
import pdb

class String(OctaveNote):
    pass

    def __call__(self, fret):
        return self + fret


tunings = {'standard': [String('E2'), String('A2'), String('D3'), String('G3'), String('B3'), String('E4')],
           'dropD':   [String('D2'), String('A2'), String('D3'), String('G3'), String('B3'), String('E4')],
           'dropC':   [String('C2'), String('G2'), String('C3'), String('F3'), String('A3'), String('D4')],
           'dropB':   [String('B1'), String('Gb2'), String('B2'), String('E3'), String('Ab3'), String('Db4')],
           'openE':   [String('E2'), String('B2'), String('E3'), String('G#3'), String('B3'), String('E4')],
           'openD':   [String('D2'), String('A2'), String('D3'), String('G3'), String('A3'), String('D4')], # aka DADGAD
           'openC':   [String('C2'), String('G2'), String('C3'), String('G3'), String('C4'), String('E4')],
           'openG':   [String('D2'), String('G2'), String('D3'), String('G3'), String('B3'), String('D4')],
           }

class Guitar:
    def __init__(self, tuning='standard', strings=6):
        """tuning can be one of:
        a descriptive string: standard, dropD, openE, etc.
        or a six-character string like: EADGBE, DADGAD, etc."""

        assert isinstance(tuning, str) # for now

        self.num_strings = strings

        if tuning in tunings.keys():
            self.open_strings = tunings[tuning]


        else:
            default_bass = String('E2')

            # cleanup:
            tuning = tuning.strip()
            # separate out individual note chromas from the input string:
            tuning_chromas = NoteList(parse_out_note_names(tuning))
            #
            open_strings = tuning_chromas.force_octave(start_octave=2)
            self.open_strings = [String(s) for s in open_strings]

            # first_string_fragment = tuning[:2]
            # if first_string_fragment[-1] in ['b', '#']:
            #     first_string_note = first_string_fragment
            #     string_idx = 2
            #     prefer_sharps = first_string_fragment[-1]  == '#' # use sharp or flat notation depending on what is used in input string
            # else:
            #     first_string_note = first_string_fragment[0]
            #     string_idx = 1
            #     prefer_sharps = True # but doesn't matter
            # # first string is going to be in octave 1 or 2, find whichever is closest to E2:
            # low_bass, high_bass = String(first_string_note + '1'), String(first_string_note + '2')
            # low_dist, high_dist = abs(low_bass - default_bass), abs(high_bass - default_bass)
            #
            # if low_dist < high_dist:
            #     first_string = low_bass
            # else:
            #     first_string = high_bass
            #
            # first_string._set_sharp_preference(prefer_sharps)
            # self.open_strings = [first_string]
            # prev_string = first_string
            #
            # while len(self.open_strings) < self.num_strings:
            #     string_note_fragment = tuning[string_idx : string_idx+2]
            #     # string_letter = tuning[string_idx]
            #     if string_note_fragment[-1] in ['#', 'b']:
            #         string_note = tuning[string_idx: string_idx+2]
            #         string_idx += 2
            #         prefer_sharps = string_note_fragment[-1] == '#'
            #     else:
            #         string_note = tuning[string_idx]
            #         string_idx += 1
            #         prefer_sharps = True # but doesn't matter
            #
            #     cur_octave = prev_string.octave
            #     low_string, high_string = String(string_note + str(cur_octave)), String(string_note + str(cur_octave+1))
            #     low_dist, high_dist = (low_string - prev_string), (high_string - prev_string)
            #     if low_dist.value > 0:
            #         self.open_strings.append(low_string)
            #     else:
            #         self.open_strings.append(high_string)
            #     prev_string = self.open_strings[-1]

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
        notes.play(*args, arpeggio=True, interval=0.3, duration=3, **kwargs)

    def strum(self, frets, *args, **kwargs):
        """plays the fretted notes as audio, arpeggiated close together"""
        notes = self[frets]
        # notes.play(*args, arpeggio=False, **kwargs)
        notes.play(*args, arpeggio=True, interval=0.05, duration=3, **kwargs)

    def chord(self, frets, *args, **kwargs):
        """plays the fretted notes as audio, summed into a chord"""
        notes = self[frets]
        # notes.play(*args, arpeggio=False, **kwargs)
        notes.play(*args, arpeggio=False, duration=3, **kwargs)

    def __getitem__(self, frets):
        """plucks each string according to the listed fret diagram, gets the
        resulting notes, and returns them as a NoteList together with the
        appropriate auto-detected Chord object"""
        string_notes = []
        if isinstance(frets, (list, tuple)):
            for s, fret in enumerate(frets):
                if isinstance(fret, int):
                    notes.append(self.open_strings[s](fret))
                elif fret is None:
                    pass
                else:
                    raise ValueError(f'Passed iterable to Guitar.__call__, expected items to be ints or None, but received item #{s}: {type(fret)}')
        elif isinstance(frets, str):
            for s, fret in enumerate(frets):
                if fret.isdigit():
                    string_notes.append(self.open_strings[s](int(fret)))
                else:
                    pass
        notes = NoteList(string_notes)
        return notes

    def __contains__(self, item):
        return item in self.open_strings

    def __call__(self, frets):
        """returns the most likely chord detected for this set of frets"""
        return most_likely_chord(self[frets])

    def __str__(self):
        tuning_letters = [string.chroma for string in self.open_strings]
        tuning_str = ''.join(tuning_letters)
        return f'|Guitar:{tuning_str}|'

    def __repr__(self):
        return str(self)


standard = Guitar()
dadgad = Guitar('DADGAD')
dadgbe = dropD = Guitar('DADGBE')

if __name__ == '__main__':

    test(standard['022100'], NoteList('EBEAbBE').force_octave(2))
    test(standard('022100'), Chord('E'))
    test(dadgad('000000'), Chord('Dsus4'))
