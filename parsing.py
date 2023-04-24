#### string parsing functions
from collections import defaultdict
from .util import reverse_dict, unpack_and_reverse_dict, log, test

######################################## accidentals

# map semitone offset values to accidental character aliases:
offset_accidentals = {-2: ['𝄫', '♭♭', 'bb'],
                -1: ['♭', 'b'],
                 0: ['', '♮'],
                 1: ['♯', '#'],
                 2: ['𝄪', '♯♯', '##']}
# map accidental aliases to offsets:
accidental_offsets = unpack_and_reverse_dict(offset_accidentals)

def accidental_value(acc):
    return accidental_offsets[acc]

# mapping of accidental aliases to canonical ascii strings (i.e. #, ##, b, bb)
accidentals_to_ascii = {char: chars[-1] for chars in offset_accidentals.values() for char in chars}

# string checking/cleaning for accidental unicode characters:
def is_sharp(char):
    """returns True for accidentals that parse as sharps"""
    assert len(char) == 1, f'is_sharp should not be called on non-char strings'
    return (char in offset_accidentals[1])
def is_flat(char):
    """returns True for accidentals that parse as flats"""
    assert len(char) == 1, f'is_flat should not be called on non-char strings'
    return (char in offset_accidentals[-1])
def is_sharp_ish(char):
    """returns True for sharps and double sharps"""
    return (accidental_value(char) >= 1)
def is_flat_ish(char):
    """returns True for flats and double flats"""
    return (accidental_value(char) >= 1)
def is_accidental(char):
    if len(char) == 0:
        raise ValueError("'' is technically not an accidental but this is an edge case")
    return (char in accidental_offsets.keys())
def parse_accidental(acc, max_len=1):
    """reads what might be unicode accidentals and casts to ascii '#' or 'b' if required"""
    assert isinstance(acc, str) and len(acc) <= max_len, f'Invalid input to parse_accidental: {acc} (where max_len={max_len})'
    if acc in accidentals_to_ascii:
        return accidentals_to_ascii[acc]
    else:
        return None


######################################## note names
generic_note_names = ['C', 'C# / Db', 'D', 'D# / Eb', 'E', 'F', 'F# / Gb', 'G', 'G# / Ab', 'A', 'A# / Bb', 'B']
natural_note_names = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
next_natural_note = {natural_note_names[i-1]:natural_note_names[i] for i in range(1,7)}
next_natural_note['B'] = 'C'
prev_natural_note = reverse_dict(next_natural_note)

# map note names to keyboard positions (where C is 0)
note_positions = {note_name:i for i, note_name in enumerate(generic_note_names)} # surjective mapping of all possible note names
note_names_by_accidental = {c: {} for c in accidental_offsets.keys()} # dict of acc: (dict of position: name of the note in that position by that acc), of length 7

# build sharps, flats, double sharps and double flats:
for n in natural_note_names:
    for offset, accidentals in offset_accidentals.items():
        for acc in accidentals:
            acc_note_name = f'{n}{acc}' # e.g C# or D𝄫
            acc_position = (note_positions[n] + offset) % 12
            note_positions[acc_note_name] = acc_position
            note_names_by_accidental[acc][acc_position] = acc_note_name
# sort the latter dict:
for c in accidental_offsets.keys():
    pos_dict = note_names_by_accidental[c]
    note_names_by_accidental[c] = {p : pos_dict[p] for p in sorted(pos_dict.keys())}

natural_note_positions = set(note_positions[n] for n in natural_note_names)
valid_note_names = set(note_positions.keys())

# now the preferred name of each note by preference:
preferred_note_names = {}
for preference in 'b', '#':
    acc_notes = note_names_by_accidental[preference]
    nat_notes = note_names_by_accidental[''] # all the white notes
    # use natural names for white notes, and the preferred accidental for black notes:
    names = [nat_notes[p] if p in nat_notes else acc_notes[p] for p in range(12)]
    preferred_note_names[preference] = names
preferred_note_names['generic'] = generic_note_names # in rare cases where we want neither preference


#
# note_names = {  # all the notes ordered from C to B, under various aliases
#
#   'flat':         ['C',  'Db', 'D',  'Eb', 'E',  'F',  'Gb', 'G',  'Ab', 'A',  'Bb', 'B'  ],
#   'sharp':        ['C',  'C#', 'D',  'D#', 'E',  'F',  'F#', 'G',  'G#', 'A',  'A#', 'B'  ],
#   'very flat':    ['C',  'Db', 'D',  'Eb', 'Fb', 'F',  'Gb', 'G',  'Ab', 'A',  'Bb', 'Cb' ],  # for key signatures with 7 flats
#   'very sharp':   ['B#', 'C#', 'D',  'D#', 'E',  'E#', 'F#', 'G',  'G#', 'A',  'A#', 'B'  ],  # or 7 sharps
#   'double flat':  ['Dbb','Db', 'Ebb','Eb', 'Fb', 'Gbb','Gb', 'Abb','Ab', 'Bbb','Bb', 'Cbb'],
#   'double sharp': ['B#', 'B##', 'C##','D#', 'D##','E#','E##',]
#
# }

# note_names
#
# # detect unicode notes too:
# note_names_flat_unicode = [n.replace('b', '♭') for n in note_names_flat]
# note_names_sharp_unicode = [n.replace('#', '♯') for n in note_names_sharp]
# note_names_very_flat_unicode = [n.replace('b', '♭') for n in note_names_very_flat]
# note_names_very_sharp_unicode = [n.replace('#', '♯') for n in note_names_very_sharp]
# note_names_natural_unicode = [n + '♮' if len(n)== 1 else n for n in note_names]
#
# valid_note_names = set(note_names + note_names_flat + note_names_sharp +
#                        note_names_flat_unicode + note_names_sharp_unicode +
#                        note_names_very_flat + note_names_very_sharp +
#                        note_names_very_flat_unicode + note_names_very_sharp_unicode +
#                        note_names_natural_unicode)
#
# note_names = {'generic':            note_names,
#               'flat':               note_names_flat,
#               'very_flat':          note_names_very_flat,
#               'very_flat_unicode':  note_names_very_flat_unicode,
#               'flat_unicode':       note_names_flat_unicode,
#               'sharp':              note_names_sharp,
#               'very_sharp':         note_names_very_sharp,
#               'sharp_unicode':      note_names_sharp_unicode,
#               'very_sharp_unicode': note_names_very_sharp_unicode,
#               'natural_unicode':    note_names_natural_unicode,
#               }
#               # 'valid':              valid_note_names}
#
#
# # map any note name to its position:
#
# note_positions = {}
# for note_list in note_names.values():
#     note_positions.update({note_name:i for i, note_name in enumerate(note_list)})
#


######################################## natural language names for numerical interval/scale degrees

num_suffixes = defaultdict(lambda: 'th', {1: 'st', 2: 'nd', 3: 'rd', 4: 'th', 5: 'th', 6: 'th', 7: 'th'})

numerals_roman = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI', 7: 'VII'}
roman_numerals = reverse_dict(numerals_roman)



degree_names = {1: 'unison',  2: 'second', 3: 'third',
                4: 'fourth', 5: 'fifth', 6: 'sixth', 7: 'seventh', 8: 'octave',
                9: 'ninth', 10: 'tenth',
                11: 'eleventh', 12: 'twelfth', 13: 'thirteenth',  15: 'double-octave'}




#### note name parsing functions:

def is_valid_note_name(name: str, case_sensitive=True):
    """returns True if string can be cast to a Note,
    and False if it cannot (in which case it must be something else, like a Note)"""
    if not isinstance(name, str) or not (0 < len(name) < 4):
        return False
    if not case_sensitive:
        # force first char to upper case and rest to lower, in case we've been
        # given e.g. lowercase 'c' or 'eb', or 'bbb', which are all valid if not case_sensitive
        name = name[0].upper() + name[1:].lower()
    return name in note_positions
    #
    # if len(name) == 1:
    #     if not case_sensitive:
    #         return name.upper() in valid_note_names
    #     else:
    #         return name in valid_note_names
    # elif len(name) == 2:
    #     if not case_sensitive:
    #         # force to upper+lower case, in case we've been given e.g. 'eb', still valid
    #         name2 = name[0].upper() + name[1].lower()
    #     else:
    #         name2 = name[:2]
    #     return name2 in valid_note_names
    # elif len(name) == 3:
    #     if not case_sensitive:
    #         # force 'ebb' to 'Ebb', still valid
    #         name3 = name[0].upper() + name[1:3].lower()
    #     else:
    #         name3 = name[:3]
    #     return name3 in valid_note_names
    # else:
    #     return False

def begins_with_valid_note_name(name: str):
    """checks if a string contains a valid note name in its first two characters.
    returns 2 for a two-character note name, 1 for a one-character name, and False if neither."""
    if len(name) >= 3 and is_valid_note_name(name[:2], case_sensitive=True) and is_accidental(name[1:3]):
        # three-character note (e.g. E## or Gbb)
        return 3
    if len(name) >= 2 and is_valid_note_name(name[:2]):
        # two-character note
        return 2
    elif is_valid_note_name(name[0]):
        return 1
    else:
        return False

def parse_out_note_names(note_string, graceful_fail=False):
    """for some string of valid note letters, of undetermined length,
    such as e.g.: 'CAC#ADbGbE', parse out the individual notes and return
    a list of corresponding Note objects.
    if graceful_fail, returns False upon failure to parse, instead of error."""

    # TBI: this could be rewritten using recursive note_split?

    assert isinstance(note_string, str), f'parse_out_note_names expected str input but got: {type(note_string)}'

    note_list = []

    # try looking for obvious split chars first before attempting char-wise split:
    for char in '-, ':
        if char in note_string:
            note_list = note_string.split(char)
            if len(note_list) >= 2:
                looks_valid = True
                for note in note_list: # check if everything that has been split out looks like a note
                    if not is_valid_note_name(note):
                        looks_valid = False
                        break
                if looks_valid:
                    return note_list
            # otherwise continue trying to split the string into notes as normal

    # use recursive note_split to break the string apart note-by-note:
    rest = note_string
    while len(rest) > 0:
        result = note_split(rest, graceful_fail=True)
        # catch failure:
        if result is False:
            if graceful_fail:
                return False
            else:
                raise ValueError(f'Error while parsing out note names from {note_string}: No valid note names found in {rest} (note names found so far: {note_list})')

        note_name, rest = result
        if is_valid_note_name(note_name):
            note_list.append(note_name)
        else:
            raise Exception(f'Tried to parse out note names from string: {note_string}, but got invalid note name: {note_name}')
    return note_list

def parse_out_integers(integers, expected_len=None):
    """accepts a string or list of integers, or strings of integers,
    and returns a strict list of integers (or None object for non-integers)"""
    if isinstance(integers, (list, tuple)):
        ints_list = [int(i) if (isinstance(i, int) or i.isnumeric()) else None for i in integers]
    elif isinstance(integers, str):
        if ((expected_len is not None) and (len(integers) == expected_len)) or (expected_len is None):
            # simply parse numbers out of string
            ints_list = [int(i) if i.isdigit() else None for i in integers]
        else:
            # assume there must be some sep char:
            ints_list = [int(i) if i.isnumeric() else None for i in auto_split(integers)]
    else:
        raise TypeError(f'Expected iterable or string for parse_out_integers input, but got {type(integers)}')
    return ints_list

def note_split(name, graceful_fail=False):
    """takes a string that contains a note in its first one or two characters
    (like the name of a chord, e.g. F#sus4)
    splits out the note name, and returns it along with the remaining substring
    as a (note_name, remainder) tuple"""
    note_idx = begins_with_valid_note_name(name)
    if note_idx is False:
        if graceful_fail:
            return False
        else:
            raise ValueError(f'No valid note name found in first 3 characters of: {name}')
    note_name, remainder = name[:note_idx], name[note_idx:]
    return note_name, remainder

def parse_octavenote_name(name, case_sensitive=True):
    """Takes the name of an OctaveNote as a string,
    for example 'C4' or 'A#3' or 'Gb1',
    and extracts the note and octave components."""
    numbers = [n for n in name if n.isnumeric()]
    numbers_str = ''.join(numbers)
    note_name = name[:-len(numbers)]
    assert numbers_str == name[-len(numbers):], f'Could not parse OctaveNote name: {name}, the numbers seem to be in weird places'
    octave = int(numbers_str)

    if not case_sensitive:
        note_name = note_name.capitalize()

    if is_valid_note_name(note_name):
        return note_name, octave

    # if (len(name) > 1) and is_accidental(name[1]): # check for accidental
    #     # check string validity:
    #     accidental = parse_accidental(name[1])
    #     note_name = note_letter + accidental
    #     assert note_name in valid_note_names, f"Invalid note name: {note_letter}"
    #
    #     if len(name) == 2: # default to 4th octave if not specified
    #         octave = 4
    #     elif len(name) == 3:
    #         octave = int(name[2])
    #     else:
    #         raise ValueError(f'Provided note name is too long: {name}')
    # else: # assume natural note
    #     # check string validity:
    #     assert note_letter in valid_note_names, f"Invalid note name: {note_letter}"
    #     note_name = note_letter
    #
    #     if len(name) == 1: # default to 4th octave if not specified
    #         octave = 4
    #     elif len(name) == 2:
    #         octave = int(name[1])
    #     else:
    #         raise ValueError(f'Provided note name is too long: {name}')
    # return note_name, octave


def parse_alteration(alteration):
    """accepts an alteration string like 'b5' or '#11' or '7' and parses it into a dict
    that keys degree to offset, such as: {5:-1} or {11:1} or {7:0}"""
    degree_chars = [c for c in alteration if c.isnumeric()]
    degree = int(''.join(degree_chars))
    offset_str = alteration[:-len(degree_chars)]
    offset = accidental_offsets[offset_str]
    return {degree: offset}


def unit_test():
    test(parse_out_note_names('CbbBbAGbE##C'), ['Cbb', 'Bb', 'A', 'Gb', 'E##', 'C'])
    test(parse_out_note_names('Cbb-Bb-A-Gb-E##-C'), ['Cbb', 'Bb', 'A', 'Gb', 'E##', 'C'])
    test(parse_alteration('b5'), {5:-1})
    test(parse_alteration('#11'), {11:+1})
    test(parse_alteration('7'), {7:0})

if __name__ == '__main__':
    unit_test()
