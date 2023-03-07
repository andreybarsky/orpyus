#### string parsing functions

# note name lookups
note_names = ['C', 'C# / Db', 'D', 'D# / Eb', 'E', 'F', 'F# / Gb', 'G', 'G# / Ab', 'A', 'A# / Bb', 'B', ]
natural_note_names = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
# is_blacknote = [False, True, False, True, False, False, True, False, True, False, True, False]

note_names_flat = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
note_names_sharp = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


# detect unicode notes too:
note_names_flat_unicode = [n.replace('b', '♭') for n in note_names_flat]
note_names_sharp_unicode = [n.replace('#', '♯') for n in note_names_sharp]
note_names_natural_unicode = [n + '♮' if len(n)== 1 else n for n in note_names]

valid_note_names = set(note_names + note_names_flat + note_names_sharp + note_names_flat_unicode + note_names_sharp_unicode + note_names_natural_unicode)

note_names = {'generic':         note_names,
              'flat':            note_names_flat,
              'flat_unicode':    note_names_flat_unicode,
              'sharp':           note_names_sharp,
              'sharp_unicode':   note_names_sharp_unicode,
              'natural_unicode': note_names_natural_unicode,
              'valid':           valid_note_names}

num_suffixes = {1: 'st', 2: 'nd', 3: 'rd', 4: 'th', 5: 'th', 6: 'th', 7: 'th'}


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

def is_valid_note_name(name: str):
    """returns True if string can be cast to a Note,
    and False if it cannot (in which case it must be something else, like a Note)"""
    if not isinstance(name, str):
        return False
    # force to upper case, in case we've been given e.g. lowercase 'c', still valid
    if len(name) == 1:
        return name.upper() in valid_note_names
    elif len(name) == 2: # force to upper+lower case, in case we've been given e.g. 'eb', still valid
        name2 = name[0].upper() + name[1].lower()
        return name2 in valid_note_names
    else:
        return False

def parse_out_note_names(note_string):
    """for some string of valid note letters, of undetermined length,
    such as e.g.: 'CAC#ADbGbE', parse out the individual notes and return
    a list of corresponding Note objects"""

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
