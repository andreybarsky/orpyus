# muse
A Python library for handling music theory in object-oriented fashion.  
Dependencies: None (at least for now, until `audio` module is complete)  
Usage: Just clone and import:  
- `from muse import Note, Chord, Key, Progression`  

(this readme is deprecated - please await a new one)

# Notes 

The `notes.Note` class represents abstract musical notes not associated with a specific octave: C, C#, D, through to B.  
When Note objects are displayed as a string, they look like: `♩C`

Notes can be initialised from a string, such as: `Note('Db')` or `Note('F#')`,  
or by an integer position, indexed starting from C, such as: `Note(0)` or `Note(7)` (which return `♩C` and `♩G` respectively)

There is also an `OctaveNote` subclass that represents notes in a specific octave, played in a specific pitch: `OctaveNote('C4')`  
These can also be initialised by calling a base Note object, with the octave as argument: `Note('C')(4)`  

The `notes` module includes all the notes of the chromatic scale pre-initialised for easy access:  
- `chromatic_scale`  
  - `[♩C, ♩Db, ♩D, ♩Eb, ♩E, ♩F, ♩Gb, ♩G, ♩Ab, ♩A, ♩Bb, ♩B]`  
- `Db`  
  - `♩Db`  

#### Note transposition
Notes can be transposed by addition or subtraction with integers, which shifts them up or down by that many semitones:  
- `Note('C') + 4`  
  - `♩E`  
- `Note('Eb') - 10`  
  - `♩F`  
- `OctaveNote('Eb5') - 10`  
  -  `♪F4`  

#### Note distance
Subtracting a Note from another Note returns the semitone distance between them as an Interval:
- `Note('C') - Note('E')`  
  - `<4:Major Third>`  
- `Note('C')(5) - Note('E')(4)`  
  - `<8:Minor Sixth>`  


# Intervals

The `intervals.Interval` class represents spaces between notes, as a value in integer semitones.  
When Interval objects are displayed as a string, they look like: `<4:Major Third>`

Intervals can be initialised from an integer value, foe example: 
- `Interval(4)`  
- `Interval(-12)`  
Doing so infers the interval's degree within a scale (such as 'third' or 'fourth') as well as its quality (such as 'major', 'minor', or 'perfect').

There is also an `IntervalDegree` subclass that represents intervals of an explicit degree, such as thirds or fourths, useful for chord detection later.  
When displayed as a string, these look like: `«8:Augmented Fifth»`  
Finally, there is a `ExtendedInterval` subclass that represents explicit ninths, elevenths, and so on, used for fancy jazz chords.

The `intervals` module includes pre-initialised IntervalDegree objects for all the theoretical non-negative intervals used in music theory (up to perfect 11ths), under a wide range of common aliases, e.g.:  
- `Maj3`  
  - `«4:Major Third»`  
- `DiminishedSeventh`  
  - `«9:Diminished Seventh»`  
- `P5`  
  - `«7:Perfect Fifth»`

#### Interval arithmetic
Intervals can be added or subtracted with other Intervals, or plain integers, the result of which is another Interval with the desired value:
- `Interval(4) + Interval(3)`  
  - `<7:Perfect Fifth>`  
- `Interval(4) - 1`  
  - `<3:Minor Third>`  
- `Interval(7) - Interval(2)`  
  - `<5:Perfect Fourth>`  

#### Interval inversion
Intervals can be negative, but the negation of an Interval specifically returns its enharmonic inversion. Compare:
- `Interval(7)`  
  - `<7:Perfect Fifth>`  
- `Interval(-7)`  
  - `<-7:Perfect Fifth (descending)>`  
- `-Interval(7)`  
  - `<-5:Perfect Fourth (descending)>`  

#### Interval equivalence
The `==` operator compares enharmonic equivalence between Intervals:
- `Interval(4) == Interval(8)`  
  - `False`  
- `Interval(4) == Interval(16)`  
  - `True`  
- `Dim5 == Aug4`  
  - `True`  
- `Interval(7) == Interval(-5) == -Interval(7)`  
  - `True`  

# Chords

The `chords.Chord` class represents collections of notes as theoretical chords.
When Chord objects are displayed as a string, they look like: `♬ F#m [♩F#, ♩A, ♩C#]`  

Chords can be initialised in a few ways:  
- Passing a theoretical chord name as a single argument:
  - `Chord('F#m')`
- Passing a chord tonic as first argument, and a chord quality as second argument, which is assumed to be major if not specified:
  - `Chord('F#', 'minor')`  
- Passing an iterable of Notes (or objects that can be cast to Notes, such as note names), which can be a list or tuple or even a string:
  -  `Chord(['F#', 'A', 'C#'])`  
  -  `Chord('F#AC#'])`  

The Chord class is clever enough to understand a wide range of common aliases, such that:

# Keys

The `scales.Key` represents theoretical musical keys, defined by a tonic note and a mode or quality.
When Key objects are displayed as a string, they look like: `𝄞F#m`

Keys can be initialised from a tonic Note (or string that can be cast to Note), and a quality, which is assumed to be major if not specified. These can be expressed as a single string argument, or split between tonic and quality:  
- `Key('F#', 'minor')`  
- `Key('F# minor')`  

As with chords, the Key class understands a wide range of aliases:
- `Key('F#m')`  
- `Key('F#min')`  
- `Key('F# natural minor')`  
- `Key('F# aeolian')`  

Keys contain an attribute `scale`, a list of the notes that belong to that key:
- `Key('F#m').scale`  
  - ` [♩F#, ♩G#, ♩A, ♩B, ♩C#, ♩D, ♩E]`  

And an attribute `chords`, a list of the triads built on those notes:
- `Key('F#m').chords`  
  - `[♬ F#m [♩F#, ♩A, ♩C#],`  
   ` ♬ G#dim [♩G#, ♩B, ♩D],`  
   ` ♬ A [♩A, ♩C#, ♩E],`  
   ` ♬ Bm [♩B, ♩D, ♩F#],`  
   ` ♬ C#m [♩C#, ♩E, ♩G#],`  
   ` ♬ D [♩D, ♩F#, ♩A],`  
   ` ♬ E [♩E, ♩G#, ♩B]]`  
   
