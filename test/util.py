VERBOSE = False
import time
global_init_time = time.time()

class Log:
    """logging class for detailed info from nested function execution"""
    def __init__(self, verbose=VERBOSE):
        self.verbose=verbose

    def __call__(self, msg):
        if self.verbose:
            cur_frame = inspect.currentframe()
            call_frame = inspect.getouterframes(cur_frame, 2)
            wall_time = time.time() - global_init_time

            context = f'[{wall_time:.06f}]({call_frame[1][3]}) '
            print(context + msg)

log = Log()


class TestSuite:
    def __init__(self, silent=False, graceful=False):
        self.silent = silent
        self.graceful = graceful

    def __call__(self, op, exp, compare='equal'):
        ### test output of an operation against its expected value
        start_time = time.time()

        if type(exp) == float:
            assert type(op) == float
            diff = op - exp
            result = (diff < 1e-10)
        else:
            if compare == 'equal':
                result = (op == exp)
            elif compare == 'enharmonic':
                result = (op & exp)

        finished_time = time.time()
        wall_time = start_time - global_init_time
        exec_time_ms = (finished_time - start_time) * 1000.

        resultstr = 'TEST +++ PASS' if result else 'TEST --- FAIL'
        if not self.silent:
            print(f'[{wall_time:.06f}] {resultstr}:\n obs: {op}\n exp: {exp}\n   (execution time: {exec_time_ms:.04f}ms)\n')

        if not result and not self.graceful:
            raise Exception('Test failed')

compare = TestSuite(silent=False)
