from .testing_tools import compare
from ..numerals import RomanNumeral
from ..qualities import Major, Minor

def unit_test():
    compare(RomanNumeral('III').natural_degree, 3)
    compare(RomanNumeral('biiio').natural_degree, 3)
    compare(RomanNumeral('III').accidental, 0)
    compare(RomanNumeral('biiio').accidental, -1)
    compare(RomanNumeral('III').quality, Major)
    compare(RomanNumeral('biiio').quality, Minor)
    compare(RomanNumeral('III').suffix, '')
    compare(RomanNumeral('biiio').suffix, '°')

    # this is the tricky one:
    compare(RomanNumeral('VIImaj9').suffix, 'ᐞ⁹')

    # test init by integer:
    compare(RomanNumeral.from_integer(3), RomanNumeral('III'))
    compare(RomanNumeral.from_integer(3, 'minor'), RomanNumeral('iii'))
    compare(RomanNumeral.from_integer(3, 'minor', -1), RomanNumeral('biii'))
    compare(RomanNumeral.from_integer(3, 'minor', -1), RomanNumeral('biii'))
    compare(RomanNumeral.from_integer(3, 'minor', -1, 1), RomanNumeral('biii/1'))
    compare(RomanNumeral.from_integer(3, 'minor', -1, 1, ['dim']), RomanNumeral('biiio/1'))

    # test operators:
    compare(RomanNumeral('bIII')+1, RomanNumeral('bIV'))
    compare(RomanNumeral('V7')-2 , RomanNumeral('III7'))
