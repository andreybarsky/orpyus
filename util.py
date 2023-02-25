
verbose = False

class Log:
    def __init__(self, verbose=verbose):
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
