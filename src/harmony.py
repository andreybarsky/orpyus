### WIP (incomplete) module, I promise structure and documentation here will get better

from .chords import AbstractChord, Chord
from .scales import Scale, NaturalMajor, NaturalMinor, HarmonicMinor, ScaleChord
from .keys import Key, KeyChord
from .progressions import Progression, ChordProgression, common_progressions
from .util import unpack_and_reverse_dict, euclidean_gcd, log
from collections import Counter

function_names = {'T': 'tonic',
                  'ST': 'subtonic',
                  'TP': 'tonic prolongation',
                  'PD': 'predominant',
                  'SD': 'subdominant', # same thing
                  'D': 'dominant'}


class HarmonicModel:
    # parent class for different harmonic model types
    pass

### HarmonicModel class not intended to be user-facing; used instead to define major/minor markov models and harmonic functions
class HarmonicFunctionModel(HarmonicModel):
    def __init__(self, scale, function_degrees, ordered_functions,
                              function_subsequents,
                              special_movements_functions=None):

        # type check:
        if not isinstance(scale, Scale):
            # cast to Scale object:
            scale = Scale(scale)
        self.scale = scale

        self.function_degrees = {f:[ScaleChord(n, scale=self.scale) for n in nums] for f, nums in function_degrees.items() }
        self.degree_functions = unpack_and_reverse_dict(self.function_degrees)

        self.ordered = ordered_functions

        self.function_subsequents = function_subsequents

        if special_movements_functions is None:
            self.special_movements = {}
        else:
            exceptions = special_movements_functions
            self.special_movements = {(ScaleChord(n1, scale=self.scale), ScaleChord(n2, scale=self.scale)) : (f1, f2)
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
        num2chord = {num: ScaleChord(num, scale=scale) for num in node_numerals}
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

BasicMajorModel = HarmonicFunctionModel(  # basic tonic - subdominant - dominant model
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

ClassicalMajorModel = HarmonicFunctionModel(  # slightly more sophisticated theoretical model
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


ClassicalMinorModel = HarmonicFunctionModel(  # extension of classical major model to minor key
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


class HarmonicDataModel(HarmonicModel):
    """a type of harmonic model that is populated by scraping a database,
    either of rooted ChordProgressions or of abstract numeral Progressions,
    and explains its predictions by attribution to the database"""
    def __init__(self, scale, progressions, memory=3, shift_scale=False, verbose=False):

        if not isinstance(scale, Scale):
            scale = Scale(scale)
        self.scale = scale
        self.memory = memory

        self.verbose = verbose

        self.populate_with_progressions(progressions, shift_scale=shift_scale)
        # sets self.continuations and self.attributions,
        # the core attributes of the model

        ### idea: extra flags to allow replacement of chords with substitutions, secondaries, tritones etc.

    ### TBI: these dict string keys should be replaced with RomanNumeral objects when possible
    def populate_with_progressions(self, progression_names, simplify=True, shift_scale=False):
        """accepts a dataset dict that keys Progression objects to informative names,
        populates the self.continuations and self.attributions dicts
        according to that data"""

        continuations_by_length = {l: {} for l in range(1, self.memory+1)}
        attributions = {}

        parallel_scale = self.scale.parallel

        for progression, prog_name in progression_names.items():
            if progression.scale != self.scale:
                # progression given is not for this scale
                if shift_scale and progression.scale == parallel_scale:
                    # we can try shifting to relative and logging that
                    log(f'\n{progression} not in {self.scale._marker}{self.scale.name}, but shifting to relative: {progression.relative}', force=self.verbose)
                    progression = progression.relative
                else:
                    # otherwise ignore it
                    log(f'\nProgression {prog_name} not in {self.scale._marker}{self.scale.name}, ignoring ({prog_name})', force=self.verbose)
                    continue

            log(f'\nProcessing progression {prog_name}: {progression}', force=self.verbose)

            # memory can't be higher than the length of the progression:
            prog_memory = min([self.memory, len(progression)])

            for start in range(len(progression)):
                # end_range = range(start+2, start+memory+1)
                for end in range(start+2, start+prog_memory+2):
                    # loop through end of progression back to start if needed:
                    chord_idxs = [i % len(progression) for i in range(start, end)]

                    seq_length = end-start
                    if (seq_length-1) <= prog_memory:
                        log(f'  processing subset from {start}-{end % len(progression)} (length={end-start})', force=self.verbose)
                        continuations = continuations_by_length[seq_length-1] # dict object of antecedent-subsequent pairs

                        # for i in chord_idxs:
                        #     assert progression.chords[i].scale == self.scale

                        if simplify:
                            # use basic, unmodified numerals (i.e. V7 becomes V, but IV and iv stay IV and iv)
                            chord_sublist = [progression.chords[i].simple_numeral for i in chord_idxs]
                        else:
                            # use modified numerals instead
                            chord_sublist =  [progression.chords[i].mod_numeral for i in chord_idxs]

                        antecedents = tuple(chord_sublist[:-1])
                        subsequent = chord_sublist[-1]

                        # update model:
                        if antecedents not in continuations:
                            continuations[antecedents] = Counter() # counter for each antecedent
                        continuations[antecedents].update((subsequent,))
                        log(f'    updated counter: {continuations[antecedents]}', force=self.verbose)

                        # update attributions:
                        seq_pair = (antecedents, subsequent)
                        if seq_pair not in attributions:
                            # attributions[seq_pair] = Counter()
                            attributions[seq_pair] = []
                        log(f'      associating {prog_name} with sequence: {antecedents} -> {subsequent}', force=self.verbose)
                        # attributions[seq_pair].update((prog_name,))
                        attributions[seq_pair].append(prog_name)

        self.continuations = continuations_by_length
        self.attributions = attributions

    def populate_with_chordprogressions(self, chordprogression_names):
        pass # TBI (requires robust key-finding)

    def complete(self, progression, simplify=False, display=True):
        if not isinstance(progression, Progression):
            progression = Progression(progression, scale=self.scale)
        else:
            if progression.scale != self.scale:
                print(f'== WARNING: Progression scale ({progression.scale}) does not match model scale {self.scale} == ')

        possible_continuation_weights = Counter() # dict linking suggestions to logits
        explanations = {} # dict linking suggestions to counters of attributions

        end_idx = len(progression)

        # memory can't be higher than the length of the progression:
        prog_memory = min([self.memory, len(progression)])
        # loop through the length of the progression in descending order,
        # up to the limit of memory::
        for start_idx in range(end_idx -1, end_idx -prog_memory -1, -1):
            # are there any continuations of this length in the model?
            seq_range = range(start_idx, end_idx)
            log(f'seq range: {list(seq_range)}')
            ante_len = len(seq_range)
            if ante_len in self.continuations:

                ante_chords = [progression.chords[i] for i in seq_range]
                if simplify:
                    ante_numerals = [ch.simple_numeral for ch in ante_chords]
                else:
                    ante_numerals = [ch.mod_numeral for ch in ante_chords]
                log(f'  {ante_len} : {ante_numerals}')

                # find matches in dataset:
                ante_key = tuple(ante_numerals)
                relevant_continuations = self.continuations[ante_len]
                if ante_key in relevant_continuations:
                    possible_subsequents = relevant_continuations[ante_key]
                    log('    ' + str(possible_subsequents))
                    # loop over each possible continuation and its weight in the dataset:
                    for sub, weight in possible_subsequents.items():
                        # augment weight by the length of this subsequence
                        # (since more precise matches are more likely)
                        aug_factor = ante_len
                        aug_weight = weight * aug_factor
                        possible_continuation_weights.update({sub: aug_weight})

                        # and get the attributions:
                        attr_key = (ante_key, sub)
                        attrs = self.attributions[attr_key] # set of prog name strings
                        log(f'      with data from: {attrs}')
                        weighted_attrs = {attr: aug_factor for attr in attrs}
                        # each of these contributes explanatory power based on the aug factor:
                        if sub not in explanations:
                            explanations[sub] = {}
                        sub_explanations = explanations[sub]
                        if ante_key not in sub_explanations:
                            sub_explanations[ante_key] = Counter()

                        sub_explanations[ante_key].update(weighted_attrs)

                else:
                    log(f'   no datapoints for subsequence: {ante_key}')



        # convert logits to probabilities:
        total_cont_weight = sum(possible_continuation_weights.values())
        continuation_probabilities = {cont: round(w / total_cont_weight, 2)
                                      for cont,w in possible_continuation_weights.items()}

        if not display:
            # just return the dict of scores
            return continuation_probabilities

        else:
            lb, rb = progression._brackets

            if isinstance(progression, ChordProgression):
                # cont_str = Chord._marker + ScaleChord(cont, scale=progression.key.scale).in_key(progression.key).short_name
                print(f'\nContinuations for {lb}{str(progression.chords)[2:-2]} ...{rb} :')
            else:
                print(f'\nContinuations for {lb}{progression.numerals} - ...{rb} :')

            ranked_conts = sorted(list(continuation_probabilities.keys()), key=lambda x: -continuation_probabilities[x])

            prob_threshold = 0.1
            num_conts = len(ranked_conts)
            conts_below_threshold = [c for c in ranked_conts if continuation_probabilities[c] < prob_threshold]

            for cont in ranked_conts:
                # display output, one suggestion at a time:
                prob = continuation_probabilities[cont]
                if prob > prob_threshold:
                    percent = f'{int(continuation_probabilities[cont] * 100)}%'

                    if isinstance(progression, ChordProgression):
                        # resulting_prog_str = f'{lb}{"-".join([ch.chord_name for ch in (progression + cont)])}{rb}'
                        cont_str = Chord._marker + ScaleChord(cont, scale=progression.key.scale).in_key(progression.key).short_name
                        resulting_prog_str = f'{lb}{" - ".join([ch.short_name for ch in (progression + cont)])}{rb}'
                    else:
                        cont_str = AbstractChord._marker + cont
                        resulting_prog_str = f'{lb}{" - ".join([str(rn) for rn in (progression + cont).numerals])}{rb}'
                    print(f'\n{percent} : {cont_str}    (to make: {resulting_prog_str})')

                    # explain reasoning:
                    print(f'    because:')
                    sub_explanation = explanations[cont]
                    already_mentioned = set() # to ensure we don't list the same prog twice
                    # explanation_antes = sub_explanation.keys() # counter of progression name strings
                    for ante_key, expl_counter in list(sub_explanation.items())[::-1]: # from longest to shortest
                        prog_names = [name for name in expl_counter.keys() if name not in already_mentioned]
                        ante_str = '-'.join(ante_key)
                        if len(prog_names) <= 5:
                            progs_str = ', '.join(prog_names) # progression names
                            if len(progs_str) > 0:
                                print(f'        [ {ante_str} ] to [ {cont} ] is seen in: {progs_str}')
                                already_mentioned.update(prog_names)
                        else:
                            num_others = len(prog_names) - 4
                            prog_names = list(prog_names)[:4]
                            already_mentioned.update(prog_names)
                            progs_str = ', '.join(prog_names) # just the first four
                            print(f'        [ {ante_str} ] to [ {cont} ] is seen in: {progs_str}, and {num_others} others')

            if isinstance(progression, ChordProgression):
                chord_names = [Chord._marker + ScaleChord(cont, scale=progression.key.scale).in_key(progression.key).short_name for cont in conts_below_threshold]
            else:
                chord_names = conts_below_threshold
            low_prob_strs = [f'{cname} ({int(continuation_probabilities[cont] * 100)}%)' for cname, c in zip(chord_names, conts_below_threshold)]
            if len(low_prob_strs) > 0:
                print(f'\nand other continuations with low probability:')
                print('    ' + ', '.join(low_prob_strs))

    def rate(self, progression, exponent=0.5, simplify=True):
        """calculates the probability of a given (abstract) Progression
        according to the continuations defined by this model
        and returns a float value"""

        assert type(progression) is Progression, "harmonic model can only rate an abstract Progression"

        pairwise_scores = []
        patterns = []



        for i in range(1, len(progression)):
            next_chord = progression.chords[i]

            # how far back to look depends on this model's memory,
            # but cannot go lower than 0:
            start_idx = max([0, i - self.memory])
            prev_chords = progression.chords[start_idx : i]

            if simplify:
                sub_numeral = next_chord.simple_numeral
                prev_numerals = [ch.simple_numeral for ch in prev_chords]
            else:
                sub_numeral = next_chord.mod_numeral
                prev_numerals = [ch.mod_numeral for ch in prev_chords]

            print(f'step {i}, comparing sequence {prev_numerals} to {sub_numeral}')

            found_match = False
            # get model continuations for next chord, starting from longest antecedent:
            for j in range(len(prev_chords)):
                print(f'  step {i}.{j}, precursor sequence: {prev_numerals[j:]}')
                antecedent_chords = prev_chords[j:]
                if simplify:
                    ante_key = tuple([ch.simple_numeral for ch in antecedent_chords])
                else:
                    ante_key = tuple([ch.mod_numeral for ch in antecedent_chords])

                seq_len = len(ante_key)
                if ante_key in self.continuations[seq_len]:
                    subsequent_scores = self.continuations[seq_len][ante_key]
                    if sub_numeral in subsequent_scores:
                        raw_score = subsequent_scores[sub_numeral]
                        probability = raw_score / len(subsequent_scores)
                        pattern = (ante_key, sub_numeral)

                        found_match = True
                        print(f'  {ante_key} predicts {sub_numeral}, score: {probability}')
                        break
                    else:
                        print(f'  {ante_key} occurs in model but does not predict {sub_numeral}')
                else:
                    print(f'  no len={seq_len} match for {ante_key}, does not occur in model')

            if not found_match:
                probability = 0 # no match found
                pattern = None
                print(f'    unexpected chord {sub_numeral} after {prev_numerals}, score: {probability}')

            pairwise_scores.append(probability)
            patterns.append((ante_key, sub_numeral))

        # adjust scores by exponent weighting:
        adj_scores = [s**exponent for s in pairwise_scores]
        print(f'scores: {pairwise_scores}')
        print(f'adj   : {adj_scores}')

        # average of adjusted scores:
        return round(sum(adj_scores) / len(adj_scores),  2)





# major_model = HarmonicModel(NaturalMajor, major_function_degrees, major_function_subsequents,
#                             exceptions=major_special_movements)
#
# # MajorHarmonicModel = HarmonicModel(NaturalMajor, degree_functions)
#

common_major_model = HarmonicDataModel('major', common_progressions)
# common_major_model.populate_with_progressions(common_progressions)

common_minor_model = HarmonicDataModel('minor', common_progressions, shift_scale=True)
# common_minor_model.populate_with_progressions(common_progressions)

default_harmonic_models = {NaturalMajor: common_major_model,
                        NaturalMinor: common_minor_model}

if __name__ == '__main__':
    # verbosely initialise progression-based harmonic models:




    # attempt autocompletion:
    p = Progression('I V')
    common_major_model.complete(p)
