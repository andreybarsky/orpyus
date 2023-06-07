# orpyus
A python library for handling music theory concepts and assisting music analysis.

Full documentation is forthcoming - for now, try some of the examples below.

## Dependencies
The main package only requires Python 3.8+ - I've deliberately tried to avoid external imports where possible to make it lightweight and cross-platform - but the optional `audio` module depends on `numpy` and `sounddevice`, which will be installed as part of the setup process below.

This library has only been tested on Ubuntu Linux so far, but should in principle run fine anywhere - please let me know if you have success (or encounter problems) running it on Windows or Mac.

## Setup

First, ensure pip/setuptools/wheel are up-to-date:
```
pip install -U pip setuptools wheel
```

Clone the repo to a directory of your choice and navigate there:
```
git clone https://github.com/andreybarsky/orpyus/
cd orpyus
```

Build the package wheels and install them:
```
pip wheel . -w dist
pip install dist/orpyus*.whl
```

That should add the `orpyus` package to your Python environment. Try it by opening a Python interpreter and running:
```
from orpyus.chords import Chord
Chord('Cmaj7')
```
If that seems to run correctly, you should be able to import the rest of the modules and try the examples below.
(I recommend using interactively with something like IPython, some of the output looks nicer)

## Examples
```
# import some useful classes and functions for the examples:
from orpyus.chords import Chord, AbstractChord, matching_chords
from orpyus.scales import Scale, Subscale
from orpyus.keys import Key, matching_keys
from orpyus.guitar import Guitar
```

### Chords
The `Chord` class represents chords as combinations of specific notes
```
# chord recognition by name:
Chord('C7sus2')                  
AbstractChord('maj7')            # AbstractChords are like Chords but without a root
Chord('Ebb minor major seventh') # orpyus understands a wide range of aliases
Chord('Dm9/E')                   # inversion can be specified as slash chord

# chord recognition by (ordered) notes:
Chord('CEbGD')       # notes are parsed in ascending order; e.g. this D is recognised as a ninth, not a second
Chord('AbCEGb')      # orpyus automatically chooses sharp/flat spelling in ambiguous cases, but respects spelling when it is given 

# examine chord attributes:
Chord('Cmaj7').notes
Chord('Cmaj7').intervals
Chord('Cmaj7').factors
Chord('Cmaj7').quality

# invert or transpose chords:
Chord('Cmaj7').invert(2)    # gives Cmaj7/G
Chord('Cmaj7') + 3          # gives Ebmaj7

# add or subtract notes from chords:
Chord('Cmaj7') + 'D'    # gives Cmaj9
Chord('Cmaj7') - 'G'    # gives Cmaj7(no5)

# find matching chords from (partial or unordered) note clusters:
matching_chords('CGFB')    # recognised as a compound Cmaj7sus4

# if audio dependencies are available: sound out any chord (experimental)
Chord('Cmaj7').play()
```

### Scales/Keys
Note that orpyus distinguishes between a 'Scale' like **natural minor**, which is described as an abstract series of intervals but not on any particular tonic, and a 'Key' like ***C* natural minor**, which is a Scale built on a specific tonic and therefore comprising a specific set of notes in addition.  
(in real music theory I understand that the two words are not strongly distinguished and are often used interchangeably, but here it proves to be a useful distinction in practice)
```
### Scales
# scale recognition by name:
Scale('major')
Scale('harmonic minor')
# including rotations and exotic modes:
Scale('lydian')
Scale('phrygian dominant')

# scale recognition by intervals (as semitones from tonic):
Scale(intervals=[2, 3, 5, 7, 9, 10])

# and pentatonic Subscales:
Scale('minor').pentatonic

# explore scale harmony by building triads on every degree of a chosen scale:
Scale('minor').chords()
# or tetrads:
Scale('minor').chords(order=4)

# or list ALL the chords that can be reasonably built on a chosen degree of a scale,
# while staying in that scale:
Scale('minor').valid_chords(1) # on the root
Scale('minor').valid_chords(2) # on the second, etc.

### Keys
# key recognition by name:
Key('Bb')
Key('G harmonic minor')
Key('Dbb altered dominant')

# all of the methods that work on Scales also work on Keys:
# (but return Notes and Chords, instead of Intervals and AbstractChords)
Key('Bb').pentatonic
Key('G harmonic minor').chords(order=4)
Key('Dbb altered dominant).valid_chords(1)

# in addition, we can identify matching keys from an unordered set of chords (e.g. a progression):
matching_keys(['C', 'G', 'Am', 'E'])
matching_keys(['Dm', 'Am', 'E7'])

# or from raw (partial) notes:
matching_keys(notes='ABCEGb')

# or, for example, from the notes of a 13 chord:
matching_keys(notes=Chord('Cmaj13').notes) # lydian
matching_keys(notes=Chord('Cm13').notes) # dorian
matching_keys(notes=Chord('C13').notes) # (i.e. dominant 13) mixolydian

# if audio dependencies are available: sound out any key
Key('C lydian').play()
```

### Progressions
As with the `AbstractChord`/`Chord` and `Scale`/`Key` distinction, orpyus distinguishes between a `Progression` which is a sequence of abstract scale-chords not in any specific key (usually denoted by Roman numerals), and a `ChordProgression` which is a sequence of specific chords in a specific key.
```
# a Progression can be initialised with case-sensitive Roman numerals, 
# whether as list of strings or as a single string with some unambiguous separator char:
Progression('I-vi-IV-V')

# a Progression is implicitly in a Scale, and will try to guess that scale (between major and minor) if not specified
# but can also be specified explicitly with the 'scale' keyword arg, even if some chords conflict with the scale:
Progression('III VII I', scale='major')  
# notice that the above is outputted with annotations: '[III] [VII] I', 
# indicating that chords III and VII are not in the major scale
Progression('III VII I', scale='minor')  
# and that this one is outputted with annotations: 'III VII [I]',
# indicating that the I chord is not in the minor scale

# also notice the output of the following:
Progression('ii V i')
# which is displayed 'iiͫ  Vͪ  i', in the (auto-detected) natural minor scale
# where the 'h' diacritic indicates that the V chord is not in natural minor, but is in *harmonic* minor
# and the 'm' diacritic indicates that the ii chord is in neither natural or harmonic minor, but is in *melodic* minor

# Progressions can also be initialised from integers, which makes the 'scale' keyword arg mandatory:
Progression(1,6,4,5, scale='major')
# scales are not limited to natural major or minor, but can be any exotic mode:
Progression(1,6,4,5, scale='phrygian dominant')
# notice that this produces the correct triad chords of that scale
# e.g. the phrygian dominant progression comes out as: 'I  VI+  iv  v°'

# and the AbstractChord objects associated with the resulting progression can be accessed
# from the Progression.chords attribute:
Progression(1,6,4,5, scale='phrygian dominant').chords


```
### Guitar integration
```
# guitar class can be initialised as default (EADGBE) tuning
g = Guitar()
# or by specifying arbitrary tuning as input:
g2 = Guitar('DADGBEb')
# alternative tunings can show how far each string is tuned from standard:
g2.distance_from_standard()

# calling a Guitar object with fretting notation displays the resulting notes, chord, and fret diagram:
g('x32013')
g2('x32013')

# we can find a matching key with respect to a set of played frets,
# using this currently clunky notation:
g.find_key({1:[3], 2:[0,2,3], 3:[0,1]})
# meaning: fret 3 on the 1st (E) string, frets 0, 2 and 3 and open on the 2nd (A) string, and frets 0 and 1 on the 3rd (D) string
# which happens to match the keys of G harmonic major or C melodic minor

# but most useful: a Guitar object can show a Note, Chord, Scale or Key object on its fretboard:
# (which shows chord/scale degrees and note names by default)
g.show_chord('C7')
g.show_key('C dorian')

# experimental: plug any orpyus object into the generic Guitar.show method:
g.show(Chord('Cmmaj11'))
g.show(Scale('minor'))
g.show(Key('Am').pentatonic)
```

Please get in touch if you have any issues with getting the library to work, if you encounter any bugs, or if you manage to do anything cool/interesting with it!
