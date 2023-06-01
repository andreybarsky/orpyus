from ..notes import *
from .testing_tools import compare

def unit_test():
    ### magic method tests:
    # Notes:
    compare(C+2, D)
    compare(D-2, C)
    compare(D-C, 2)
    compare(C+Interval(4), E)

    # OctaveNotes:
    compare(OctaveNote('C4')+15, OctaveNote('Eb5'))

    # NoteList:
    compare(NoteList('CEG'), NoteList(['C', 'E', 'G']))
    compare(NoteList('CEG'), NoteList('C', 'E', 'G'))

    nl = NoteList('CEG')

    # test double sharps and double flats:

    compare(Note('Ebb'), Note('C𝄪'))
    compare(Note('E𝄫'), Note('C##'))

    # test matching chords:
    compare(NoteList('CEG').most_likely_chord().intervals, IntervalList(0,4,7))
