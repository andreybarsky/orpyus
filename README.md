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
```
# chord recognition by name:
Chord('Csus2')
AbstractChord('maj7')

# chord recognition by (ordered) notes:
Chord('CEbGD')
Chord('AbCEGb')

# examine chord attributes:
Chord('Cmaj7').notes
Chord('Cmaj7').intervals
Chord('Cmaj7').factors
Chord('Cmaj7').quality

# invert or transpose chords:
Chord('Cmaj7').invert(2)
Chord('Cmaj7') + 2

# find matching chords from (partial or unordered) note clusters:
matching_chords('CGFB')

# if audio dependencies are available: sound out any chord (experimental)
Chord('Cmaj7').play()
```

### Scales/Keys
Note that orpyus distinguishes between a 'Scale' like *natural minor*, which is described as an abstract series of intervals but not on any particular tonic, and a 'Key' like *C natural minor*, which is a Scale built on a specific tonic and therefore comprising a specific set of notes.  
(this might not be a strictly musical distinction but it proved useful in the context of this program)
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
(still under construction)

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
