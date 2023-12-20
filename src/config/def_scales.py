

### common names for base scales are defined here, whether heptatonic or pentatonic,
### though the MODES of these subscales are specified later.
### 'base scales' are those considered to be the primary examples among their modes.
### e.g. natural major and harmonic minor are defined here, but natural minor
### and phrygian dominant are defined further down, in base_scale_mode_names.

base_scale_defines = { # base scales are defined here, modes and subscales are added later:

    #### heptatonic scales:
    '1,  2,  3,  4,  5,  6,  7': ['natural major', 'major'],
    # '1,  2, b3,  4,  5, b6, b7': ['natural minor', 'minor'],  # is a mode
    '1,  2,  3,  4,  5, b6,  7': ['harmonic major'],
    '1,  2, b3,  4,  5, b6,  7': ['harmonic minor'],
    # '1,  2,  3,  4,  5, b6, b7': ['melodic major'],   # is a mode
    '1,  2, b3,  4,  5,  6,  7': ['melodic minor', 'jazz minor', 'melodic minor ascending'], # (ascending)
    # while it's true that "melodic minor" can refer to a special scale that uses
    # the natural minor scale when descending, that is out-of-scope for now

    '1, b2, b3,  4,  5,  6,  7': ['neapolitan major', 'phrygian melodic minor'],
    '1, b2, b3,  4,  5, b6,  7': ['neapolitan minor', 'phrygian harmonic minor'],
    '1, b2,  3,  4,  5, b6,  7': ['double harmonic', 'double harmonic major'],
    '1, b2,bb3,  4,  5, b6,bb7': ['miyako-bushi'],

    #### pentatonic scales:
    '1,  2,  3,  5,  6': ['major pentatonic', 'pentatonic', 'natural major pentatonic', 'ryo'], # mode 1

    # modes of the hirajoshi / in scale:
    '1,  2, b3,  5, b6': ['hirajoshi'], # base scale with 5 modes

    # modes of the dorian pentatonic:
    '1,  2, b3,  5,  6': ['dorian pentatonic'], # base scale with modes 2 and 5
    # '1, b2,  4,  5, b7': ['kokinjoshi'], # mode 2
    # '1, b3,  4, b5, b7': ['minor b5 pentatonic'], # mode 5

    # pentatonics derived from (flattened) 9th chords:
    '1,  2,  3,  5,  7': ['blues major pentatonic', 'maj9 pentatonic', 'major 9th pentatonic'],
    '1,  2,  3,  5, b7': ['dominant pentatonic', 'dominant 9th pentatonic'],
    '1,  2, b3,  5, b7': ['pygmy', 'm9 pentatonic', 'minor 9th pentatonic'],
    '1,  2, b3,  5,  7': ['minor-major pentatonic', 'mmaj9 pentatonic'],
    '1,  2,  3, #5, b7': ['augmented pentatonic', 'aug9 pentatonic'],
    '1,  2,  3, #5,  7': ['augmented major pentatonic', 'augmaj9 pentatonic'],
    '1,  2, b3, b5,  6': ['diminished pentatonic', 'dim9 pentatonic'],
    '1, b2, b3, b5,  6': ['diminished minor pentatonic', 'dmin9 pentatonic', ],
    '1,  2, b3, b5,  b7': ['half-diminished pentatonic', 'hdim9 pentatonic'],
    '1, b2, b3, b5,  b7': ['half-diminished minor pentatonic', 'hdmin9 pentatonic'],
    '1, #2,  3,  5,  b7': ['hendrix pentatonic'],

    # misc:
    '1,  2,  4,  5,  7': ['suspended', 'suspended pentatonic'],
    '1,  3,  4,  5,  7': ['okinawan'],
    # '1, b2, b3,  5, b6': ['balinese'], # 2nd mode of okinawan scale
    '1,  2,  3,  5, b6': ['major b6 pentatonic'],

    #### scales containing chromatic intervals:
    '1, b3,  4, [b5], 5, b7': ['minor blues', 'blues', 'minor blues hexatonic'],
    # '1,  2, [b3], 3,  5,  6': ['major blues', 'major blues hexatonic'],
    '1, b2, [b3], 4,  5,  b6, [b7]': ['sakura'],
    # '1, 2, 3, 4, 5, 6, [b7],7': ['bebop dominant'],
    # '1, 2, 3, 4, 5,[b6], 6, 7': ['bebop', 'bebop major', 'barry harris', 'major 6th diminished'],
    # '1, 2,b3, 4, 5,[b6], 6, 7': ['bebop minor', 'bebop melodic minor', 'minor 6th diminished'],


    #### I found it useful to define 'hybrid' scales for key searching,
    #### to accommodate different note borrowing settings in certain genres,
    #### but these might be obsolete now given the new 'tonality' searching feature.

    # natural-harmonic hybrids:
    '1,  2,  b3,  4,  5,  b6,  b7, [7]': ['extended minor', 'chromatic minor (natural/harmonic)', 'chromatic minor NH', 'NH minor'],
    '1,  2,  b3,  4,  5,  b6, [b7], 7':  ['extended minor harmonic', 'chromatic minor (harmonic/natural)', 'chromatic minor HN', 'HN minor'],
    '1,  2,   3,  4,  5, [b6], 6,   7 ': ['extended major', 'chromatic major (natural/harmonic)', 'chromatic major NH', 'NH major'],
    '1,  2,   3,  4,  5,  b6, [6],  7 ': ['extended major harmonic', 'chromatic major (harmonic/natural)', 'chromatic major HN', 'HN major'],
    # natural-melodic hybrids:
    '1,  2,  b3,  4,  5,  b6, [6],  b7, [7]': ['full minor', 'chromatic minor (natural/melodic)', 'chromatic minor NM', 'NM minor'],
    '1,  2,  b3,  4,  5, [b6], 6,  [b7], 7 ': ['full minor melodic', 'chromatic minor (melodic/natural)', 'chromatic minor MN', 'MN minor'],
    '1,  2,   3,  4,  5, [b6], 6,  [b7], 7': ['full major', 'chromatic major (natural/melodic)', 'chromatic major NM', 'NM major'],
    '1,  2,   3,  4,  5,  b6, [6],  b7, [7] ': ['full major melodic', 'chromatic major (melodic/natural)', 'chromatic major MN', 'MN major'],
    # the missing third hybrid: 'rock scales', natural/dorian/mixo hybrids:
    '1,  2,  b3,  4,  5,  b6,  [6], b7': ['rock minor', 'chromatic minor (natural/dorian)', 'chromatic minor ND', 'ND minor'],
    '1,  2,  b3,  4,  5, [b6],  6,  b7': ['rock minor dorian', 'chromatic minor (dorian/natural)', 'chromatic minor DN', 'DN minor'],
    '1,  2,   3,  4,  5,   6, [b7],  7 ': ['rock major', 'chromatic major (natural/mixolydian)', 'chromatic major NX', 'NX major'],
    '1,  2,   3,  4,  5,   6,  b7 , [7]': ['rock major mixolydian', 'chromatic major (mixolydian/natural)', 'chromatic major XN', 'XN major'],



    # '1,  2,   3,  4,  5,[b6],  6,[b7],  7': ['full major'],
    # '1,  2,  b3,  4,  5,  b6, [6], b7, [7]': ['full minor'],

    # chromatic scale from major: (currently do not work with mode rotation)
    # '1, [b2], 2,  [b3], 3, 4, [b5], 5, [b6], 6, [b7], 7': ['chromatic major'],
    # '1, [b2], 2,  b3, [3], 4, [b5], 5, b6, [6], b7, [7]': ['chromatic minor'],

    #### rare hexatonic and octatonic scales:
    # hexatonic scales:
    '1,  2,  3, #4, #5, #6': ['whole tone', 'whole-tone'],
    '1,  2,  3, b5,  6, b7': ['prometheus'],
    '1, b2, b3, #4,  5, b7': ['tritone'],

    # octatonic scales: (these get parsed with IrregularInterval members)
    '1,  2, b3,  4, b5, b6,  6,  7': ['diminished', 'whole-half', 'wholehalf', 'whole half'],
    '1, b2, b3, b4, b5,  5,  6, b7': ['half-whole', 'halfwhole', 'half whole'],
    '1,  2,  3,  4,  5,  6, b7, 7': ['bebop dominant', 'bebop dominant octatonic'],
    '1,  2,  3,  4,  5, #5,  6, 7': ['bebop', 'bebop major', 'barry harris', 'major 6th diminished', 'bebop major octatonic', 'bebop octatonic', ],
    '1,  2, b3,  4,  5, #5,  6, 7': ['bebop minor', 'bebop melodic minor', 'bebop minor octatonic', 'minor 6th diminished'],
    '1,  2, b3,  3,  4,  5,  6, 7': ['bebop dorian', 'bebop dorian octatonic'],
}



#### if a base scale has named modes, they are defined here.
#### if a scale is detected that WOULD be a mode of a base scale, but has no
#### name given in this dict, it will be called something like: 'dorian pentatonic (3rd mode)'

base_scale_mode_names = {
                    # the diatonic base scale and its modes:
   'natural major': {1: ['ionian', 'bilawal'],
                     2: ['dorian', 'kafi'],
                     3: ['phrygian', 'bhairavi'],
                     4: ['lydian', 'kalyan'],
                     5: ['mixolydian', 'khamaj'],
                     6: ['natural minor', 'minor', 'aeolian', 'asavari',],
                     7: ['locrian']},

                     # non-diatonic heptatonic base scales and their modes:
   'melodic minor': {1: ['athenian'],
                     2: ['cappadocian', 'phrygian ♯6', 'dorian ♭2'],
                     3: ['asgardian', 'lydian augmented'],
                     4: ['acoustic', 'pontikonisian', 'lydian dominant', 'overtone'],
                     5: ['melodic major', 'olympian', 'aeolian dominant', 'mixolydian ♭6'],
                     6: ['sisyphean', 'aeolocrian', 'half-diminished'],
                     7: ['palamidian', 'altered dominant', 'super locrian']},
  'harmonic minor': {1: [],
                     2: ['locrian ♯6'],
                     3: ['ionian ♯5'],
                     4: ['ukrainian dorian', 'ukrainian minor'],
                     5: ['phrygian dominant', 'spanish gypsy', 'egyptian'],
                     6: ['lydian ♯2', 'maqam mustar'],
                     7: ['altered diminished']},
  'harmonic major': {1: [],
                     2: ['blues heptatonic', 'dorian ♭5', 'locrian ♯2♯6'],
                     3: ['phrygian ♭4', 'altered dominant ♯5'],
                     4: ['lydian minor', 'lydian ♭3', 'melodic minor ♯4'],
                     5: ['mixolydian ♭2'],
                     6: ['lydian augmented ♯2'],
                     7: ['locrian 𝄫7']},
'neapolitan minor': {1: [],
                     2: ['lydian ♯6'],
                     3: ['mixolydian augmented'],
                     4: ['romani minor', 'aeolian ♯4'],
                     5: ['locrian dominant'],
                     6: ['ionian ♯2'],
                     7: ['ultralocrian', 'altered diminished 𝄫3']},
'neapolitan major': {1: [],
                     2: ['lydian augmented ♯6'],
                     3: ['lydian augmented dominant'],
                     4: ['lydian dominant ♭6'],
                     5: ['major locrian'],
                     6: ['half-diminished ♭4', 'altered dominant #2'],
                     7: ['altered dominant 𝄫3']},
'double harmonic':  {1: ['byzantine', 'arabic', 'gypsy major', 'flamenco', 'major phrygian', 'bhairav'],
                     2: ['lydian ♯2 ♯6'],
                     3: ['ultraphrygian'],
                     4: ['hungarian minor', 'gypsy minor', 'egyptian minor', 'double harmonic minor'],
                     5: ['oriental'],
                     6: ['ionian ♯2 ♯5'],
                     7: ['locrian 𝄫3 𝄫7']},

                     # pentatonic base scales and their modes:
'major pentatonic': {1: ['pentatonic', 'natural major pentatonic', 'ryo'],
                     2: ['egyptian pentatonic'],
                     3: ['blues minor pentatonic', 'minyo', 'man gong'],
                     4: ['yo', 'ritsu', 'ritusen', 'major pentatonic II'],
                     5: ['minor pentatonic', 'natural minor pentatonic']},
       'hirajoshi': {
                     2: ['iwato', 'sachs hirajoshi'],
                     3: ['kumoi', 'kumoijoshi'],
                     4: ['hon kumoi', 'hon kumoijoshi', 'sakura pentatonic', 'in', 'in sen'],
                     5: ['amritavarshini', 'chinese', 'burrows hirajoshi']},

                     # incidental/partial mode names:
         'okinawan': {2: ['balinese']},
'dorian pentatonic': {2: ['kokinjoshi'], 5: ['minor ♭5 pentatonic']},
      'minor blues': {2: ['major blues']},}



# substring replacements for scale searching are defined here.
# these allow you to type, e.g. Scale('Δ nat') which parses to 'natural major'.
# dict key is the 'canonical' name reflected in the named scales above;
# listed dict values are the alternative names, that reduce to canonical form.

scale_name_replacements = {
      'major': ['maj', 'M', 'Δ', ],
      'minor': ['min', 'm'],
      'natural': ['nat', 'N'],
      'harmonic': ['harm', 'har', 'hic'],
      'melodic': ['melo', 'mel', 'mic'],
      'pentatonic': ['pent', '5tonic', '5t'],
      'hexatonic': ['hex', '6tonicm', '6t'],
      'octatonic': ['oct', '8tonic', '8t'],
      'mixolydian': ['mixo', 'mix'],
      'dorian': ['dori', 'dor'],
      'phrygian': ['phrygi', 'phryg'],
      'lydian': ['lydi', 'lyd'],
      'locrian': ['locri', 'loc'],
      'diminished': ['dim', 'dimin'],
      'dominant': ['dom', 'domin'],
      'augmented': ['aug', 'augm'],
      'suspended': ['sus', 'susp'],
      'neapolitan': ['naples', 'neapol', 'neapo', 'np'],
      # '#': ['sharp', 'sharpened', 'raised'],
      # 'b': ['flat', 'flattened', 'lowered'],
      '2nd': ['second'],
      '3rd': ['third'],
      '4th': ['fourth'],
      '5th': ['fifth'],
      '6th': ['sixth'],
      '7th': ['seventh'],
        }


# this dict is responsible for establishing which scales are considered 'parallel'
# to one another. this seems like it should be computational, but in practice
# it is hardcoded here since they are mostly established by convention.
# i.e. technically every diatonic mode is 'parallel' to natural major, but if
# we say 'the parallel of natural major' we usually mean the natural minor scale.

# (hardcoded since these are mostly established by convention,
# as all modes are technically parallel)
parallel_scale_names = {
      # natural and melodic major/minor are classically parallel
      # since they are modes of each other:
      'natural major': 'natural minor',
      'melodic major': 'melodic minor',
      # their other modes are all technically parallel, but here
      # we map them to those of roughly opposite 'brightness':
      'mixolydian': 'dorian',
      'phrygian': 'lydian',

      # harmonic major and minor are NOT parallel, since they
      # have different notes

      # natural pentatonics and blues scales are straightforward:
      'major pentatonic': 'minor pentatonic',
      'minor blues': 'major blues',
      # and some other scales have only one named mode, which
      # makes it the obvious candidate for a parallel:
      'okinawan': 'balinese',
      'dorian pentatonic': 'kokinjoshi',
      }
# these relations are symmetric; this dict gets reversed at runtime inside ..scales.py


# rarities of various scale names,
# used in certain places when deciding how to rank the probability of scale matches.

heptatonic_scale_names_by_rarity = {
    1: {'natural major', 'natural minor'}, #, },
    2: {'harmonic major', 'harmonic minor', 'melodic minor',
        'extended major', 'extended minor'}, # , 'minor blues', 'major blues'},
    3: {'melodic major',
        'phrygian', 'dorian',
        'lydian', 'mixolydian',
        'full major', 'full minor',},
    4: {'neapolitan major', 'neapolitan minor',
        'double harmonic', 'miyako-bushi', 'locrian'}}

other_scale_names_by_rarity = {
    1: {'major pentatonic', 'minor pentatonic'},
    2: {'minor blues', 'major blues'},
    3: set(),
    4: {'hirajoshi', 'iwato', 'kumoi', 'yo'},
}
