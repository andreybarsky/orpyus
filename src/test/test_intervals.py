from ..intervals import *
from .testing_tools import compare

def unit_test():
    print('Testing basic arithmetic:')
    compare(Interval(4) - Interval(2), Interval(2))
    compare(Interval(3) - 5, Interval(-2))
    compare(Interval(4) + 10, Interval(14))

    print('Recasting and init by degrees')
    compare(Interval(Interval(14)), Interval(14))
    compare(Maj3, Interval(4))
    compare(Maj3 + Min3, Per5)
    compare(Per5-Min3, Maj3)

    # init by degree:
    compare(Interval(4), Interval.from_degree(3))

    print('Inversion and negation:')
    compare(~Interval(-7), Per4)
    compare(-Aug9, Interval(-15, degree=9))
    compare(~Dim12, -Aug11)

    print('Extended intervals:')
    compare(Interval(14), Interval.from_degree(9))

    print('Degree preservation under addition/subtraction by octaves:')
    compare((Aug4 + Interval(12)).degree, Aug11.degree)
    compare((-Aug4 - Interval(12)).degree, (-Aug11).degree)

    print('And degree inversion under sign switch:')
    compare((Aug4 - Interval(12)).degree, (~Aug4).degree)
    compare(Interval(4) - Interval(24), Interval(-20))


    print('IntervalLists:')
    compare(IntervalList([M3, P5]).pad(left=True, right=True), IntervalList([P1, M3, P5, P8]))
    compare(IntervalList([M3, P5]), IntervalList([P1, M3, P5, P8]).strip())
    compare(IntervalList([M2, M3, P5]), IntervalList([M3, P5, M9]).flatten())




if __name__ == '__main__':
    unit_compare()
