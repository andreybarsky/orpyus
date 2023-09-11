from .parsing import is_accidental
from ._settings import A4_PITCH
from . import tuning
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
def pitch_to_value(pitch, nearest=True, intonation=None):
    """Given a pitch in Hz, returns the value of the corresponding piano key.
    If the pitch is not exact, will return the value of the *nearest* piano key
    instead, unless round is False, in which case will return a float of the hypothetical
    real-valued piano key corresponding to that pitch."""
    # since pitches are floats and non-exact,
    # we take a float approximation of the 'value' corresponding to that exact pitch
    # and round to nearest whole note value (if asked)
    if intonation is None:
        intonation = tuning.get_intonation()
    else:
        intonation = intonation.upper()
    if intonation == 'EQUAL': # easily calculable by formula
        exact_value = 12 * math.log(pitch/A4_PITCH, 2) + 49
        if nearest:
            return round(exact_value)
        else:
            return exact_value
    else:
        # loop through all pitches inside this octave (from the lower A, since
        # A is defined with a reference pitch), and find the nearest match
        A_octave = int(math.log(pitch,2) - math.log(440,2)) + 3
        A_value = A_octave*12 + 1
        start_val, end_val = A_value, A_value+12

        tuned_value_pitches = tuning.value_pitches[intonation]
        pitch_offsets, abs_pitch_offsets = [], []
        for v in range(start_val, end_val):
            exact_pitch = tuned_value_pitches[v]
            offset = pitch - exact_pitch
            pitch_offsets.append(offset)
            abs_pitch_offsets.append(abs(offset))
        # argmin of the absolute offsets:
        min_offset = min(abs_pitch_offsets)
        argmin = [i for i,offset in enumerate(abs_pitch_offsets) if offset==min_offset][0]
        closest_value = start_val+argmin
        if nearest:
            # this is already 'rounded' to the nearest full note, so return that:
            return closest_value
        else:
            # we'll need to interpolate logarithmically between closest notes
            # first: did we round up or down?
            remainder = pitch_offsets[argmin]
            if remainder > 0: # remainder is positive, i.e. rounded down
                next_closest_value = closest_value + 1
                lower_value, higher_value = closest_value, next_closest_value
            else: # remainder is negative, i.e. rounded up
                next_closest_value = closest_value - 1
                lower_value, higher_value = next_closest_value, closest_value
            # interpolate:
            lower_pitch, higher_pitch = tuned_value_pitches[lower_value], tuned_value_pitches[higher_value]
            lower_log, higher_log, pitch_log = [math.log(p) for p in [lower_pitch, higher_pitch, pitch]]
            # distance between the two closest notes in log scale:
            log_fraction = (pitch_log - lower_log) / (higher_log - lower_log)
            # added on top of lower note:
            exact_value = round(lower_value + log_fraction,2)
            return exact_value

def value_to_pitch(value, intonation=None):
    """Given a piano key value (for an 88-note piano), return the corresponding
    pitch in Hz as a float."""
    return tuning.get_pitch(value, intonation)
    # value = int(value)
    # pitch = 2 ** ((value-49)/12) * A4_PITCH
    # return round(pitch, 2)

### pitch-name conversion
def pitch_to_name(pitch, round=True, prefer_sharps=False):
    val = pitch_to_value(pitch)
    return value_to_name(val, prefer_sharps=prefer_sharps)

def name_to_pitch(name):
    val = name_to_value(name)
    return value_to_pitch(val)


def get_pitch(value, temperament=None):
    """returns the pitch for an OctaveNote's value"""
    # first we take the pitch of the A below the note, which is easy.
    lower_A_octave = (value-1) // 12 # the octave of that A
    lower_A_octave_dist = 4 - lower_A_octave # distance from reference A4s
    # the pitch of the lower A, by halving/doubling from reference:
    lower_A_pitch = A4_PITCH / 2**(lower_A_octave_dist)
    ## if that is THIS note, stop and return there:
    lower_A_value = 1 + (lower_A_octave*12)
    if lower_A_value == value:
        return lower_A_pitch

    # otherwise, we now adjust the reference A pitch upwards to hit the desired note
    interval_from_A = value - lower_A_value
    # retrieve the multiplicative term wrt A from tuning system:
    ratio_from_A, step_from_A = tuning.cache[tuning_system.upper()]
    pitch = lower_A_pitch * step_from_A # multiply by tuning step to get desired pitch
    return pitch



# aliases for name-value-pitch conversion:
v2n = value_to_name
n2v = name_to_value
p2v = pitch_to_value
v2p = value_to_pitch
p2n = pitch_to_name
n2p = name_to_pitch
