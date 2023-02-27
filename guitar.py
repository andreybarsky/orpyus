import notes
from notes import OctaveNote
from chords import Chord
import pdb

class String(OctaveNote):
    pass

    def __call__(self, fret):
        return self + fret


tunings = {'standard': [String('E2'), String('A2'), String('D3'), String('G3'), String('B3'), String('E4')],
           'dropD':   [String('D2'), String('A2'), String('D3'), String('G3'), String('B3'), String('E4')],
           'openD':   [String('D2'), String('A2'), String('D3'), String('G3'), String('A3'), String('D4')]}

class Guitar:
    def __init__(self, tuning='standard', strings=6):
        """tuning can be one of:
        a descriptive string: standard, dropD, openD
        or a six-character string like: EADGBE, DADGAD, etc."""

        assert isinstance(tuning, str) # for now

        self.num_strings=strings

        tuning = tuning.strip().lower()
        if tuning in tunings.keys():
            self.open_strings = tunings[tuning]

        else:
            default_bass = String('E2')

            first_string_fragment = tuning[:2]
            if first_string_fragment[-1] in ['b', '#']:
                first_string_note = first_string_fragment
                string_idx = 2
            else:
                first_string_note = first_string_fragment[0]
                string_idx = 1
            # first string is going to be in octave 1 or 2, find whichever is closest to E2:
            low_bass, high_bass = String(first_string_note + '1'), String(first_string_note + '2')
            low_dist, high_dist = abs(low_bass - default_bass), abs(high_bass - default_bass)
            if low_dist < high_dist:
                first_string = low_bass
            else:
                first_string = high_bass

            self.open_strings = [first_string]
            prev_string = first_string

            while len(self.open_strings) < self.num_strings:
                string_note_fragment = tuning[string_idx : string_idx+2]
                # string_letter = tuning[string_idx]
                if string_note_fragment[-1] in ['#', 'b']:
                    string_note = tuning[string_idx: string_idx+2]
                    string_idx += 2
                else:
                    string_note = tuning[string_idx]
                    string_idx += 1

                cur_octave = prev_string.octave
                low_string, high_string = String(string_note + str(cur_octave)), String(string_note + str(cur_octave+1))
                low_dist, high_dist = (low_string - prev_string), (high_string - prev_string)
                if low_dist > 0:
                    self.open_strings.append(low_string)
                else:
                    self.open_strings.append(high_string)
                prev_string = self.open_strings[-1]

    def __call__(self, frets):
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
        # TBI: turn this into a chord, but that requires parsing the tonic of chords where their first note is not the tonic
        # requires some kind of notes.detect_chord method?
        return string_notes
