# muse
A Python library for handling music theory in object-oriented fashion.

# Notes 

The `notes.Note` class represents abstract musical notes not associated with a specific octave: C, C#, D, through to B.  
When Note objects are displayed as a string, they look like: `♩C`

Notes can be initialised from a string, such as: `Note('Db')` or `Note('F#')`,  
or by an integer position, indexed starting from C, such as `Note(0)` or `Note(7)`. These return `♩C` and `♩G` respectively.

#### Operators on Notes

In addition, the `notes` module includes all the notes of the chromatic scale pre-initialised for easy access:  
`chromatic_scale`  
`> [♩C, ♩Db, ♩D, ♩Eb, ♩E, ♩F, ♩Gb, ♩G, ♩Ab, ♩A, ♩Bb, ♩B]`  
`Db`  
`> ♩Db`  

- Notes can be transposed by addition or subtraction with integers, which shifts them up or down by that many semitones:  
`Note('C') + 4`  
`> ♩E`  
`Note('Eb') - 10`  
`> ♩F`  

- Subtracting a Note from another Note returns the (unsigned) interval semitone distance between them as an Interval object:  
`Note('E') - Note('C')`  
`> <4:Major Third>`

### OctaveNotes

OctaveNotes are a subclass of Notes, with the additional property that they represent a Note within a specific octave.
When OctaveNote objects are displayed as a string, they look like: `♪C4`

OctaveNotes can be initialised from a string, such as: `OctaveNote('C4')`  
or from an integer position on an 88-note keyboard, such as: `OctaveNote(value=40)`  
or from a float pitch in Hz, such as: `OctaveNote(pitch=261.0)`  
(all of which return `♪C4`)

#### Operators on OctaveNotes

OctaveNotes inherit all the behaviour from Notes, with a couple of exceptions:  
- Transposing OctaveNotes transposes them by value, rather than position, meaning that going up/down 12 semitones does not return the same note:  
`OctaveNote('C4') + 12`  
`> ♪C5`  

- Subtracting OctaveNotes from each other returns the *signed* interval semitone distance, now that it is clear that one note can be strictly higher in pitch than another.  
`OctaveNote('C4') - OctaveNote('F3')`  
`> <7:Perfect Fifth>`  
`OctaveNote('F3') - OctaveNote('C4')`  
`> <-7:Perfect Fifth (descending)>`

# Intervals

The `intervals.Interval` class represents spaces between notes, as a value in integer semitones.  
When Interval objects are displayed as a string, they look like: `<4:Major Third>`

Intervals can be initialised from an integer value, such as: `Interval(4)` or `Interval(-12)`. Doing so infers the interval's degree within a scale (such as 'third' or 'fourth') as well as its quality (such as 'major', 'minor', or 'perfect').

### IntervalDegrees

IntervalDegrees are a subclass of Intervals, with the additional property that they explicitly represent a degree within a scale.
When displayed as a string, they look like: `«4:Major Third»`

IntervalDegrees can be initialised in the same way as Intervals, in which case the degree is automatically inferred as before:  
`IntervalDegree(8)`  
`>  «8:Minor Sixth»`  
but also allow the degree to be set explicitly, as in:  
`IntervalDegree(8, degree=5)`  
`>  «8:Augmented Fifth»`  
The interval's quality is automatically inferred from the value and degree.  

They can also be initialised directly from degree (as integer) and quality (as string, accepts common aliases), using the static method:  
`Interval.from_degree(5, 'diminished')`  
`> «6:Diminished Fifth»`  
`Interval.from_degree(5, 'ddim')`  
`> «5:Double diminished Fifth»`  

The `intervals` module also includes all the theoretical non-negative IntervalDegrees used in music theory (up to perfect 11ths), pre-initialised for easy access under a wide range of common aliases:  
`Maj3`  
`> «4:Major Third»`  
`DiminishedSeventh`  
`> «9:Diminished Seventh»`  
`P5`  
`> «7:Perfect Fifth»`

#### Interval attributes

Intervals all have the following core attributes:

-`value`: a signed integer denoting a directional distance in semitones.
-`mod`: the value % 12, denoting a distance in semitones to the nearest enharmonic note.
-`width`: the unsigned value denoting an absolute distance in semitones.
-`octave_span`: the width // 12, denoting how many total octaves this interval traverses.
-`quality`: computed from their interval value and their (implicit or explicit) degree. 
--This is one of: `'major', 'minor', 'perfect', 'augmented', 'diminished', 'double augmented', 'double diminished'`  
-`expected_degree`: the 'default' degree associated with their semitone interval value. 
-- IntervalDegrees additionally have a `degree` attribute that is explicitly set, whether or not it is the same as `expected_degree`.

#### Operators on Intervals and IntervalDegrees
