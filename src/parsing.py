#### string parsing functions
from collections import defaultdict
from .util import reverse_dict, unpack_and_reverse_dict, log
from .config import settings
import string

################### accidentals

# map semitone offset values to accidental character aliases:
offset_accidentals = {-2: ['𝄫', '♭♭', 'bb'],
                -1: ['♭', 'b'],
                 0: ['', '♮', 'N'],
                 1: ['♯', '#'],
                 2: ['𝄪', '♯♯', '##']}
# map accidental aliases to offsets:
accidental_offsets = unpack_and_reverse_dict(offset_accidentals)

def accidental_value(acc):
    return accidental_offsets[acc]

# mapping of accidental aliases to canonical ascii strings (i.e. #, ##, b, bb)
accidentals_to_ascii = {char: chars[-1] for chars in offset_accidentals.values() for char in chars}


if settings.PREFER_UNICODE_ACCIDENTALS:
    fl = flat = '♭'
    sh = sharp = '♯'
    dfl = dflat = '𝄫'
    dsh = dsharp = '𝄪'
    nat = '♮'
else:
    fl = flat = 'b'
    sh = sharp = '#'
    dfl = dflat = 'bb'
    dsh = dsharp = '##'
    nat = 'N'

preferred_accidentals = {-2: dfl, -1: fl, 0: nat, 1: sh, 2: dsh}
# map all possible accidental back to preferred chars too:
for val, chars in offset_accidentals.items():
    pref = preferred_accidentals[val]
    preferred_accidentals.update({c:pref for c in chars})


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
    return (accidental_value(char) <= -1)
def is_accidental(char):
    if len(char) == 0:
        raise ValueError("'' is technically not an accidental but this is an edge case")
    return (char in accidental_offsets.keys())
def cast_accidental(acc, max_len=1):
    """reads what might be unicode accidentals and casts to preferred accidental according to config.settings"""
    assert isinstance(acc, str) and len(acc) <= max_len, f'Invalid input to parse_accidental: {acc} (where max_len={max_len})'
    if acc in accidentals_to_ascii:
        return preferred_accidentals[acc]
    else:
        return None


################### note names
generic_note_names = ['C', f'C{sh} / D{fl}', 'D', f'D{sh} / E{fl}', 'E', 'F', f'F{sh} / G{fl}', 'G', f'G{sh} / A{fl}', 'A', f'A{sh} / B{fl}', 'B']
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

# now the preferred name of each note by preference:
preferred_note_names = {}
for preference in fl, sh:
    acc_notes = note_names_by_accidental[preference]
    nat_notes = note_names_by_accidental[''] # all the white notes
    # use natural names for white notes, and the preferred accidental for black notes:
    names = [nat_notes[p] if p in nat_notes else acc_notes[p] for p in range(12)]
    preferred_note_names[preference] = names
preferred_note_names['generic'] = generic_note_names # in rare cases where we want neither preference

natural_note_positions = set(note_positions[n] for n in natural_note_names)
valid_note_names = set(note_positions.keys())
# common note names are cached for chord init, they are just the natural notes plus the commonly typed sharp and flat accidentals:
common_note_names = set(preferred_note_names[fl] + preferred_note_names[sh]) # note that this contains duplicate notes! e.g. C# / Db



################### subscript and superscript mappings:

subscript_integers = ['₀', '₁', '₂', '₃', '₄', '₅', '₆', '₇', '₈', '₉']
superscript_integers = ['⁰', '¹', '²', '³', '⁴', '⁵', '⁶', '⁷', '⁸', '⁹']

subscript_letters = {   # lowercase only:
      'a': 'ₐ',  'e': 'ₑ',  'o': 'ₒ',  'x': 'ₓ',
      'h': 'ₕ',  'k': 'ₖ',  'm': 'ₘ',  'n': 'ₙ',
      'p': 'ₚ',  's': 'ₛ',  't': 'ₜ',  'l': 'ₗ',
      'j': 'ⱼ',  'i': 'ᵢ',  'r': 'ᵣ',  'u': 'ᵤ',
      'v': 'ᵥ', }

subscript_symbols = {
      '+': '₊',  '-': '₋',  '=': '₌',
      '(': '₍',  ')': '₎',
      }

superscript_letters = {  # lowercase: (nearly complete alphabet)
       'a': 'ᵃ',  'b': 'ᵇ',  'c': 'ᶜ',  'd': 'ᵈ',  'e': 'ᵉ',
       'f': 'ᶠ',  'g': 'ᵍ',  'h': 'ʰ',  'i': 'ⁱ',  'j': 'ʲ',
       'k': 'ᵏ',  'l': 'ˡ',  'm': 'ᵐ',  'n': 'ⁿ',  'o': 'ᵒ',
       'p': 'ᵖ',  'r': 'ʳ',  's': 'ˢ',  't': 'ᵗ',  'u': 'ᵘ', # note: no Q
       'v': 'ᵛ',  'w': 'ʷ',  'x': 'ˣ',  'y': 'ʸ',  'z': 'ᶻ',

         # uppercase:
       'A': 'ᴬ',  'B': 'ᴮ',  'D': 'ᴰ',  'E': 'ᴱ',
       'G': 'ᴳ',  'H': 'ᴴ',  'I': 'ᴵ',  'J': 'ᴶ',
       'K': 'ᴷ',  'L': 'ᴸ',  'M': 'ᴹ',  'N': 'ᴺ',
       'O': 'ᴼ',  'P': 'ᴾ',  'R': 'ᴿ',  'T': 'ᵀ',
       'U': 'ᵁ',  'V': 'ⱽ',  'W': 'ᵂ',  'Z': 'ᙆ',
       }
superscript_symbols = {
       '+': '⁺',  '-': '⁻',  '=': '⁼',
       '(': '⁽',  ')': '⁾',  '?': 'ˀ', '!': 'ᵎ',
       'Δ': 'ᐞ',  '/': 'ᐟ',  '\\': 'ᐠ', '.': 'ᐧ',
       }

# unions of them all:
superscript, subscript = {}, {}
[superscript.update(s) for s in [superscript_letters, superscript_symbols, {str(i): superscript_integers[i] for i in range(10)}]]
[subscript.update(s)   for s in [subscript_letters,   subscript_symbols,   {str(i): subscript_integers[i]   for i in range(10)}]]

# reverse mapping of either:
unscript = reverse_dict(superscript)
unscript.update(reverse_dict(subscript))

################### natural language names for numerical interval/scale degrees

num_suffixes = defaultdict(lambda: 'th', {1: 'st', 2: 'nd', 3: 'rd'})
for tens in range(20,100,10):
    # 21st, 22nd, 23rd etc for all numbers 21-23, 31-33 etc, otherwise 'th'
    num_suffixes[tens+1] = 'st'
    num_suffixes[tens+2] = 'nd'
    num_suffixes[tens+3] = 'rd'

degree_names = {1: 'unison',  2: 'second', 3: 'third',
                4: 'fourth', 5: 'fifth', 6: 'sixth', 7: 'seventh', 8: 'eighth',
                9: 'ninth', 10: 'tenth', 11: 'eleventh',
                12: 'twelfth', 13: 'thirteenth'} #, 14: 'fourteenth', 15: 'fifteenth', 16: 'sixteenth'}

multiple_names = {2: 'Double', 3: 'Triple', 4: 'Quadruple'}


################### roman numeral handling: (and associated lookups)

numerals_roman = {1: 'I', 2: 'II', 3: 'III', 4: 'IV',
                  5: 'V', 6: 'VI', 7: 'VII'}
roman_numerals = reverse_dict(numerals_roman)

# which chord modifier names map preferentially back onto roman numeral prog notation:
modifier_marks = { 'dim':  '°', 'hdim7': 'ø', # ᶲ ?
                   'aug':  '⁺',  'maj':  'ᐞ',
                   'sus':  'ˢ',  'add':  'ᵃ',
settings.CHARACTERS['unknown_chord']: settings.CHARACTERS['unknown_superscript'],
} # '⁽ᵃ⁾'}

# all numerals also get turned into modifier marks:
modifier_marks.update({str(i): superscript_integers[i] for i in range(10)})
# as well as some select superscriptable symbols:
modifier_marks.update({c: superscript_symbols[c] for c in '/+-!?'})
# but not chord alterations: (because we can't superscript sharps/flats)
modifier_marks.update({f'{acc}{i}' : f'{acc}{i}' for i in range(3,14) for acc in [sh, fl, nat]})

roman_degree_chords = {}
# render as an alias dict linking numerals to major/minor qualities:
for arabic,roman in numerals_roman.items():
    roman_degree_chords[roman] = (arabic, 0, 'major')
    roman_degree_chords[roman.lower()] = (arabic, 0, 'minor')
# and the reverse mapping, for SDC.__repr__:
degree_chords_roman = reverse_dict(roman_degree_chords)

progression_aliases = dict(roman_degree_chords)
# fractional degrees for bIII chords etc:
accidental_progression_aliases = {}
for num, (deg, acc, qual) in progression_aliases.items():
    if deg > 1:
        # loop through all possible flat signs:
        for flat_sign in offset_accidentals[-1]:
            # accidental_progression_aliases[flat_sign + num] = (round(deg-0.5, 1), qual)
            accidental_progression_aliases[flat_sign + num] = (deg, -1, qual)
    if 1 < deg < 8:
        # all possible sharp signs:
        for sharp_sign in offset_accidentals[1]:
            # accidental_progression_aliases[sharp_sign + num] = (round(deg+0.5, 1), qual)
            accidental_progression_aliases[sharp_sign + num] = (deg, +1, qual)
progression_aliases.update(accidental_progression_aliases)
# kludge: we have to specifically ignore 'dim' when reading roman numerals,
# because it is the only modifier that contains a roman numeral ('i')
progression_aliases['dim'] = 'dim'

#####  CURSED MUSIC THEORY  #####

# very niche use: 'Octave' is not technically appropriate for octatonic scales,
# and other theoretical scales with more than 7 degrees,
# so we define what else these non-Octave 'spans' might be called:
span_names = {5: 'pentave', 6: 'sexave', 7: 'septave', 8: 'octave',
              9: 'nonave', 10: 'decave', 11: 'undecave', 12: 'duodecave'}
# in practice we avoid 'sexave' etc. for pentatonic scales
# because they have eight IMPLIED degrees, some of which are skipped,
# but we do use 'nonave' in the context of octatonic scales and so on

extended_numerals = {8: 'VIII', # for octatonic scales
                     9: 'IX', 10: 'X', 11: 'XI', 12: 'XII'} # for god-knows-what
numerals_roman.update(extended_numerals)
roman_numerals.update(reverse_dict(extended_numerals))

################### note name parsing functions:

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

def begins_with_accidental(name: str):
    """checks if a string begins with an accidental substring.
        returns 1 for a single-char accidental (e.g. # or 𝄫), 2 for a two-character accidental (e.g. ## or bb)
        and False if not an accidental."""
    if len(name) >= 2 and name[:2] in accidental_offsets:
        return 2
    elif len(name) >= 1 and name[:1] in accidental_offsets:
        return 1
    else:
        return False


def begins_with_roman_numeral(name: str, allow_accidental=True, return_value=False):
    """checks if a string begins with a valid roman numeral, returns boolean.
    if allow_accidental is True, still returns True if the roman numeral
        is prefaced with a leading accidental (like 'bIII'). otherwise 'bIII' returns False.
    if return_value is True, returns the value of the numeral, including any accidental alterations as half-degrees.
        i.e. 'VII' returns 7, and 'bVII' returns 6.5
        otherwise, if return_value is False, returns the LENGTH of the numeral instead.
        i.e. a one-character numeral (like 'i') gives 1, and longer numerals give 2,3, or 4 (counting the accidental if allowed)
    in either case, returns False if the substring does not start with a numeral."""
    if allow_accidental:
        # only start measuring from where the accidental ends,
        # if this string starts with one:
        acc_idx = begins_with_accidental(name)
        acc_value = accidental_offsets[name[:acc_idx]] / 2 # i.e. 0.5 or -0.5 for a sharp or flat
        if acc_value % 1 == 0:
            acc_value = int(acc_value) # keep as integer if possible
        else:
            acc_value = round(acc_value, 1) # try and avoid floating point errors
    else:
        acc_idx = acc_value = 0
    substring = name[acc_idx:]
    # check decreasing lengths for matches to uppercase roman numeral substrings
    for l in [3,2,1]:
        contains_numeral = False
        if len(substring) >= l:
            upper_numeral = substring[:l].upper()
            if upper_numeral in roman_numerals:
                # this is a match, store length/value and break out of loop
                length, value = l, roman_numerals[upper_numeral]
                contains_numeral = True
                break
    if not contains_numeral:
        return False
    elif return_value:
        return value + acc_value
    else:
        return length + acc_idx

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

def note_split(name, graceful_fail=False, strip=True):
    """takes a string that contains a note in its first one or two characters
    (like the name of a chord, e.g. F#sus4)
    splits out the note name, and returns it along with the remaining substring
    as a (note_name, remainder) tuple.
    if graceful_fail, returns False on failure to parse instead of raising error.
    if strip, strips whitespace from the remainder string before returning."""
    note_idx = begins_with_valid_note_name(name)
    if note_idx is False:
        if graceful_fail:
            return False
        else:
            raise ValueError(f'No valid note name found in first 3 characters of: {name}')
    note_name, remainder = name[:note_idx], name[note_idx:]
    if strip:
        remainder = remainder.strip()
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


##### alteration / accidental parsing:

def is_alteration(string):
    """returns True if a string is a valid chord/scale alteration, like #5 or b11,
    and False otherwise"""
    # first find double-char accidentals: ('##', 'bb' etc.)
    if string[:2] in accidental_offsets.keys():
        return string[2:].isnumeric()
    # then regular (accidental),(numeral) pairs:
    else:
        return (is_accidental(string[0])) and (string[1:].isnumeric())

def contains_accidental(string):
    """returns True if string has any explicit accidental characters
    (not including 'b' or '#'), and False otherwise"""
    for acc_char in '♯𝄪♭𝄫♮':
        if acc_char in string:
            return True
    return False
def contains_sharp(string):
    for acc_char in '#♯𝄪':
        if acc_char in string:
            return True
    return False
def contains_flat(string):
    for acc_char in 'b♭𝄫':
        if acc_char in string:
            return True
    return False

def parse_out_alterations(string):
    """given a string that contains arbitrary characters along with alterations,
    split across a list with each alteration as its own element"""
    out_list = []
    current_item = []
    currently_alteration = False
    assert isinstance(string, str), "Can only parse alterations out of strings"
    for i, char in enumerate(string):
        if currently_alteration and char.isnumeric():
            # add to an existing alteration
            current_item.append(char)
        elif (not is_accidental(char)) or (is_accidental(char) and i<len(string) and not string[i+1].isnumeric()):
            if not currently_alteration:
                # normal string, save to current item
                current_item.append(char)
            else:
                # normal string, must be the END of an alteration, so end the current item:
                out_list.append(''.join(current_item))
                currently_alteration = False
                current_item = [char]

        else:
            # detected an accidental followed by a numeral, indicating the start of an alteration
            # end the current item:
            if len(current_item) > 0:
                out_list.append(''.join(current_item))
            # start a new one that is an alteration:
            current_item = [char]
            currently_alteration = True
    out_list.append(''.join(current_item))
    return out_list


def parse_alteration(alteration):
    """accepts a string of a single alteration like 'b5' or '#11' or '♮7' and parses it into a dict
    that keys degree to offset, such as: {5:-1} or {11:1} or {7:0}"""
    degree_chars = [c for c in alteration if c.isnumeric()]
    degree = int(''.join(degree_chars))
    offset_str = alteration[:-len(degree_chars)]
    offset = accidental_offsets[offset_str]
    return {degree: offset}


##### multi-purpose string splitting/parsing:

### TBI: allow split by blacklist instead of whitelist??
def auto_split(inp, allow='', allow_numerals=True, allow_letters=True, allow_accidentals=False, disallow=None):
    """takes a string 'inp' and automatically separates it by the first char found that is
        not in the whitelist iterable 'allow'.
        alternatively, if 'disallow' is not None and is set to a string or list of chars,
        separates along any of those chars.
    'allow' should be a string of characters that are NOT to be treated as separators.
    if 'allow_numerals' is True, allow all the digit characters from 0 to 9.
    if 'allow_letters' is True, allow all the upper and lowercase English alphabetical chars.
    all three above args are ignored if 'disallow' is set."""

    if disallow is None:
        whitelist = set(allow)
        if allow_numerals:
            whitelist.update(string.digits)
        if allow_letters:
            whitelist.update(string.ascii_letters)
        if allow_accidentals:
            whitelist.update('#♯𝄪b♭𝄫')
        blacklist = None
    else:
        blacklist = disallow
        whitelist = None

    if whitelist is not None:
        # whitelist method: move forward and find the first char not in whitelist,
        # then treat it as a sep-char (while also stripping surrounding whitespace)
        sep_char = None
        for c in inp:
            # specifically allow whitespace, to catch separators like ' - ', but look for whitespace as sep later
            if c not in whitelist and c != ' ':
                sep_char = c
                break
        if sep_char is None and ' ' in inp:
            # if no separator found yet, use whitespace if it is in the string:
                sep_char = ' '

        if sep_char is None:
            # if no separator found,
            # return input as single list item
            return [inp]
        else:
            # split along detected separator
            splits = inp.split(sep_char)
            # strip whitespace in addition: in case our sep is something like ', '
            splits = [s.strip() for s in splits]
            splits = [s for s in splits if s != ''] # omit emptystring splits (handles stacked whitespace chars in input )
            return splits

    elif blacklist is not None:
        # blacklist method: move forward and create a new substring
        # whenever a new blacklist char is encountered
        splits = []
        current_word = []
        for c in inp:
            if c not in blacklist:
                # continue building a word
                current_word.append(c)
            else:
                if len(current_word) > 0:
                    # finish this word and start a new one
                    splits.append(''.join(current_word))
                    current_word = []
        # add final word to splits too:
        splits.append(''.join(current_word))
        return splits
