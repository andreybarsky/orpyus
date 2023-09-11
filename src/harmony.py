### WIP (incomplete) module, I promise structure and documentation here will get better

from .chords import AbstractChord, Chord
from .scales import Scale, NaturalMajor, NaturalMinor, HarmonicMinor, ScaleChord
from .progressions import Progression
from .util import unpack_and_reverse_dict, euclidean_gcd, log


function_names = {'T': 'tonic',
                  'ST': 'subtonic',
                  'TP': 'tonic prolongation',
                  'PD': 'predominant',
                  'SD': 'subdominant', # same thing
                  'D': 'dominant'}

### HarmonicModel class not intended to be user-facing; used instead to define major/minor markov models and harmonic functions
class HarmonicModel:
    def __init__(self, scale, function_degrees, ordered_functions,
                              function_subsequents,
                              special_movements_functions=None):

        # type check:
        if not isinstance(scale, Scale):
            # cast to Scale object:
            scale = Scale(scale)
        self.scale = scale

        self.function_degrees = {f:[ScaleChord.from_numeral(n, scale=self.scale) for n in nums] for f, nums in function_degrees.items() }
        self.degree_functions = unpack_and_reverse_dict(self.function_degrees)

        self.ordered = ordered_functions

        self.function_subsequents = function_subsequents

        if special_movements_functions is None:
            self.special_movements = {}
        else:
            exceptions = special_movements_functions
            self.special_movements = {(ScaleChord.from_numeral(n1, scale=self.scale), ScaleChord.from_numeral(n2, scale=self.scale)) : (f1, f2)
                                      for (n1, n2), (f1, f2) in exceptions.items()}


        self.markov = self.populate_markov_model(self.scale, function_degrees, function_subsequents, special_movements_functions, ordered_functions=self.ordered)


    def populate_markov_model(self, scale, function_degrees, function_subsequents, special_movements = None, ordered_functions=False):
        """given harmonic model input parameters, creates the master markov model dict
        that fully describes harmonic progression in that model"""
        degree_functions = unpack_and_reverse_dict(function_degrees)
        if special_movements is None:
            special_movements = {} # nothing by default

        markov_dct = {}

        node_numerals = degree_functions.keys()
        num2chord = {num: ScaleChord.from_numeral(num, scale=scale) for num in node_numerals}
        node_chords = [num2chord[num] for num in node_numerals]

        for num, prev_chord in zip(node_numerals, node_chords):
            markov_dct[(prev_chord,)] = []

            node_function = degree_functions[num]
            subsequent_functions = function_subsequents[node_function]

            subsequent_nums = []

            # progression within the same function:
            if ordered_functions:
                ### can progress down the list of the same function but not up it
                # so get index of this chord/numeral/degree in the list for this function:
                this_num_idx_in_func = [i for i,d in enumerate(function_degrees[node_function]) if d == num][0]
                # and allow only those from the same index or later:
                same_function_subsequent_nums = [num for i,num in enumerate(function_degrees[node_function]) if i >= this_num_idx_in_func]

                subsequent_nums.extend(same_function_subsequent_nums)

                # subsequent_functions now refers only to DIFFERENT functions, not this one:
                subsequent_functions = [func for func in subsequent_functions if func != node_function]

            for func in subsequent_functions:
                subsequent_nums.extend(function_degrees[func])
            subsequent_chords = [num2chord[num] for num in subsequent_nums]

            ### populate markov dict with these subsequents:
            # note that dict keys are always tuples, even for markov order 1:
            markov_dct[(prev_chord,)].extend(subsequent_chords)

        return markov_dct ### TO BE TESTED

        ### TO BE FINISHED:
        # parse 'special' movements that exist outside the strict function-degree typology:
        for degree_pair, function_pair in special_movements_functions.items():
            d1, d2 = degree_pair
            f1, f2 = function_pair



    def parse_functions(self, progression):
        """from a Progression object, return a list of the chord functions
        of that object's constituent ScaleChords"""
        simple_triads = [ch.scale_triad for ch in progression.chords]
        functions = []
        # iterate through progression, looking for special movements first
        # and for atomic degree functions second:
        prog_idx = 0
        while prog_idx < len(progression):
            print(f'Prog idx: {prog_idx}')
            if prog_idx + 1 < len(progression): # if at least two chords remain
                chord_pair = simple_triads[prog_idx], simple_triads[prog_idx + 1]
                print(f' Checking chord pair: {chord_pair[0].short_name}, {chord_pair[1].short_name}')
                if chord_pair in self.special_movements:
                    print(f'Special movement found: {chord_pair}')
                    functions.extend(self.special_movements[chord_pair])
                    prog_idx += 2
                    continue
            # atomic degree functions:
            single_chord = simple_triads[prog_idx]
            print(f'   Checking single chord: {single_chord}')
            if single_chord in self.degree_functions:
                functions.append(self.degree_functions[single_chord])
            else:
                functions.append(None)
            prog_idx += 1
        return functions


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



###### major:

BasicMajorModel = HarmonicModel(  # basic tonic - subdominant - dominant model
                       scale = NaturalMajor,
            function_degrees = { 'T' : ['I', 'iii'],
                                 'PD': ['IV', 'ii',  'vi'],
                                 'D' : ['viio', 'V'],
                               },
                                  ordered_functions=False,
        function_subsequents = { 'T' : ['T', 'PD', 'D'],
                                 'PD': ['PD', 'D'],
                                 'D' : ['T', 'D'],
                               },

special_movements_functions =  { ('IV','I'): ('PD', 'T'), # plagal cadence
                                 ('V','vi'): ('D' , 'T'), # deceptive cadence
                               },
                               )

ClassicalMajorModel = HarmonicModel(  # slightly more sophisticated theoretical model
                                      # with more classical-style formalisation of movement within degrees
                       scale = NaturalMajor,
            function_degrees = { 'T' : ['I'],
                                 'TP': ['iii', 'vi'], # can progress down the list but not up it
                                 'PD': ['IV', 'ii'],
                                 'D' : ['viio', 'V'],
                               },
                                ordered_functions=True,
       function_subsequents =  {'T' : ['TP', 'PD', 'D'],
                                'TP': ['PD', 'TP'],
                                'PD': ['D', 'PD'],
                                'D' : ['T', 'D'],
                               },

special_movements_functions =   {('IV','I'): ('TP', 'T'), # plagal cadence
                                 ('V','vi'): ('D', 'TP'), # deceptive cadence
                                ('V','bVI'): ('D', 'TP'), # deceptively deceptive cadence
                            ('bVI', 'bVII'): ('TP', 'D'), # 'epic' deceptive cadence conclusion
                              },
                            )


ClassicalMinorModel = HarmonicModel(  # extension of classical major model to minor key
                       scale = HarmonicMinor,
            function_degrees = { 'T' : ['i'],
                                 'ST': ['VII'], # minor-specific subtonic
                                 'TP': ['III', 'VI'],
                                 'PD': ['iv', 'iio'],
                                 'D' : ['viio', 'V'],
                               },
                                ordered_functions=True,
       function_subsequents =  {'T' : ['TP', 'PD', 'D', 'ST'],
                                'ST': [],
                                'TP': ['PD', 'TP'],
                                'PD': ['D', 'PD'],
                                'D' : ['T', 'D'],
                               },

special_movements_functions =   {('VII', 'III'): ('ST', 'TP'), # sole function of subtonic
                                     ('iv','i'): ('TP', 'T'), # plagal cadence
                                     ('V','vi'): ('D', 'TP'), # deceptive cadence
                                     ('V','VI'): ('D', 'TP'), # deceptively deceptive cadence
                                  ('VI', 'VII'): ('TP', 'D'), # 'epic' deceptive cadence conclusion
                              },
                            )





# major_model = HarmonicModel(NaturalMajor, major_function_degrees, major_function_subsequents,
#                             exceptions=major_special_movements)
#
# # MajorHarmonicModel = HarmonicModel(NaturalMajor, degree_functions)
#

p = Progression('I visus4 IV')
