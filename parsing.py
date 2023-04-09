#### string parsing functions
from collections import defaultdict
from util import reverse_dict

# note name lookups
note_names = ['C', 'C# / Db', 'D', 'D# / Eb', 'E', 'F', 'F# / Gb', 'G', 'G# / Ab', 'A', 'A# / Bb', 'B', ]
natural_note_names = ['C', 'D', 'E', 'F', 'G', 'A', 'B']

note_names_flat = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
note_names_sharp = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# for keys with 7 sharps / flats
note_names_very_flat = ['C', 'Db', 'D', 'Eb', 'Fb', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'Cb']
note_names_very_sharp = ['B#', 'C#', 'D', 'D#', 'E', 'E#', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# detect unicode notes too:
note_names_flat_unicode = [n.replace('b', '♭') for n in note_names_flat]
note_names_sharp_unicode = [n.replace('#', '♯') for n in note_names_sharp]
note_names_very_flat_unicode = [n.replace('b', '♭') for n in note_names_very_flat]
note_names_very_sharp_unicode = [n.replace('#', '♯') for n in note_names_very_sharp]
note_names_natural_unicode = [n + '♮' if len(n)== 1 else n for n in note_names]

valid_note_names = set(note_names + note_names_flat + note_names_sharp +
                       note_names_flat_unicode + note_names_sharp_unicode +
                       note_names_very_flat + note_names_very_sharp +
                       note_names_very_flat_unicode + note_names_very_sharp_unicode +
                       note_names_natural_unicode)

note_names = {'generic':            note_names,
              'flat':               note_names_flat,
              'very_flat':          note_names_very_flat,
              'very_flat_unicode':  note_names_very_flat_unicode,
              'flat_unicode':       note_names_flat_unicode,
              'sharp':              note_names_sharp,
              'very_sharp':         note_names_very_sharp,
              'sharp_unicode':      note_names_sharp_unicode,
              'very_sharp_unicode': note_names_very_sharp_unicode,
              'natural_unicode':    note_names_natural_unicode,
              }
              # 'valid':              valid_note_names}


# map any note name to its position:
note_positions = {note_name:i for i, note_name in enumerate(note_names['generic'])}
note_positions = {}
for note_list in note_names.values():
    note_positions.update({note_name:i for i, note_name in enumerate(note_list)})


num_suffixes = defaultdict(lambda: 'th', {1: 'st', 2: 'nd', 3: 'rd', 4: 'th', 5: 'th', 6: 'th', 7: 'th'})

numerals_roman = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI', 7: 'VII'}
roman_numerals = reverse_dict(numerals_roman)

degree_names = {1: 'unison',  2: 'second', 3: 'third',
                4: 'fourth', 5: 'fifth', 6: 'sixth', 7: 'seventh',
                8: 'octave', 9: 'ninth', 10: 'tenth',
                11: 'eleventh', 12: 'twelfth', 13: 'thirteenth'}

#### note name parsing functions:

# string checking/cleaning for accidental unicode characters:
def is_sharp(char):
    return (char in ['#', '♯'])
def is_flat(char):
    return (char in ['b', '♭'])
def is_accidental(char):
    return (char in ['#', 'b', '♯', '♭'])
def parse_accidental(acc):
    """reads what might be unicode accidentals and casts to '#' or 'b' if required"""
    assert len(acc) == 1
    if acc == '♭':
        return 'b'
    elif acc == '♯':
        return '#'
    elif acc in ['#', 'b']:
        return acc
    else:
        return None
        # raise ValueError(f'{acc} is not an accidental')

def is_valid_note_name(name: str, case_sensitive=False):
    """returns True if string can be cast to a Note,
    and False if it cannot (in which case it must be something else, like a Note)"""
    if not isinstance(name, str):
        return False
    # force to upper case, in case we've been given e.g. lowercase 'c', still valid
    if len(name) == 1:
        if not case_sensitive:
            return name.upper() in valid_note_names
        else:
            return name in valid_note_names
    elif len(name) == 2:
        if not case_sensitive:
            # force to upper+lower case, in case we've been given e.g. 'eb', still valid
            name2 = name[0].upper() + name[1].lower()
        else:
            name2 = name[:2]
        return name2 in valid_note_names
    else:
        return False

def begins_with_valid_note_name(name: str):
    """checks if a string contains a valid note name in its first two characters.
    returns 2 for a two-character note name, 1 for a one-character name, and False if neither."""
    if len(name) >= 2 and is_valid_note_name(name[:2]):
        # two-character note
        return 2
    elif is_valid_note_name(name[0]):
        return 1
    else:
        return False


def parse_out_note_names(note_string):
    """for some string of valid note letters, of undetermined length,
    such as e.g.: 'CAC#ADbGbE', parse out the individual notes and return
    a list of corresponding Note objects"""

    # TBI: this could be rewritten using recursive note_split?

    assert isinstance(note_string, str), f'parse_out_note_names expected str input but got: {type(note_string)}'

    first_note_fragment = note_string[:2]
    if is_accidental(first_note_fragment[-1]):
        letter, accidental = first_note_fragment
        first_note = letter + parse_accidental(accidental)
        next_idx = 2
    else:
        first_note = first_note_fragment[0]
        next_idx = 1

    assert is_valid_note_name(first_note), f'{first_note} is not a valid note name'
    note_list = [first_note]

    while next_idx < len(note_string):
        next_note_fragment = note_string[next_idx : next_idx+2]
        if is_accidental(next_note_fragment[-1]):
            letter, accidental = next_note_fragment
            next_note = letter + parse_accidental(accidental)
            next_idx += 2
        else:
            next_note = next_note_fragment[0]
            next_idx += 1
        note_list.append(next_note)
    return note_list

def note_split(name):
    """takes a string that contains a note in its first one or two characters
    (like the name of a chord, e.g. F#sus4)
    splits out the note name, and returns it along with the remaining substring
    as a (note_name, remainder) tuple"""
    note_idx = begins_with_valid_note_name(name)
    if note_idx is False:
        raise ValueError(f'No valid note name found in first two characters of: {name}')
    note_name, remainder = name[:note_idx], name[note_idx:]
    return note_name, remainder

def parse_octavenote_name(name):
    """Takes the name of an OctaveNote as a string,
    for example 'C4' or 'A#3' or 'Gb1',
    and extracts the note and octave components."""
    note_letter = name[0].upper()
    if (len(name) > 1) and is_accidental(name[1]): # check for accidental
        # check string validity:
        accidental = parse_accidental(name[1])
        note_name = note_letter + accidental
        assert note_name in valid_note_names, f"Invalid note name: {note_letter}"

        if len(name) == 2: # default to 4th octave if not specified
            octave = 4
        elif len(name) == 3:
            octave = int(name[2])
        else:
            raise ValueError(f'Provided note name is too long: {name}')
    else: # assume natural note
        # check string validity:
        assert note_letter in valid_note_names, f"Invalid note name: {note_letter}"
        note_name = note_letter

        if len(name) == 1: # default to 4th octave if not specified
            octave = 4
        elif len(name) == 2:
            octave = int(name[1])
        else:
            raise ValueError(f'Provided note name is too long: {name}')
    return note_name, octave
