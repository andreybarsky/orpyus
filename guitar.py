import notes
from notes import OctaveNote

class String(OctaveNote):
    pass

    def __call__(self, fret):
        return self + fret

standard = [String('E2'), String('A2'), String('D3'), String('G3'), String('B3'), String('E4')]
dropD = [String('D2'), String('A2'), String('D3'), String('G3'), String('B3'), String('E4')]
openD = [String('D2'), String('A2'), String('D3'), String('G3'), String('A3'), String('D4')]

tunings = {'standard': standard,
           'dropD':    dropD,
           'openD':    openD}

class Guitar:
    def __init__(self, tuning='standard'):
        """tuning can be one of:
        a descriptive string: standard, dropD, openD
        or a six-character string like: EADGBE, DADGAD, etc."""

        assert isinstance(tuning, str) # for now

        tuning = tuning.strip().lower()
        if tuning in tunings:
            note_names = tunings[tuning]
            self.open_strings = [OctaveNote(n) for n in note_names]

        else:
            default_bass = String('E2')

            first_string_char = tuning[0]
            # first string is going to be in octave 1 or 2, find whichever is closest to E2:
            low_bass, high_bass = String(first_string_char + '1'), String(first_string_char + '2')
            low_dist, high_dist = abs(low_bass - default_bass), abs(high_bass - default bass)
            if low_dist < high_dist:
                first_string = low_bass
            else:
                first_string = high_bass

            self.open_strings = [first_string]
            prev_string = first_string

            string_idx = 1
            while len(tuning) < 6:
                string_letter = tuning[string_idx]
                if tuning[string_idx+1] in ['#', 'b']:
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
