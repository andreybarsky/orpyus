# muse
A Python library for handling music theory in object-oriented fashion.  
Dependencies: None (at least for now, until `audio` module is complete)  
Usage: Just clone and import:  
- `from muse import Note, Chord, Key, Progression`  

# Notes 

The `notes.Note` class represents abstract musical notes not associated with a specific octave: C, C#, D, through to B.  
When Note objects are displayed as a string, they look like: `♩C`

Notes can be initialised from a string, such as: `Note('Db')` or `Note('F#')`,  
or by an integer position, indexed starting from C, such as: `Note(0)` or `Note(7)` (which return `♩C` and `♩G` respectively)

There is also an `OctaveNote` subclass that represents notes in a specific octave, played in a specific pitch: `OctaveNote('C4')`

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
Subtracting a Note from another Note returns the  distance between them as an Interval:
- `Note('E') - Note('C')`  
  - `<4:Major Third>`  
- `OctaveNote('C5') - OctaveNote('E4')`  
  - `<8:Minor Sixth>`  


# Intervals

The `intervals.Interval` class represents spaces between notes, as a value in integer semitones.  
When Interval objects are displayed as a string, they look like: `<4:Major Third>`

Intervals can be initialised from an integer value, such as: `Interval(4)` or `Interval(-12)`. Doing so infers the interval's degree within a scale (such as 'third' or 'fourth') as well as its quality (such as 'major', 'minor', or 'perfect').

There is also an `IntervalDegree` subclass that represents intervals of an explicit degree, such as thirds or fourths.  
When displayed as a string, these look like: `«8:Augmented Fifth»`  
Finally, there is a `ExtendedInterval` subclass that represents explicit ninths, elevenths, and so on.

The `intervals` module includes all the theoretical non-negative IntervalDegrees used in music theory (up to perfect 11ths), pre-initialised for easy access under a wide range of common aliases:  
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

# Keys

The `scales.Key` represents theoretical musical keys, defined by a tonic note and a mode or quality.
When Key objects are displayed as a string, they look like: `𝄞D#m`
