from ..util import precision_recall, reduce_aliases
# from .testing_tools import compare

def unit_test():
    # some tests on membership evaluation
    target = ['C', 'E', 'G', 'A']
    # weights will prioritise the root:
    weights = {'C': 2, 'E': 1, 'G': 1, 'A': 1}

    # candidate is a subset of target:
    print(precision_recall(target, ['C', 'E', 'G'], weights=weights))

    # candidate is a subset of target (but missing the root):
    print(precision_recall(target, ['A', 'E', 'G'], weights=weights))

    # target is a subset of candidate:
    print(precision_recall(target, ['C', 'E', 'G', 'A', 'Bb']))

    # same length but a mismatch:
    print(precision_recall(target, ['C', 'E', 'G', 'B']))

    # perfect fit: (but inverted)
    print(precision_recall(target, ['A', 'C', 'E', 'G']))

    # complete mess:
    print(precision_recall(target, ['A', 'D#', 'Eb', 'Gb', 'B']))

    # test alias reduction:
    aliases = {'hdim': ['half diminished', 'halfdim'], 'fdim': ['diminished', 'fully diminished']}
    print(''.join(reduce_aliases('half diminished diminished chord', aliases)))
