from ..display import Fretboard
# from .testing_tools import compare

def unit_test():
    Fretboard({(1,6):'x', (2,5):'xo', (6,6):'xox' }).disp(fret_size=5)
    Fretboard({(1,3):'bb', (2,2):'bb', (6,9):'bb' }, mute=[3,4], highlight=(2,2)).disp(fret_size=2)
    Fretboard({(1,5):'x', (2,4):'xo', (6,9):'xox' }, mute=[3,4], highlight=[(2,4), (6,9)]).disp(continue_strings=False)
    Fretboard({(3,1):'A', (3,3):'Ab',  (3,5):'AbC', (3,7):'AbCd'}, highlight=[(3,0), (6,2), (5,3), (4,4)], mute=[1,2,4,5,6]).disp(continue_strings=False, align='cright')
