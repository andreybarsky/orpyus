from dataclasses import dataclass
# load preferred accidental characters: (specified in .settings)
from ..parsing import sh, fl, dsh, dfl, nat


### chord types and their names - for example, 'm7' and 'sus4' and 'add9' are defined in this module.
### new chord types (or aliases for existing types) can be freely added by following the examples below,
### where hopefully the template is self-explanatory.

### first, some overhead: a chord definition starts from a major triad and includes one or more of the following keywords
@dataclass
class ChordDef:
    add: dict = None # added note, in the form {degree: quality}
    # for example a dom7 chord is given by add={7:-1}, indicating a lowered 7th degree
    remove: int = None # removed tone, by degree. for example a power chord is given by: remove=3
    modify: dict = None # altered degree, in the form degree:alteration. for example,
    make: dict = None
    verify: int or dict = None # does not modify the chord, but checks whether a certain degree exists already, and makes this definition only valid if it does.
    # for example, an augmented chord is given by: modify={5:+1}, verify={3:0}, meaning a raised 5th produces an augmented chord, but only when the 3rd exists and is unaltered (major); i.e. there is no 'minor aug' chord.

### chords can also be defined as concatenations
### of existing chord types. for example, if 'dim' and '7' are already defined types, we can say 'm7b5': ['dim', '7']

### specific degree alterations, such as 'b7' or '♯5', are defined procedurally and do not need to be listed below. they are treated as 'make' parameters,
### and can be used in explicit concatenations as above, e.g. 'hendrix' = ['7', '♯9'], meaning a dom7 chord with a ♯9 on top

# modifiable 'base' chord types are defined here, i.e. chords constructed from a single named term.
# 'compound' chords of multiple terms (mostly adds and suspensions, like 'maj9sus2' or 'm7add11'
# are procedurally generated inside ..chords.py from the definitions given here.

chord_types =  {
    'm': ChordDef(make={3:-1}),
    '5': ChordDef(remove=3, verify={5:0}),
    'dim': ChordDef(make={3:-1, 5:-1}),         # dimininished chord (m3+m3)
    'aug': ChordDef(modify={5:+1}, verify={3:0}),   # augmented chord (M3+M3)
    '6': ChordDef(add=6),                         # 6 chord aka add6

    '7': ChordDef(add={7:-1}), # dominant 7th
    'dim7': ChordDef(make={3:-1, 5:-1}, add={7:-2}),
    # '7b5': ChordDef(add={7: -1}, modify={5:-1}),

    # note: m7, m9 etc. are implicit concatenations of 'm' and '7', '9' etc.
    # and mmaj7 is an implicit concatenation of 'm' and 'maj7'

    # but maj7 is NOT a concatenation of 'maj' and '7', since '7' implies dominant:
    'maj7': ChordDef(add={7: 0}),
    # 'maj7b5': ChordDef(add={7: 0}, modify={5:-1}),

    ### explicit concatenations: (for chords that ought to be recognised during chord name searching)

    #
    'm6': ['m', '6'],
    'hdim7': ['dim', '7'],    # half diminished 7th (diminished triad with minor 7th), also called m7b5
    '9': ['7', '♮9'],          # i.e. dominant 9th
    'maj9': ['maj7', '♮9'],    # major 9th
    f'7{fl}9': ['7', '♭9'],        # dominant minor 9th, (i.e. dm9?)
    'dim9': ['dim7', '♮9'],    # diminished 9th
    'dmin9': ['dim7', '♭9'],   # diminished minor 9th
    'hdim9': ['hdim7', '♮9'],  # half diminished 9th
    'hdmin9': ['hdim7', '♭9'],   # half diminished minor 9th
    f'7{sh}9': ['7', '♯9'],        # dominant 7 sharp 9, i.e. Hendrix chord

    '11': ['9', '♮11'],        # dominant 11th
    'maj11': ['maj9', '♮11'],  # major 11th
    'dmin11': ['dmin9', '♮11'],  # diminished minor 11th
    'hdim11': ['hdim9', '♮11'],  # half-diminished 11th
    'hdmin11': ['hdmin9', '♮11'],  # half-diminished minor 11th

    '13': ['11', '♮13'],               # dominant 13th
    'maj13': ['maj11', '♯11', '♮13'],  # major 13th with a raised 11th
    f'maj13{nat}11': ['maj11', '♮13'],         # major 13th WITHOUT raised 11th
    'dmin13': ['dmin11', '♮13'],  # diminished minor 11th
    'hdim13': ['hdim11', '♮13'],  # half-diminished 11th
    'hdmin13': ['hdmin11', '♮13'],  # half-diminished minor 11th
    }


# chord 'tweaks' are the extra terms that could create compound chords by tweaking an existing chord type,
# as well as being base chords themselves on their own.
# note that this dict order is non-arbitrary; it affects the order in which chords get named (e.g. add9sus4 instead of sus4add9)
chord_tweaks = {
    'sus4': ChordDef(remove=3, add=4, verify={2:False}),
    'sus2': ChordDef(remove=3, add=2, verify={4:False}),

    'add4': ChordDef(add=4, verify={9: False, 11:False}), # are these real? or just add11s

    'add9': ChordDef(add={9:0}, verify={7: False, 2:False}),
    'add11': ChordDef(add=11, verify={9: False, 4:False}),
    'add13': ChordDef(add=13, verify={11: False, 6:False, 5:0, 7:True}), # verify natural 5 is a kludge, see: Bbdim9add13/C

    '(no5)': ChordDef(remove=5), # , verify={3: True, 10:False}),    # we don't need verifiers on this because no5s are not registered anywhere, just treated as a valid input
    f'({fl}5)': ChordDef(make={5:-1}, verify={3:0}),
    }


# we rank chords by their rarity for purposes such as searching and note-matching
# this is a subjective list but it does the job:
chord_names_by_rarity = { 0: ['', 'm', '7', '5'],   # basic chords: major/minor triads, dominant sevenths, and power chords
                          1: ['m7', 'maj7', 'dim', 'sus4', 'sus2', 'add9'], # maj/min7s, dim triads, and common melodic alterations
                          2: ['9', 'maj9', 'm9', 'aug', '6', 'm6'],
                          3: ['dim7', 'hdim7', 'aug7', 'mmaj7', f'7{fl}5', f'7{sh}9', f'7{fl}9', f'({fl}5)'],
                          4: ['dim9', 'dmin9', 'mmaj9', 'hdmin9', 'dimM7', 'augM7', 'augM9', 'maj13'] + [f'{q}{d}' for q in ('', 'm', 'maj') for d in (11,13)],
                          5: [f'maj13{nat}11', 'add11'] + [f'{q}{d}' for q in ('dim', 'mmaj') for d in (11,13)],
                          6: [], 7: [], 8: [], 9: []}

# the rarity of more complex chords, i.e. combinations of these (e.g. 'maj7sus2add11')
# are calculated dynamically based on the rarities of the component chord types, in src/chords.py


# string replacement aliases for interval quality types:
quality_aliases = {'major': ['maj', 'M'],
           'minor': ['min', 'm'],
           'perfect': ['indeterminate', 'ind', 'I', 'null', 'perf', 'per', 'P'],
           'augmented': ['aug', 'A', '+'],
           'diminished': ['dim', 'd', '°', 'o', '0'],
           'doubly augmented': ['aaug', 'AA'],
           'doubly diminished': ['ddim', 'dd']}


# string replacement aliases for chord types/modifiers:
modifier_aliases = {
   'maj' : ['major', 'M', 'Δ', 'ᐞ'],
    'm'  : ['minor', 'min', '-',],
    'sus': ['suspended', 's', 'ˢ'],
    'dim': ['diminished', 'o', '°',],
    'aug': ['augmented', '+', '⁺'],
    # special case: the chord 'half-dim' is implicitly a 7th, but 'hdim7' is clearer than 'hdim'
'hdim7': ['ø', 'ø7', 'hdim', 'half-diminished', 'half-dim', 'm7b5', 'm7♭5', 'tristan'],
    'add' : ['added', 'ᵃ'],
'(no5)': ['no5', '(omit5)'],

    # bit of a kludge; but 'domX' always refers to an 'X' chord,
    # so we map 'dom' to nothing and it all works fine
        '': ['dominant', 'dom'],

    # another kludge: "maj7", "maj9" in particular need to be caught as
    # explicit concatenations, since 'maj7' is not a concetenation of 'maj' and '7':
    'maj7': ['maj7', 'add7'],
    # (add7 is an awkward case because a maj7 shouldn't really be called that,
    # but if you DO say 'add7' it implies a natural rather than a flat 7)
    'maj9': ['maj9'],
'maj11': ['maj11'],
'maj13': ['maj13'],

       '2': ['two', '2nd', 'second', '²'],
       '3': ['three', '3rd', 'third', '³'],
       '4': ['four', '4th', 'fourth', '⁴'],
       '5': ['five', '5th', 'fifth', '(no3)', 'power', 'power chord', '⁵'],
       '6': ['six', '6th', 'sixth', 'add6', '⁶'],
       '7': ['seven', '7th', 'seventh', '⁷'],
       '8': ['eight', '8th', 'eighth', '⁸'],
       '9': ['nine', '9th', 'ninth', '⁹'],
      '10': ['ten', '10th', 'tenth', '¹⁰'],
      '11': ['eleven', '11th', 'eleventh', '¹¹'],
      '12': ['twelve', '12th', 'twelfth', '¹²'],
      '13': ['thirteen', '13th', 'thirteenth', '¹³'],

    # special edge cases, otherwise 'dmin9' etc. doesn't parse correctly:
   'hdim9': ['hdim9', 'ø9'],
  'hdim11': ['hdim11', 'ø11'],
  'hdim13': ['hdim13', 'ø13'],
  'hdmin9': ['hdmin9', 'hdimm9', 'hdimmin9'],
 'hdmin11': ['hdmin11', 'hdimm11', 'hdimmin11'],
 'hdmin13': ['hdmin13', 'hdimm13', 'hdimmin13'],
   'dmin9': ['dmin9', 'dimm9', 'dimmin9'],
  'dmin11': ['dmin11', 'dimm11', 'dimmin11'],
  'dmin13': ['dmin13', 'dimm13', 'dimmin13'],
 f'7{fl}9': ['dm9', 'domin9', 'domm9'],
 f'7{sh}9': ['hendrix', 'purple haze'],

# map all accidentals back onto their preferred char
# (as determined in settings)
        sh: ['#', '♯', 'sh', 'sharpened', 'sharped', 'raised'],
        fl: ['b', '♭', 'fl', 'flattened', 'flatted', 'lowered'],
       dsh: ['𝄪', '♯♯', '##', 'dsh'],
       dfl: ['𝄫', '♭♭', 'bb', 'dfl'],
       nat: ['♮', 'N', 'with', 'include', 'nat', 'natural'],
}
