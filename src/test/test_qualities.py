from ..qualities import Quality, ChordModifier, parse_chord_modifiers, cast_alterations
from .testing_tools import compare

def unit_test():
    # test quality initialisation:
    compare(Quality('major'), Quality('M'))
    compare(Quality('Indeterminate'), Quality(value=0))
    # test quality inversion:
    compare(~Quality('major'), Quality('minor'))
    compare(~Quality('dim'), Quality('aug'))
    # test quality from offset:
    compare(Quality.from_offset_wrt_major(-1), Quality('minor'))
    compare(Quality.from_offset_wrt_perfect(1), Quality('augmented'))

    # test chordmodifier parsing:
    compare(parse_chord_modifiers('minormajor7 add11b5'),
    [ChordModifier('min'), ChordModifier('major 7'), ChordModifier('added eleven'), ChordModifier('flattened fifth')])

    # test alterations:
    compare(cast_alterations('#9b11'), [ChordModifier(make={9:1}), ChordModifier(make={11:-1})])
    # compare(parse_chord_modifiers('maj7#9'), parse_chord_modifiers('maj9#9'))
