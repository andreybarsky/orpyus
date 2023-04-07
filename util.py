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

    N = len(lst)
    rotated_start_place = num_steps
    rotated_idxs = [(rotated_start_place + i) % N for i in range(N)]
    rotated_lst= [lst[i] for i in rotated_idxs]
    return rotated_lst

def precision_recall(target, candidate, weights=None):
    """return a metric that can be used to determine how well <candidate> fits <target>,
    so long as both have a meaningful __contains__ method to query their members,
    and both contain the same types of objects (that have a meaningful __eq__ method).

    optionally accepts a weight argument, as dict mapping items to weighting terms.
    weights are technically arbitrary, but default to 1 if the weights for an item
    are left unspecified in the dict, so should be set relative to that."""

    # in ML parlance: the candidate is the 'retrieved' set,
    # and the target is the 'relevant' set
    if weights is None:
        num_retrieved = len(candidate)
        num_relevant = len(target)
    else: # sum of weights instead of number of items:
        candidate_weights = [weights[c] if c in weights.keys() else 1 for c in candidate]
        target_weights = [weights[t] if t in weights.keys() else 1 for t in target]

        num_retrieved = sum(candidate_weights)
        num_relevant = sum(target_weights)

    relevant_retrieved = 0 # how many of target's members are in candidate (and vice-versa)

    # TBI: this naive implementation is O(n^2), could be improved if this turns out to be a bottleneck
    for item in target:
        if item in candidate:
            item_weight = 1 if ((weights is None) or (item not in weights.keys())) else weights[item]

            relevant_retrieved += item_weight

    precision = relevant_retrieved / num_retrieved    # i.e. validity
    recall = relevant_retrieved / num_relevant        # i.e. completeness

    return precision, recall

def reverse_dict(dct):
    """accepts a dict whose values and keys are both unique,
    and returns the reversed dict where keys are values and vice versa"""
    rev_dct = {}
    for k,v in dct.items():
        if isinstance(v, list):
            v = tuple(v)
        rev_dct[v] = k
    # rev_dct = {k:v for v,k in dct.items()}
    return rev_dct

def unpack_and_reverse_dict(dct, include_keys=False, force_list=False):
    """accepts a dict whose values are iterables, the items of which are all unique,
    and returns the reversed dict that maps each item to its corresponding parent key"""
    rev_dct = {}
    for k, v_list in dct.items():
        if not isinstance(v_list, (tuple, list)):
            # we expected the value to be an iterable, but it isn't one
            if force_list:
                # set it to be one anyway:
                v_list = [v_list]
            else:
                raise TypeError(f"unpack_and_reverse_dict expects dict values to be tuples or lists of strings")

        for v_item in v_list:
            rev_dct[v_item] = k
        if include_keys:
            # map original dict key back into itself, e.g. for aliases
            rev_dct[k] = k
    return rev_dct

def reduce_aliases(inp, aliases, strip=True, reverse=False, force_list=True, include_keys=False, discard=False, verbose=False):
    """given an input string, and a dict that maps potential input substrings
    to replacements (which can be arbitrary objects), recursively replace the string
    starting from longest possibilities first, until we have reduced it to its canonical form.

    if strip, pad replacement candidates with whitespace as well.
    if reverse, we expect a dict where the VALUES are the replacements, instead of the reverse.
        we assume that the values, then, are lists of replacement substrings,
        and the keys are arbitrary objects.
    if force_list, we relax this assumption on the values, and allow them to be non-lists,
        in which case we just wrap them up as single-item lists.

    if discard, we discard nonmatching characters instead of adding them to the output list."""

    if reverse:
        replacements = unpack_and_reverse_dict(aliases, force_list=force_list, include_keys=include_keys)
    else:
        replacements = aliases


    if strip:
        # add whitespace to the front of every replacmeent in addition:
        whitespaced_replacements = {f' {k}':v for k,v in replacements.items()}
        # as well as versions with stripped whitespace everywhere:
        stripped_replacements = {k.replace(' ', ''):v for k,v in replacements.items()}

        replacements.update(whitespaced_replacements)
        replacements.update(stripped_replacements)

    alias_lengths = [len(a) for a in replacements.keys()]
    max_alias_len = max(alias_lengths)

    # pre-initialise new (output) list:
    output = []

    # iterate starting from each character of the current string:
    cur_input_idx = 0

    while cur_input_idx < len(inp):

        remaining_chars = len(inp) - cur_input_idx
        start_length = min([remaining_chars, max_alias_len])
        # iterate backward starting from the longest possible replacement here:
        found_match = False
        for cur_rep_len in range(start_length, 0, -1):
            cur_len_replacements = {k:v for k,v in replacements.items() if len(k) == cur_rep_len}
            substring = inp[cur_input_idx : cur_input_idx + cur_rep_len]
            if substring in cur_len_replacements.keys():
                # found a replacement:
                rep = cur_len_replacements[substring]
                output.append(rep)
                cur_input_idx += cur_rep_len
                found_match = True
                if verbose:
                    print(f'Replacing {substring} with {rep} at original index={cur_input_idx-cur_rep_len}. New index is {cur_input_idx}, current replacement is: {output}')
                    import pdb; pdb.set_trace()
                break
        if not found_match:
            # no replacement at this character, advance forward by one character
            if not discard:
                output.append(inp[cur_input_idx])
            cur_input_idx += 1

    # finished, join output string and return:
    return output



def transpose_nested_list(nested_list):
    """Given a list of lists (of equal length), or other iterables like strings,
      which represent values across separate rows, returns a list of lists
      that is transposed such that the former rows are now the columns
      and vice versa"""

    num_rows = len(nested_list)
    num_cols = len(nested_list[0])

    new_rows = []
    for c in range(num_cols):
        this_row = []
        for r in range(num_rows):
            this_row.append(nested_list[r][c])
        # cast to string if the original nested list was also strings:
        if isinstance(nested_list[r], str):
            new_rows.append(''.join(this_row))
        else:
            new_rows.append(this_row)
    return new_rows

if __name__ == '__main__':
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
