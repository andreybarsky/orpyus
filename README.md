# orpyus
A python library for handling music theory concepts and assisting music analysis.

Currently in alpha, under active development.

Full documentation is forthcoming - for now, try some of the examples below.

## Dependencies
The main package only requires Python 3.8+ - I've deliberately tried to avoid external imports where possible to make it lightweight and cross-platform - but the optional `audio` module depends on `numpy` and `sounddevice`, which will be installed as part of the setup process below.
For the audio module you may also need to install:



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

Note: If you want to use the audio module you may also need to install:
```
sudo apt-get install libportaudio2
```

## Examples
```
# import some useful classes and functions for the examples:
from orpyus.chords import Chord, AbstractChord, matching_chords
from orpyus.scales import Scale
from orpyus.keys import Key, matching_keys
from orpyus.progressions import Progression, ChordProgression
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
Scale(intervals=[2, 3, 5, 7, 9, 10])      # unison-intervals of 0 and 12 on either side are assumed if not explicitly given

# parallels of major/minor scales:
Scale('major').parallel
# pentatonic Subscales of natural scales:
Scale('major').pentatonic

# pentatonic subscales of non-natural scales are not well-defined,
# but orpyus tries to construct them anyway by choosing the most consonant subset of intervals
# while preserving a scale's character: (experimental)
Scale('phrygian').pentatonic   # gives the subscale  1 ♭2 ♭3 4 ♭6 (in an attempt to preserve the characteristic phrygian ♭2)

# explore scale harmony by building triads on every degree of a chosen scale:
Scale('harmonic minor').chords()
# or tetrads:
Scale('harmonic minor').chords(order=4)

# or list ALL the chords that can be reasonably built on a chosen degree of a scale,
# while staying in that scale:
Scale('harmonic minor').valid_chords_on(1) # on the root
Scale('harmonic minor').valid_chords_on(2) # on the second, etc.
```

```
### Keys
# key recognition by name:
Key('Bb')
Key('G harmonic minor')
Key('Dbb altered dominant')

# all of the methods that work on Scales also work on Keys:
# (but return Notes and Chords, instead of Intervals and AbstractChords)
Key('Bb').pentatonic
Key('G harmonic minor').chords(order=4)
Key('Dbb phrygian dominant').valid_chords_on(1)
# and Scales can be cast to Keys using the on_tonic method:
Scale('phrygian dominant').on_tonic('C')  

# in addition, we can identify matching keys from an unordered set of chords (e.g. a progression):
matching_keys(['C', 'G', 'Am', 'E'])
matching_keys('Dm, Am, E7')   # raw strings are fine if clearly demarcated

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
Progression('III VII I', scale='minor')  
    # notice that the above is outputted with annotations:  III VII I̲
    # indicating that the I chord is not in the minor scale

# Progressions can also be initialised from integers, which makes the 'scale' keyword arg mandatory:
Progression(1,6,4,5, scale='major')
# higher-order chords (sevenths, ninths etc.) can be produced using the 'order' keyword arg:
Progression(1,6,4,5, scale='major', order=4)    # gives tetrads built over degrees 1,6,4,5 of the major scale,
                                                # displayed as as: Iᐞ⁷ vi⁷ IVᐞ⁷ V⁷

# Progression scales are not limited to natural major or minor, but can be any exotic mode:
Progression(1,6,4,5, scale='phrygian dominant')
    # notice that this produces the correct triad chords of that scale
    # e.g. the phrygian dominant progression comes out as: I  VI+  iv  v°

# the AbstractChord objects associated with the resulting progression can be accessed
# from the Progression.chords attribute:
Progression(1,6,4,5, scale='phrygian dominant').chords

# you can use Progression.analysis to view the root movements and cadences of a Progression object:
Progression('ii V i').analysis     # displays root movements as descending fifths 
                                   # and notes authentic cadential resolution
```
```
# ChordProgressions can be initialised from a sequence of chords or unambiguous chord names:
ChordProgression('C Am F G')

# just as a Progression is in a Scale, a ChordProgression is also in a Key
# which is also guessed at if not given, though this is a more difficult (and error-prone) guess:
ChordProgression('Em C G D')     # this is placed in G and not Em, 
                                 # because of the IV-I-V cadence (and implied V-I resolution at end)

# non-natural Keys will be guessed if they are better harmonic matches than natural Keys:
ChordProgression('D7 Bm Gmaj7 Am')     # gets placed in D mixolydian and parsed as: I⁷ vi IVΔ⁷ v

# but Key can also be assigned explicitly, though note this does not change the chords as given:
ChordProgression('D7 Bm Gmaj7 Am', key='D major')    # parsed as [I⁷] vi IVΔ⁷ [v], with out-of-key I⁷ and v chords

# ChordProgressions can also be initialised from a Progression instance using the Progression.on_tonic() method:
Progression('I vi IV V').on_tonic('D')

# or from a Key instance using the Key.progression() method:
Key('D').progression(1,6,4,5)

# this is handy for composing cohesive-sounding progressions in unusual keys:
Key('F lydian').progression(1,6,4,5, order=4)      # gives:  Fmaj7 Dm7 Bhdim7 Cmaj7

# and just as with Chords and Keys, any ChordProgression can be sounded out using the .play() method: (experimental)
Key('F lydian').progression(1,6,4,5, order=4).play()
```

### Guitar integration
```
# guitar class can be initialised as default (EADGBE) tuning
g = Guitar()
# or by specifying arbitrary tuning as input:
g2 = Guitar('DADGBEb')
# alternative tunings can show how far each string is tuned from standard:
g2.distance_from_standard

# calling a Guitar object with fretting notation displays the resulting notes, chord, and fret diagram:
g('x32013')
g2('x32013')

# we can find a matching key with respect to a set of played frets,
# using this currently clunky notation:
g.find_key({1:[3], 2:[0,2,3], 3:[0,1]})
    # meaning: fret 3 on the 1st (E) string, frets 0, 2 and 3 and open on the 2nd (A) string, 
    # and frets 0 and 1 on the 3rd (D) string
    # which happens to match the keys of G harmonic/melodic major, or C melodic minor

# but most useful: a Guitar object can show a Note, Chord, Scale, or Progression object on its fretboard:
# (which displays chord/scale degrees and note names by default)
g.show_chord('C7')
g.show_key('C dorian')
g.show_chord_progression('Cm E G D')

# experimental: plug any orpyus object into the generic Guitar.show method:
g.show(Chord('Cmmaj11'))
g.show(Scale('minor'))
g.show(Key('Am').pentatonic)
g.show(ChordProgression('Gm C Fm'))
```

Please get in touch if you have any issues with getting the library to work, if you encounter any bugs, or if you manage to do anything cool/interesting with it!
