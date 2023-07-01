from ..qualities import Quality, ChordQualifier, parse_chord_qualifiers, cast_alterations
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

    # test chordqualifier parsing:
    compare(parse_chord_qualifiers('minormajor7 add11b5'),
    [ChordQualifier('min'), ChordQualifier('major 7'), ChordQualifier('added eleven'), ChordQualifier('flattened fifth')])

    # test alterations:
    compare(cast_alterations('#9b11'), [ChordQualifier(make={9:1}), ChordQualifier(make={11:-1})])
    # compare(parse_chord_qualifiers('maj7#9'), parse_chord_qualifiers('maj9#9'))
