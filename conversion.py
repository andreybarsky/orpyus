from parsing import is_accidental, parse_accidental
import math

#### name-value-pitch conversion functions for OctaveNotes
# get octave and position from note value:
def oct_pos(value): # equivalent to div_mod
    value = int(value) # cast from Interval object if needed
    oct = math.floor((value+8) / 12)
    pos = (value - 4) % 12
    return oct, pos

# get note value from octave and position
def oct_pos_to_value(oct, pos):
    value = ((12*oct)-8) + pos
    return value

### name-value conversion:
def value_to_name(value, prefer_sharps=False):
    oct, pos = oct_pos(value)
    name = accidental_note_name(pos, prefer_sharps=prefer_sharps)
    note_name = f'{name}{oct}'
    return note_name

def name_to_value(name):
    # get pitch class and octave
    note_name, oct = parse_octavenote_name(name)
    # convert pitch class to position within octave:
    pos = note_positions[note_name]
    return oct_pos_to_value(oct, pos)
    # octave_value = (12*octave)-8
    # value = octave_value + note_name_value
    # return value

### pitch-value conversion
def pitch_to_value(pitch, nearest=True):
    """Given a pitch in Hz, returns the value of the corresponding piano key.
    If the pitch is not exact, will return the value of the *nearest* piano key
    instead, unless round is False, in which case will return a float of the hypothetical
    real-valued piano key corresponding to that pitch."""
    exact_key = 12 * math.log(pitch/440., 2) + 49
    if nearest:
        return round(exact_key)
    else:
        return exact_key

def value_to_pitch(value):
    """Given a piano key value (for an 88-note piano), return the corresponding
    pitch in Hz as a float."""
    value = int(value)
    pitch = 2 ** ((value-49)/12) * 440.
    return round(pitch, 2)

### pitch-name conversion
def pitch_to_name(pitch, round=True, prefer_sharps=False):
    val = pitch_to_value(pitch)
    return value_to_name(val, prefer_sharps=prefer_sharps)

def name_to_pitch(name):
    val = name_to_value(name)
    return value_to_pitch(val)

# aliases for name-value-pitch conversion:
v2n = value_to_name
n2v = name_to_value
p2v = pitch_to_value
v2p = value_to_pitch
p2n = pitch_to_name
n2p = name_to_pitch
