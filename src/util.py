import string
import time
import inspect

VERBOSE = False

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

# generically useful functions used across modules:
def rotate_list(lst, num_steps, N=None):
    """Accepts a list, and returns the wrapped-around list
    that begins num_steps up from the beginning of the original.
    used for inversions, i.e. the 2nd inversion of [0,1,2] is [1,2,0],
    and for modes, which are rotations of scales.
    N uses the length of the list by default,  """
    if N is None:
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

    if precision > 1:
        from ipdb import set_trace; set_trace(context=30)

    return precision, recall

### TBI: allow split by blacklist instead of whitelist??
def auto_split(inp, allow='', allow_numerals=True, allow_letters=True):
    """takes a string 'inp' and automatically separates it by the first character found that is
        not in the whitelist 'allow'.
    'allow' should be a string of characters that are NOT to be treated as separators.
    if 'allow_numerals' is True, allow all the digit characters from 0 to 9.
    if 'allow_letters' is True, allow all the upper and lowercase English alphabetical chars."""
    allow = set(allow)
    if allow_numerals:
        allow.update(string.digits)
    if allow_letters:
        allow.update(string.ascii_letters)
    sep_char = None
    for c in inp:
        if c not in allow:
            sep_char = c
            break
    if sep_char is None:
        # no separator found, return input as single list item
        return [inp]
    else:
        splits = inp.split(sep_char)
        # strip whitespace in addition: in case our sep is something like ', '
        splits = [s.strip() for s in splits]
        return splits


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

def reduce_aliases(inp, aliases, strip=True, reverse=False, force_list=True,
                   include_keys=False, discard=False, verbose=False):
    """given an input string 'inp', and a dict 'aliases' that maps potential input substrings
    to replacements (which can be arbitrary objects), recursively replace the string
    starting from longest possibilities first, until we have reduced it to its canonical form.

    if strip, pad replacement candidates with whitespace as well.
    if reverse, we expect a dict where the VALUES are the replacements, instead
        of the reverse. we assume that the values in this case are lists of
        replacement substrings, and the keys are arbitrary objects.
    if force_list, we relax this assumption on the values, and allow them to be
        non-lists, in which case we just wrap them up as single-item lists.
    if include_keys, we include the dict key in the replacements so they can map
        back onto themselves.
    if discard, we discard nonmatching characters instead of adding them to the
        output list."""

    if reverse:
        replacements = unpack_and_reverse_dict(aliases, force_list=force_list, include_keys=include_keys)
    else:
        replacements = dict(aliases)

    if strip:
        # add whitespace to the front of every replacement in addition:
        whitespaced_replacements = {f' {k}':v for k,v in replacements.items()}
        # as well as versions with stripped whitespace everywhere:
        stripped_replacements = {k.replace(' ', ''):v for k,v in replacements.items()}

        replacements.update(whitespaced_replacements)
        replacements.update(stripped_replacements)

    # cached key lengths for performance optimisation:
    replacement_lengths = {k:len(k) for k in replacements.keys()}

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
            cur_len_replacements = {k:v for k,v in replacements.items() if replacement_lengths[k] == cur_rep_len}
            substring = inp[cur_input_idx : cur_input_idx + cur_rep_len]
            if substring in cur_len_replacements.keys():
                # found a replacement:
                rep = cur_len_replacements[substring]
                output.append(rep)
                cur_input_idx += cur_rep_len
                found_match = True
                log(f'Replacing {substring} with {rep} at original index={cur_input_idx-cur_rep_len}. New index is {cur_input_idx}, current replacement is: {output}')
                break
        if not found_match:
            # no replacement at this character, advance forward by one character
            if not discard:
                output.append(inp[cur_input_idx])
            cur_input_idx += 1

    # finished, join output string and return:
    return output

def check_all(iterable, check, type_assertion):
    """accepts an iterable of objects, and a type that they are assumed to be,
    and individually checks that all items in iterable are of that type.

    'check' arg determines what function we use to check type. must be one of:
        'isinstance' / 'instance': use "isinstance(X, Y)""
        '==' / 'eq' / 'equals':    use "type(X) == Y"
        'is':                      use "X is Y"                             """
    for item in iterable:
        if check in ('isinstance', 'instance'):
            if not (isinstance(item, type_assertion)):
                return False
        elif check in ('==', 'eq', 'equals'):
            if not (type(item) == type_assertion):
                return False
        elif check == 'is':
            if not (item is type_assertion):
                return False
        else:
            raise Exception(f"invalid check arg ({check}) to assert_all, must be one of: 'isinstance', '==, 'is'")
    return True

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

def euclidean_gcd(a,b):
    """Euclidean algorithm to calculate greatest common divisor"""
    # (don't ask me why this works)
    left, right = a,b
    while right > 0:
        left, right = right, left % right
    return left

def least_common_multiple(a,b):
    return (a*b) // euclidean_gcd(a,b)
