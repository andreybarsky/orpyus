from .chords import AbstractChord, Chord
from .scales import Scale, NaturalMajor, NaturalMinor, ScaleChord
from .progressions import Progression
from .util import unpack_and_reverse_dict, euclidean_gcd, log

function_names = {'T': 'tonic',
                  'ST': 'subtonic',
                  'TP': 'tonic prolongation',
                  'PD': 'predominant',
                  'D': 'dominant'}

###### major:
major_function_degrees = { 'T': ['I'],
                          'TP': ['iii', 'VI'], # can progress down the list but not up it
                          'PD': ['IV', 'ii'],
                           'D': ['viio', 'V'],
                          }

major_function_subsequents = {'T' : ['TP', 'PD', 'D'],
                              'TP': ['PD', 'TP'],
                              'PD': ['D', 'PD'],
                              'D' : ['T', 'D'],
                             }

major_special_movements = {  ('IV','I'): ('TP', 'T'), # plagal cadence
                             ('V','VI'): ('D', 'TP'), # deceptive cadence
                            ('V','bVI'): ('D', 'TP'), # deceptively deceptive cadence
                        ('bVI', 'bVII'): ('TP', 'D'), # 'epic' deceptive cadence conclusion
                          }
######
minor_function_subsequents = dict(major_function_subsequents)
minor_function_subsequents['T'].append('ST') # minor includes subtonic that connects T
minor_function_degrees = { 'T': ['i'],
                          'ST': ['VII'],
                          'TP': ['III', 'VI'],
                          'PD': ['iv', 'iio'],
                           'D': ['viio', 'V'],
                          }


def populate_markov_model(function_degrees, function_subsequents, special_movements = None):
    degree_functions = unpack_and_reverse_dict(function_degrees)
    if special_movements is None:
        special_movements = {} # nothing by default

    markov_model = {}
    

### HarmonicModel class not intended to be user-facing; used instead to define major/minor markov models and harmonic functions
class HarmonicModel:
    def __init__(self, scale, function_degrees, function_subsequents):

        # type check:
        if not isinstance(scale, Scale):
            # cast to Scale object:
            scale = Scale(scale)
        self.scale = scale

        self.function_degrees = function_degrees
        self.degree_functions = unpack_and_reverse_dict(function_degrees)
        self.function_subsequents = function_subsequents

    def parse_functions(self, progression):
        """from a Progression object, return a list of the chord functions
        of that object's constituent ScaleChords"""
        return [self.degree_functions[d]
                if d in self.degree_functions
                else None
                for d in progression.root_degrees]

    def check_grammar(self, progression):
        prog_functions = self.parse_functions(progression)
        prog_list = zip(progression.root_degrees, prog_functions)

        grammar_score = 0
        for i in range(1, len(progression)):
            # prog_so_far = progression.slice(0,i+1)
            # (prev_deg, prev_func), (next_deg, next_func) = prog_list[i-1], prog_list[i]

            prev_deg = progression.root_degrees[i-1]
            next_deg = progression.root_degrees[i]

            if prev_deg == next_deg:
                # allowed by default
                grammar_score += 1
            else:
                # check if the next degree is in the list of allowable ones by continuation rules:
                possible_next_degrees = self.continuation_degrees(progression, from_idx=i-1, as_numerals=False)
                log(f'Allowable next degrees after {[c.short_name for c in progression.chords[:i]]}:\n{possible_next_degrees}')
                if next_deg in possible_next_degrees:
                    log(f'{progression.chords[i].short_name} can legally follow from {progression.chords[i-1].short_name}')
                    grammar_score += 1
                    if not progression.chords[i].in_scale:
                        log(f'  (but it is not in the scale: {self.scale.name}, so penalised)')
                        grammar_score -= 0.5
                else:
                    log(f'{progression.chords[i].short_name} CANNOT legally follow from {progression.chords[i-1].short_name}')
                    pass # no increase in score
                log(f'Current score: {grammar_score}/{i} ({(grammar_score/i):.2f})')

        for idx in [0, -1]:
            if prog_functions[idx] == 'T':
                # increase score for tonic occurring at start or end:
                grammar_score += 1

        # at end: return average grammar across progression
        final_score = grammar_score / (len(progression)+1)
        return round(final_score, 2)

    def continuation_degrees(self, progression, from_idx=-1, as_numerals=True):
        """accepts a Progression object, returns a list of root degrees that serve
        as valid continuations of that progression"""
        # markov-order-1 continuations
        prog_functions = self.parse_functions(progression)
        prev_func, prev_deg = prog_functions[from_idx], progression.root_degrees[from_idx]

        ####
        if prev_func is None:
            possible_next_degrees = [] # unknown continuation
        else:
            possible_next_functions = self.function_subsequents[prev_func]
            possible_next_degrees = []
            for nf in possible_next_functions:
                if nf == prev_func: # movement within a function
                    # must be a listed degree that occurs after this one
                    this_idx = [i for i,d in enumerate(self.function_degrees[nf]) if d == prev_deg][0]
                    possible_next_degrees.extend(self.function_degrees[nf][(this_idx+1):])
                else:
                    possible_next_degrees.extend(self.function_degrees[nf])

        possible_next_degrees.sort()
        # import ipdb; ipdb.set_trace()
        if as_numerals:
            # return upper/lowercase roman numerals
            cont_chords = self.scale.chords(possible_next_degrees, order=3)
            return [c.numeral for c in cont_chords]
        else:
            # return integer degrees
            return possible_next_degrees

    continuations = degree_continuations = continuation_degrees

    def continuation_chords(self, progression, order=3, from_idx=-1):
        """as continuation_degrees, but returns ScaleChords instead of root degrees"""
        cont_degs = self.continuation_degrees(progression, from_idx=from_idx, as_numerals=False)
        cont_chords = self.scale.chords(cont_degs, order=order)
        return cont_chords

    chord_continuations = continuation_chords

major_model = HarmonicModel(NaturalMajor, function_degrees, function_subsequents)

# MajorHarmonicModel = HarmonicModel(NaturalMajor, degree_functions)
