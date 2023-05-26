# orpyus
A python library for handling music theory concepts and assisting music analysis.

Full documentation is forthcoming - for now, try some of the examples below.

# Dependencies
None. The main functionality only requires Python 3.8+ - I've deliberately tried to avoid external imports where possible to make cross-platform setup very easy and straightforward. 

The optional *audio* module does have a few dependencies, all of which can be installed by pip: *numpy scipy matplotlib sounddevice*
(it's also only been tested on Ubuntu Linux so far, I imagine that the current sounddevice implementation for audio output doesn't work on Windows or Mac)

# Setup
Just git clone https://github.com/andreybarsky/orpyus/ to a root directory of your choice.
Then navigate to the root directory (just *above* the orpyus directory itself) and enter an interactive Python interpreter.
Then (interactively) try:
```from orpyus.chords import Chord```
```Chord('Cmaj7')```
If that works (and outputs something) you should be able to import the rest of the modules and attempt the examples below.

# Examples
```from orpyus.chords import Chord, AbstractChord
from orpyus.scales import Scale, Subscale
from orpyus.keys import Key

AbstractChord('maj13').intervals

Scale('lydian dominant')```
