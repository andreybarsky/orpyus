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

    # test execution time for init by various methods:
    def repeat_init_by_value(n):
        print('Testing interval init by value:')
        for i in range(n):
            for j in range(-24, 24):
                x = Interval(j)
    def repeat_init_by_degree(n):
        print('Testing interval init by value/degree:')
        values = range(-24, 24)
        degrees = [Interval(v).extended_degree for v in values]
        value_degrees = zip(values, degrees)
        for i in range(n):
            for v,d in value_degrees:
                x = Interval(v,d)
    def repeat_init_by_int_addition(n):
        print('Testing interval init by addition with int:')
        base_iv = Interval(1)
        for i in range(n):
            for j in range(-24, 24):
                x = base_iv + j
    def repeat_init_by_iv_addition(n):
        print('Testing interval init by addition with interval:')
        base_iv = Interval(1)
        add_ivs = [Interval(j) for j in range(-24, 24)]
        for i in range(n):
            for j in add_ivs:
                x = base_iv + j
    def repeat_init_by_negation(n):
        print('Testing interval init by negation:')
        ivs = [Interval(j) for j in range(-24, 24)]
        for i in range(n):
            for iv in ivs:
                x = -iv

    # n = 10000
    # repeat_init_by_value(        n=n)
    # repeat_init_by_degree(       n=n)
    # repeat_init_by_int_addition( n=n)
    # repeat_init_by_iv_addition(  n=n)
    # repeat_init_by_negation(     n=n)



if __name__ == '__main__':
    unit_test()
