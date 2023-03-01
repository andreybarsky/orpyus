VERBOSE = False

class Log:
    def __init__(self, VERBOSE=verbose):
        self.verbose=verbose

    def __call__(self, msg):
        if self.verbose:
            print(msg)

log = Log()


class TestSuite:
    def __init__(self, silent=False, graceful=False):
        self.silent = silent
        self.graceful = graceful

    def __call__(self, op, exp):
        ### test output of an operation against its expected value
        if type(exp) == float:
            assert type(op) == float
            diff = op - exp
            result = (diff < 1e-10)
        else:
            result = (op == exp)
        resultstr = '+++ PASS' if result else '--- FAIL'
        if not self.silent:
            print(f'{resultstr}:\n o: {op}\n e: {exp}\n')

        if not result and not self.graceful:
            raise Exception('Test failed')

test = TestSuite()

def evaluate_membership(target, candidate):
    """return a metric that can be used to determine how well <candidate> fits <target>,
    so long as both have a meaningful __contains__ method to query their members,
    and both contain the same types of objects (that have a meaningful __eq__ method)"""

    t_in_c = 0 # how many of target's members are in candidate
    c_in_t = 0 # how many of candidate's members are in target

    for t_item in target:
        if t_item in candidate:
            t_in_c += 1         # t_in_
    for c_item in candidate:
        if c_item in target:
            c_in_t += 1

    # are c_in_t and t_in_c always the same? why?
    if t_in_c != c_in_t:
        print('Found a case where t_in_c ({t_in_c}) does not equal c_in_t ({c_in_t}): \ntarget: {target} \ncandidate {candidate}')

    # are these the right way round?
    precision = c_in_t / len(candidate)  # i.e. validity
    recall = t_in_c / len(target)        # i.e. completeness

    return precision, recall




if __name__ == '__main__':
    # some tests on membership evaluation
    target = ['C', 'E', 'G', 'A']

    # candidate is a subset of target:
    print(evaluate_membership(target, ['C', 'E', 'G']))

    # target is a subset of candidate:
    print(evaluate_membership(target, ['C', 'E', 'G', 'A', 'Bb']))

    # same length but a mismatch:
    print(evaluate_membership(target, ['C', 'E', 'G', 'B']))

    # perfect fit: (inverted)
    print(evaluate_membership(target, ['A', 'C', 'E', 'G']))

    # complete mess:
    print(evaluate_membership(target, ['A', 'D#', 'Eb', 'Gb', 'B']))
