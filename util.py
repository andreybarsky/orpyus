VERBOSE = False

class Log:
    def __init__(self, verbose=VERBOSE):
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

# generically useful functions used across modules:
def rotate_list(lst, num_steps):
    """Accepts a list, and returns the wrapped-around list
    that begins num_steps up from the beginning of the original.
    used for inversions, i.e. the 2nd inversion of [0,1,2] is [1,2,0],
    and for modes, which are rotations of scales. """

    rotated_start_place = num_steps
    rotated_idxs = [(rotated_start_place + i) % 7 for i in range(7)]
    rotated_lst= [lst[i] for i in rotated_idxs]
    return rotated_lst

def precision_recall(target, candidate):
    """return a metric that can be used to determine how well <candidate> fits <target>,
    so long as both have a meaningful __contains__ method to query their members,
    and both contain the same types of objects (that have a meaningful __eq__ method)"""

    # in ML parlance: the candidate is the 'retrieved' set,
    # and the target is the 'relevant' set
    num_retrieved = len(candidate)
    num_relevant = len(target)

    relevant_retrieved = 0 # how many of target's members are in candidate (and vice-versa)

    # TBI: this naive implementation is O(n^2), could be improved if this turns out to be a bottleneck
    for item in target:
        if item in candidate:
            relevant_retrieved += 1

    precision = relevant_retrieved / num_retrieved    # i.e. validity
    recall = relevant_retrieved / num_relevant        # i.e. completeness

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
