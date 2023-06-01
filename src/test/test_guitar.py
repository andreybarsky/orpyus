from ..guitar import Guitar, standard
from ..notes import NoteList
from .testing_tools import compare

def unit_test():
    #
    compare(standard['022100'], NoteList('EBEAbBE').force_octave(2))
    # compare(standard('022100'), Chord('E'))
    # compare(dadgad('000000'), Chord('Dsus4'))

    # open chord:
    Guitar('DADGBE').query('x32010') # Cmaj
    # high chord:
    standard.query('07675x') # E7?
    # extended chord:
    standard.query('x1881x')

    # standard.query('x1881x')
    # standard.query('x32010')
