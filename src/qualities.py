# OOP representation of major/minor quality that is invertible and has a null (indeterminate) value
from .util import reverse_dict, unpack_and_reverse_dict, reduce_aliases, log
from .parsing import degree_names, is_valid_note_name, parse_alteration, accidental_offsets, offset_accidentals, fl, sh, nat, dfl, dsh
from . import _settings

# TBI: double dim/aug qualities?


#### interval qualities:

quality_aliases = {'major': ['maj', 'M'],
           'minor': ['min', 'm'],
           'perfect': ['indeterminate', 'ind', 'I', 'null', 'perf', 'per', 'P'],
           'augmented': ['aug', 'A', '+'],
           'diminished': ['dim', 'd', '°', 'o', '0'],
           'doubly augmented': ['aaug', 'AA'],
           'doubly diminished': ['ddim', 'dd']}
alias_qualities = unpack_and_reverse_dict(quality_aliases, include_keys=True)

quality_values = {   'doubly diminished': -3,
                     'diminished': -2,
                     'minor': -1,
                     'perfect': 0,
                     'major': 1,
                     'augmented': 2,
                     'doubly augmented': 3}
value_names = reverse_dict(quality_values)




class Quality:
    """class representing interval quality: major/minor-ness
    as well as perfect/augmented/diminished qualities
    with inversion method defined for the major-minor and aug-dim relationship"""
    def __init__(self, name=None, value=None):
        if name is not None:
            assert value is None, "Quality init must provide one of 'name' OR 'value', but got both"
            self.full_name, self.value = self._parse_input(name)
        elif value is not None:
            assert name is None, "Quality init must provide one of 'name' OR 'value', but got both"

            self.value = value
            self.full_name = value_names[value]
        else:
            raise Exception("Quality init must provide one of 'name' or 'value', but got neither")

        self.major = self.value == 1
        self.minor = self.value == -1
        self.perfect = self.value == 0
        self.augmented = self.value == 2
        self.diminished = self.value == -2
        self.doubly_augmented = self.value == 3
        self.doubly_diminished = self.value == -3

        # an interval is 'major-ish' if it is major/augmented, and 'minor-ish' if it is minor/diminished:
        self.major_ish = self.value >= 1
        self.minor_ish = self.value <= -1

        self.aug_ish = self.value >= 2
        self.dim_ish = self.value <= -2

        # an interval is 'doubled' if it is doubly augmented or doubly diminished
        self.doubled = (self.doubly_augmented or self.doubly_diminished)

    def _parse_input(self, inp):
        """accepts either a string denoting quality name, or an existing quality.
        sanitises input and returns the corresponding canonical name and quality value"""

        if isinstance(inp, Quality):
            # accept re-casting:
            return inp.full_name, inp.value
        elif isinstance(inp, str):
            # case-insensitive except for the crucial distinction between m and M:
            name = inp.lower() if len(inp) > 1 else inp

            if name in alias_qualities.keys():
                # cast to canonical string name (major/minor/perfect etc.) from possible aliases:
                canonical_name = alias_qualities[name]
                value = quality_values[canonical_name]
                return canonical_name, value
            else:
                raise Exception(f'Quality object init received unknown quality name: {inp}')

        else:
            raise Exception(f'Quality object initialised using name arg, expected string (or Quality object) but got type: {type(name)}')

    @staticmethod
    def from_offset_wrt_major(offset):
        # return Quality(major_offsets[offset])
        ### use pre-initialised Quality instance:
        if offset in major_offset_qualities:
            return major_offset_qualities[offset]
        else:
            raise ValueError(f'Tried to initialise a Quality with offset_wrt_major={offset}, which is too far to be doubly augmented or diminished')

    @staticmethod
    def from_offset_wrt_perfect(offset):
        # return Quality(perfect_offsets[offset])
        ### use pre-initialised Quality instance:
        if offset in perfect_offset_qualities:
            return perfect_offset_qualities[offset]
        else:
            raise ValueError(f'Tried to initialise a Quality with offset_wrt_perfect={offset}, which is too far to be doubly augmented or diminished')

    @staticmethod
    def from_value(value):
        return value_qualities[value]

    @staticmethod
    def from_cache(name=None, value=None):
        """efficient Quality object retrieval without init"""
        if value is not None:
            return value_qualities[value]
        elif name is not None:
            canonical_name = alias_qualities[name]
            value = quality_values[canonical_name]
            return value_qualities[value]

    def __invert__(self):
        """invert major to minor, aug to dim, or vice versa"""
        return value_qualities[self.value * -1]

    def __eq__(self, other):
        """qualities are emod to other qualities with the same name/value"""
        return self.value == other.value

    def __hash__(self):
        return hash(str(self))


    # interval offsets with respect to major or perfect qualities:
    @property
    def offset_wrt_major(self):
        """offsets relative to a major interval are 0 for major, -1 for minor, +1 for augmented etc."""
        assert self.value != 0, f"{self.full_name} quality should not have its offset compared to a major interval"
        return offsets_wrt_major[self.full_name]

    @property
    def offset_wrt_perfect(self):
        """offsets relative to a perfect interval are -1 if diminished and +1 if augmented"""
        assert self.value not in [-1, 1], f"{self.full_name} quality should not have its offset compared to a perfect interval"
        return offsets_wrt_perfect[self.full_name]

    @property
    def name(self):
        if not self.doubled:
            if self.major_ish:
                return self.full_name[:3].capitalize()
            elif self.perfect:
                return 'Ind'
            elif self.minor_ish:
                return self.full_name[:3]
        else:
            if self.doubly_augmented:
                return 'AAug'
            elif self.doubly_diminished:
                return 'ddim'

    @property
    def short_name(self):
        if not self.doubled:
            if self.major_ish or self.perfect:
                return self.full_name[0].upper()
            elif self.minor_ish:
                return self.full_name[0]
        else:
            if self.doubly_augmented:
                return 'AA'
            elif self.doubly_diminished:
                return 'dd'

    def __str__(self):
        lb, rb = self._brackets
        return f'{lb}{self.full_name}{rb}'

    def __repr__(self):
        return str(self)

    _brackets = _settings.BRACKETS['Quality']


# interval semitone distances from major or perfect interval degrees:

offsets_wrt_major = {'doubly diminished': -3,
                     'diminished': -2,
                     'minor': -1,
                     'major': 0,
                     'augmented': 1,
                     'doubly augmented': 2}

offsets_wrt_perfect = {'doubly diminished': -2,
                       'diminished': -1,
                       'perfect': 0,
                       'augmented': 1,
                       'doubly augmented': 2}

major_offsets = reverse_dict(offsets_wrt_major)
perfect_offsets = reverse_dict(offsets_wrt_perfect)


# pre-initialised quality dicts:
major_offset_qualities = {o: Quality(q) for o,q in major_offsets.items()}
perfect_offset_qualities = {o: Quality(q) for o,q in perfect_offsets.items()}
value_qualities = {v: Quality(q) for v,q in value_names.items()}

###############################################################

# pre-initialised interval qualities:

Major = Maj = M = Quality('major')
Minor = Min = m = Quality('minor')
Perfect = Perf = P = Ind = Indeterminate = Quality('perfect')
Augmented = Aug = A = Quality('augmented')
Diminished = Dim = d = Quality('diminished')
DoublyAugmented = AAug = AA = Quality('doubly augmented')
DoublyDiminished = DDim = dd = Quality('doubly diminished')

#################################################################


class ChordModifier:
    """a class representing the ways in which a Chord can be different from a major triad"""

    def __init__(self, alias=None, remove=None, add=None, make=None, modify=None, verify=None):
        """each Modifier can be instantiated by an alias, which searches the aliases of existing Modifiers,
        but is fully identified by its keyword args:
        remove (int or iterable): specify chord degree/s to remove, error if the specified degree does not exist.
        add (int, iterable or dict): specify a chord degree to add, and optionally an interval value to modify it by. error if that degree already exists
        make (dict): sets a chord degree to a specific distance-from-default, whether it exists or not
        modify (dict): specify an existing chord degree to modify up or down by some number of semitones. error if it doesn't exist
        verify (dict): specify that certain chord degrees must be satisfied, or gives error:
                       either present (True), absent (False) or a specific value (int)"""

        if alias is not None:
            assert (remove is None and add is None and modify is None), "ChordModifier must have either an alias OR some keyword args"
            remove, add, make, modify, verify = self._parse_name(alias)
        else:
            # must have one or more keyword args:
            kwargs = [remove, add, make, modify, verify]
            assert len([kw for kw in kwargs if kw is not None]) >= 1

        removals, additions, makes, modifications, verifications = remove, add, make, modify, verify

        # set of the degrees affected by this modifier:
        self.degrees = set()
        # dict of degree alterations (similar to a ChordFactors object) that gets parsed into a name later:
        # (for display purposes only, we do not guarantee this dict to have any consistent behaviour for strange inputs)
        self.summary = {}

        # remove any number of degrees:
        if removals is not None:
            assert isinstance(removals, (int, list, tuple)), f'"remove" arg to ChordModifier expected int, or iterable of ints, but got: {type(additions)}'
            self.removals = [removals] if isinstance(removals, int) else removals
            # self.degrees.update(removals)
            self.summary.update({r: False for r in self.removals})
        else:
            self.removals = []

        if additions is not None:
            if isinstance(additions, int):
                self.additions = {additions: 0}
            elif isinstance(additions, (tuple, list)):
                self.additions = {a:0 for a in additions}
            elif isinstance(additions, dict):
                self.additions = additions
            else:
                raise TypeError(f'"add" arg to ChordModifier expected int, or iterable/dict of ints, but got: {type(additions)}')
            self.degrees.update(self.additions.keys())
            self.summary.update(self.additions)
        else:
            self.additions = {}

        if make is not None:
            assert isinstance(make, dict), f'"make" arg to ChordModifier must be a dict, but got: {type(make)}'
            self.makes = makes
            self.degrees.update(self.makes.keys())
            self.summary.update(makes)
        else:
            self.makes = {}

        if modifications is not None:
            assert isinstance(modifications, dict), f'"modify" arg to ChordModifier must be a dict, but got: {type(modifications)}'
            for d, v in modifications.items():
                assert v != 0, f'"modify" arg to ChordModifier tried to modify degree {d} by 0, which does nothing'
                if d in self.summary:
                    self.summary[d] += v
                else:
                    self.summary[d] = v
            self.modifications = modifications
            self.degrees.update(self.modifications.keys())
        else:
            self.modifications = {}

        if verifications is not None:
            assert isinstance(verifications, dict), f'"verify" arg to ChordModifier must be a dict, but got: {type(verifications)}'
            self.verifications = verifications
        else:
            self.verifications = {}

        self.params = [self.removals, self.additions, self.makes, self.modifications, self.verifications]

        # sort the summary attribute:
        self.summary = {k : self.summary[k] for k in sorted(self.summary.keys())}

    def apply(self, factors):
        """accepts a Factors object, modifies it with the alterations in this modifier,
        and returns the result"""
        # assert isinstance(factors, dict), f"ChordModifiers can only be applied to Factors or dicts, but was attempted on: {type(factors)}"

        # original_class = factors.__class__
        # factors = dict(factors)

        # assert type(factors) is dict, "Can only apply ChordModifier to dict object"
        # in order: remove, add, modify

        # initialise a new dict to apply alteraitons to
        new_factors = dict(factors)
        # which then gets cast as Factors object as modification, since Factors are immutable

        # verify that certain degrees are present, absent or modified:
        for d, v in self.verifications.items():
            if v is False:
                assert d not in new_factors.keys(), f'ChordModifier {self.name} verification failed, expected no degree={d} in factors={factors}'
            elif v is True:
                assert d in new_factors.keys(), f'ChordModifier {self.name} verification failed, expected degree={d} in factors={factors}'
            elif isinstance(v, int):
                assert new_factors[d] == v, f'ChordModifier {self.name} verification failed, expected degree={d} to be {v}, but was {factors[d]}'


        # remove any number of existing degrees
        for d in self.removals:
            assert d in factors.keys(), f"ChordModifier {self.name} tried to remove missing degree={d} from Chord with factors={new_factors}"
            del new_factors[d]

        # add any number of degrees:
        for d, v in self.additions.items():
            assert d not in factors.keys(), f"ChordModifier {self.name} tried to add existing degree={d} to factors because it already exists: {new_factors}"
            new_factors[d] = v

        for d, v in self.makes.items():
            new_factors[d] = v

        # modify any number of existing degrees
        for d, v in self.modifications.items():
            assert d in factors.keys(), f"ChordModifier {self.name} tried to modify missing degree={d} from factors={new_factors}"
            new_factors[d] += v


        return factors.__class__(new_factors)

    def _parse_name(self, alias):
        """accepts the alias of a ChordModifier and returns appropriate parameters"""
        # re-cast existing ChordModifier as input:
        if isinstance(alias, ChordModifier):
            return alias.params
        elif isinstance(alias, str):
            if alias in alias_modifiers:
                alias = alias_modifiers[alias]
            if alias in chord_lookup:
                # this is already the name of a modifier e.g. maj7
                mod = chord_lookup[alias]
                return mod.params
            elif alias[0] in accidental_offsets:
                # this is an alteration, like b5 or #11:
                alter_dict = parse_alteration(alias)
                # return it as a Make:
                return None, None, alter_dict, None, None

            else:
                # this needs to be reduced to one
                mods = parse_chord_modifiers(alias)
                if len(mods) == 1:
                    return mods[0].params
                elif len(mods) > 2:
                    raise ValueError(f'{alias} refers not to one ChordModifier but to multiple: {mods}')
                else:
                    raise Exception
        else:
            raise TypeError(f'ChordModifier initialised with alias, expected to be string or ChordModifier object but got: {type(alias)}')



    def valid_on(self, other):
        """returns True if this is a valid modifier to apply to a given ChordFactors object, and false otherwise"""
        # from chords import ChordFactors # lazy import to avoid circular dependencies
        # proxy = ChordFactors(other)
        try:
            _ = self.apply(other)
        except:
            return False
        else:
            return True

    def describe(self):
        """Describes this ChordModifier object in natural language"""
        removals, additions, makes, modifications, verifications = [], [], [], [], []
        for d in self.removals:
            d_name = degree_names[d]
            removals.append(f'remove the {d_name}')
        removals = ','.join(removals).capitalize()
        for d in self.additions:
            perfect_degree = (d in [1, 4, 5])
            d_quality_name = 'perfect' if perfect_degree else 'major'
            d_name = degree_names[d]
            additions.append(f'add a {d_quality_name} {d_name}')
        additions = ','.join(additions).capitalize()
        for d, v in self.makes.items():
            perfect_degree = (d in [1, 4, 5])
            d_name = degree_names[d]
            d_quality_name = perfect_offsets[v] if perfect_degree else major_offsets[v]
            makes.append(f'make the {d_name} {d_quality_name}')
        makes = ','.join(makes).capitalize()
        for d, v in self.modifications.items():
            d_name = degree_names[d]
            modifier_names = {-1: 'flatten', 1: 'raise',
                              -2: 'double flatten', 2: 'double raise'}
            m_name = modifier_names[v]
            modifications.append(f'{m_name} the {d_name}')
        modifications = ','.join(modifications).capitalize()
        for d,v in self.verifications.items():
            d_name = degree_names[d]
            if v is True:
                verifications.append(f'Ensure the {d_name} is present')
            elif v is False:
                verifications.append(f'Ensure the {d_name} is absent')
            else:
                verification_names = {-1: 'flattened', 1: 'raised', -2: 'double flattened', 2: 'double raised',
                                       0: 'perfect' if d in [1,4,5] else 'major'}
                verifications.append(f'Ensure the {d_name} is {verification_names[v]}')
        verifications = ','.join(verifications).capitalize()
        return '\n'.join([removals, additions, makes, modifications, verifications]).strip()

    def __len__(self):
        """returns the total number of note alterations contained in this Modifier"""
        return len(self.summary)

    def get_name(self, check_chord_dicts=True):
        """lookup whether this modifier exists in the definition dicts, otherwise call it unnamed"""
        if check_chord_dicts:
            for lookup in [chord_types, chord_tweaks, chord_alterations]: #, chord_alterations]:
                rev_lookup = reverse_dict(lookup)
                if self in rev_lookup:
                    mod_name = rev_lookup[self]

                    return mod_name

        # no lookup exists (or not asked to find one):
        # so build up a name string from self.summary instead:
        name_str = []
        for deg, val in self.summary.items():
            if val: # i.e. not 0 (add) or False (remove)
                name_str.append(f'{offset_accidentals[val][0]}{deg}')
            elif val is False:
                name_str.append(f'no{deg}')
            elif val == 0:
                name_str.append(f'add{deg}')
        return ' '.join(name_str)
    @property
    def name(self):
        return self.get_name()

    @property
    def order(self):
        """returns, as an integer, the order of the resulting chord
        if this modifier were to be applied to a major triad."""
        order = 3 # by default
        added_degrees = set(self.degrees)
        # 1, 3 and 5 degrees are implicit, so remove them from set and don't consider them
        # unless they are removals, in which case they shrink the order
        for i in [1,3,5]:
            added_degrees.discard(i)
            if i in self.removals:
                order -= 1
        # anything remaining is a new degree:
        order += len(added_degrees)
        return order

    def __hash__(self):
        tuples = [tuple(x) for x in [self.removals, self.additions.keys(), self.additions.values(), self.makes.keys(), self.makes.values(),
                  self.modifications.keys(), self.modifications.values(), self.verifications.keys(), self.verifications.values()]]
        return hash(tuple(tuples))

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __str__(self):
        lb, rb = self._brackets
        return f'{lb}{self.name}{rb}'

    def __repr__(self):
        return str(self)

    # IntervalList object unicode identifier:
    _brackets = _settings.BRACKETS['ChordModifier']


# chord 'types' are those used to characterise a chord in its completeness:

chord_types =  {'m': ChordModifier(make={3:-1}),
                '5': ChordModifier(remove=3, verify={5:0}),
                'dim': ChordModifier(make={3:-1, 5:-1}),         # dimininished chord (m3+m3)
                'aug': ChordModifier(modify={5:+1}, verify={3:0}),   # augmented chord (M3+M3)
                '6': ChordModifier(add=6),                         # 6 chord aka add6

                '7': ChordModifier(add={7:-1}), # dominant 7th
                'dim7': ChordModifier(make={3:-1, 5:-1}, add={7:-2}),
                # '7b5': ChordModifier(add={7: -1}, modify={5:-1}),

                # note: m7, m9 etc. are implicit concatenations of 'm' and '7', '9' etc.
                # and mmaj7 is an implicit concatenation of 'm' and 'maj7'

                # but maj7 is NOT a concatenation of 'maj' and '7', since '7' implies dominant:
                'maj7': ChordModifier(add={7: 0}),
                # 'maj7b5': ChordModifier(add={7: 0}, modify={5:-1}),

                # explicit concatenations: (for chords that ought to be recognised during chord name searching)
                'm6': ['m', '6'],
                'hdim7': ['dim', '7'],    # half diminished 7th (diminished triad with minor 7th), also called m7b5
                '9': ['7', '♮9'],          # i.e. dominant 9th
                'maj9': ['maj7', '♮9'],    # major 9th
                f'7{fl}9': ['7', '♭9'],        # dominant minor 9th, (i.e. dm9?)
                'dim9': ['dim7', '♮9'],    # diminished 9th
                'dmin9': ['dim7', '♭9'],   # diminished minor 9th
                'hdim9': ['hdim7', '♮9'],  # half diminished 9th
                'hdmin9': ['hdim7', '♭9'],   # half diminished minor 9th
               f'7{sh}9': ['7', '♯9'],        # dominant 7 sharp 9, i.e. Hendrix chord

                '11': ['9', '♮11'],        # dominant 11th
                'maj11': ['maj9', '♮11'],  # major 11th
                'dmin11': ['dmin9', '♮11'],  # diminished minor 11th
                'hdim11': ['hdim9', '♮11'],  # half-diminished 11th
                'hdmin11': ['hdmin9', '♮11'],  # half-diminished minor 11th

                '13': ['11', '♮13'],               # dominant 13th
                'maj13': ['maj11', '♯11', '♮13'],  # major 13th with a raised 11th
               f'maj13{nat}11': ['maj11', '♮13'],         # major 13th WITHOUT raised 11th
                'dmin13': ['dmin11', '♮13'],  # diminished minor 11th
                'hdim13': ['hdim11', '♮13'],  # half-diminished 11th
                'hdmin13': ['hdmin11', '♮13'],  # half-diminished minor 11th
                }


# chord 'tweaks' are those that could conceivably tweak an existing chord type:
# note that this dict order matters, since it affects the order in which chords get named: (e.g. add9sus4 instead of sus4add9)
chord_tweaks = {    'sus4': ChordModifier(remove=3, add=4, verify={2:False}),
                    'sus2': ChordModifier(remove=3, add=2, verify={4:False}),

                    'add4': ChordModifier(add=4, verify={9: False, 11:False}), # are these real? or just add11s

                    'add9': ChordModifier(add={9:0}, verify={7: False, 2:False}),
                    'add11': ChordModifier(add=11, verify={9: False, 4:False}),
                    'add13': ChordModifier(add=13, verify={11: False, 6:False, 5:0, 7:True}), # verify natural 5 is a kludge, see: Bbdim9add13/C

                    '(no5)': ChordModifier(remove=5), # , verify={3: True, 10:False}),    # we don't need verifiers on this because no5s are not registered anywhere, just treated as a valid input
                 f'({fl}5)': ChordModifier(make={5:-1}, verify={3:0}),
                    }

# add degree alterations too:
chord_alterations = {}
for acc in [fl, sh]:
   for deg in range(5,14):
       acc_val = accidental_offsets[acc]
       chord_alterations[f'{acc}{deg}'] = ChordModifier(make={deg:acc_val})

# union of them all:
chord_lookup = {**chord_types, **chord_tweaks, **chord_alterations}

# string replacements for chord searching:
modifier_aliases = { 'maj' : ['major', 'M', 'Δ', 'ᐞ'],
                      'm'  : ['minor', 'min', '-',],
                      'sus': ['suspended', 's', 'ˢ'],
                      'dim': ['diminished', 'o', '°',],
                      'aug': ['augmented', '+', '⁺'],
                      # special case: the chord 'half-dim' is implicitly a 7th, but 'hdim7' is clearer than 'hdim'
                    'hdim7': ['ø', 'ø7', 'hdim', 'half-diminished', 'half-dim', 'm7b5', 'm7♭5', 'tristan'],
                     'add' : ['added', 'ᵃ'],
                    '(no5)': ['no5', '(omit5)'],

                     # bit of a kludge; but 'domX' always refers to an 'X' chord,
                     # so we map 'dom' to nothing and it all works fine
                         '': ['dominant', 'dom'],

                     # another kludge: "maj7", "maj9" in particular need to be caught as
                     # explicit concatenations:
                     'maj7': ['maj7', 'add7'],
                     # (add7 is an awkward case because a maj7 shouldn't really be called that,
                     # but if you DO say 'add7' it implies a natural rather than a flat 7)
                     'maj9': ['maj9'],
                    'maj11': ['maj11'],
                    'maj13': ['maj13'],

                        '2': ['two', '2nd', 'second', '²'],
                        '3': ['three', '3rd', 'third', '³'],
                        '4': ['four', '4th', 'fourth', '⁴'],
                        '5': ['five', '5th', 'fifth', '(no3)', 'power', 'power chord', '⁵'],
                        '6': ['six', '6th', 'sixth', 'add6', '⁶'],
                        '7': ['seven', '7th', 'seventh', '⁷'],
                        '8': ['eight', '8th', 'eighth', '⁸'],
                        '9': ['nine', '9th', 'ninth', '⁹'],
                       '10': ['ten', '10th', 'tenth', '¹⁰'],
                       '11': ['eleven', '11th', 'eleventh', '¹¹'],
                       '12': ['twelve', '12th', 'twelfth', '¹²'],
                       '13': ['thirteen', '13th', 'thirteenth', '¹³'],

                      # special edge cases, otherwise 'dmin9' etc. doesn't parse correctly:
                    'hdim9': ['hdim9', 'ø9'],
                   'hdim11': ['hdim11', 'ø11'],
                   'hdim13': ['hdim13', 'ø13'],
                   'hdmin9': ['hdmin9', 'hdimm9', 'hdimmin9'],
                  'hdmin11': ['hdmin11', 'hdimm11', 'hdimmin11'],
                  'hdmin13': ['hdmin13', 'hdimm13', 'hdimmin13'],
                    'dmin9': ['dmin9', 'dimm9', 'dimmin9'],
                   'dmin11': ['dmin11', 'dimm11', 'dimmin11'],
                   'dmin13': ['dmin13', 'dimm13', 'dimmin13'],
                  f'7{fl}9': ['dm9', 'domin9', 'domm9'],
                  f'7{sh}9': ['hendrix', 'purple haze'],

                    # map all accidentals back onto preferred char
                         sh: ['#', '♯', 'sh', 'sharpened', 'sharped', 'raised'],
                         fl: ['b', '♭', 'fl', 'flattened', 'flatted', 'lowered'],
                        dsh: ['𝄪', '♯♯', '##', 'dsh'],
                        dfl: ['𝄫', '♭♭', 'bb', 'dfl'],
                        nat: ['♮', 'N', 'with', 'include', 'nat', 'natural'],
                    }

alias_modifiers = unpack_and_reverse_dict(modifier_aliases)



def parse_chord_modifiers(mod_str, aliases=modifier_aliases, verbose=False, allow_note_names=False, catch_duplicates=False):
    """given a string of modifiers that typically follows a chord root,
    e.g. 7sus4add11♯5,
    recursively parse them into a list of ChordModifier objects"""

    reduced_mods = reduce_aliases(mod_str, aliases, reverse=True, include_keys=True)
    if not allow_note_names:
        if is_valid_note_name(reduced_mods[0], case_sensitive=True):
            raise ValueError(f'parse_chord_modifiers got fed a string starting with a note name: {mod_str} (parsed as {reduced_mods})')

    # special case: 'sus' alone without qualification refers to 'sus4'
    if reduced_mods == ['sus']:
        reduced_mods = ['sus4']

    # we need to catch a special case: 'major' as first modifier NOT followed by an extended degree number
    major_in_front = (len(reduced_mods) >= 1 and reduced_mods[0] == 'maj')
    followed_by_degree = (len(reduced_mods) >= 2 and reduced_mods[1] in ['7', '9', '11', '13'])
    if major_in_front:
        if not followed_by_degree:
            reduced_mods = reduced_mods[1:]

    standard_form_modifier_string = ''.join(reduced_mods)

    raw_mod_ops = reduce_aliases(standard_form_modifier_string, chord_lookup, discard=True)

    # have we ended up with an empty list, even though we had something OTHER than just 'major' in the input?
    found_nothing = len(raw_mod_ops) == 0 and not major_in_front
    found_major_and_nothing = len(raw_mod_ops) == 0 and major_in_front and len(reduced_mods) >= 2
    if found_nothing or found_major_and_nothing:
        raise ValueError(f"Tried to parse chord modifiers but did not find any matches for: {''.join(reduced_mods)}")

    # raw_mod_ops might include iterables (concatenations),
    # so we loop through those and process them:
    # try:
    mod_ops = cast_modifiers(raw_mod_ops, verbose=verbose)
    # except ValueError as e:
    #     raise Exception(f'Could not understand {mod_str} (parsed as {reduced_mods}) as valid chord alias.\nSpecific issue: {e}')

    if catch_duplicates:
        # minor kludge: if we end up parsing the same modifier twice
        # (due to a naming redundancy like 'hdim7')
        # we want to ignore any repeats of the same modifier:
        clean_ops = [mod_ops[0]]
        for i in range(1, len(mod_ops)):
            if mod_ops[i] != clean_ops[-1]:
                clean_ops.append(mod_ops[i])
            else:
                log(f'Duplicate mod while parsing {mod_str} up to {clean_ops}: {mod_ops[i]}')
        mod_ops = clean_ops

    return mod_ops

def cast_modifiers(mod, verbose=False):
    """accepts a ChordModifier object, a string that casts to one, or a list of either,
    and recursively returns a strict list of ChordModifier objects"""
    mod_list = []
    if isinstance(mod, ChordModifier):
        if verbose:
            print(f'{mod} is already a ChordModifier, appending...')
        mod_list.append(mod)
    elif isinstance(mod, str):
        # could be a string that exists in chord_types or chord_modifiers
        # so fetch it and convert to ChordModifier object(or list of such)
        if mod in chord_lookup:
            fetched_mod = chord_lookup[mod]
            if isinstance(fetched_mod, ChordModifier):
                mod_list.append(fetched_mod)
            elif isinstance(fetched_mod, (list, tuple)):
                if verbose:
                    print(f'Recursively going down a level to parse: {fetched_mod} (which turns out to be a list)')
                mod_list.extend(cast_modifiers(fetched_mod, verbose=verbose))
            elif isinstance(fetched_mod, str):
                if fetched_mod in chord_lookup:
                    mod_list.extend(cast_modifiers(fetched_mod, verbose=verbose))
                else:
                    raise ValueError(f'Invalid string provided to cast_modifiers: {mod} (parsed as {fetched_mod}) does not indicate a chord type')
        else:
            # # could be a chord alteration, like ♭5 or ♯7
            # alter_dict = parse_alteration(mod)
            # mod_list.append(ChordModifier(make=alter_dict))
            log(f'Found a possible chord alteration: {mod}')
            mods = cast_alterations(mod)
            log(f'Parsed as: {mods}')
            mod_list.extend(mods)
            # if (len(mod) in [2,3]) and (mod[0] in accidental_ops):
            #     degree = mod[1:]
            #     op = accidental_ops[mod[0]]
            #     mod_list.append(ChordModifier(make={degree:op}))
            # else:

            # raise ValueError(f'Invalid string provided to cast_modifiers: {mod} \n  (expected a chord_type, chord_modifier or chord_alteration)')
    elif isinstance(mod, (list, tuple)):
        # is an iterable of acceptable objects, so call recursively
        for each_mod in mod:
            if verbose:
                from ipdb import set_trace; set_trace(context=30)
                print(f'Recursively going down a level to parse: {each_mod} (which is an item in a list)')
            mod_list.extend(cast_modifiers(each_mod, verbose=verbose))
    else:
        raise TypeError(f'cast_modifiers expected a ChordModifier, or a string that casts to one, or a list/tuple of either, but got: {type(mod)}')
    return mod_list


def cast_alterations(name):
    """given a string that contains one or more chord alterations,
    like '#9' or 'b9b11', parse them into a list of ChordModifiers"""

    # assume that 'name' has already been reduced to standard form,
    # i.e. modifier_aliases keys

    # loop through the string to parse out accidentals
    # and the degrees they modify:
    accidental_degrees = []

    current_accidental = None
    current_degree_chars = []
    for char in name:
        if char in accidental_offsets:

            if len(current_degree_chars) == 0:
                # start of loop
                current_accidental = char
            else:
                # found a second-or-more accidental:
                # so turn the previous degree into an int:
                degree = int(''.join(current_degree_chars))
                accidental_degrees.append((current_accidental, degree))
                # and start a new alteration:
                current_accidental = char
                current_degree_chars = []

        else:
            # must be a number! if it is, append to current degree
            assert char.isnumeric()
            current_degree_chars.append(char)

    # add last-parsed-one to list as well:
    degree = int(''.join(current_degree_chars))
    accidental_degrees.append((current_accidental, degree))

    # loop through alterations and make ChordModifier objects:
    modifiers = []
    for acc,degree in accidental_degrees:
        acc_value = accidental_offsets[acc]
        mod = ChordModifier(make={degree: acc_value})
        modifiers.append(mod)
    return modifiers

# pre-initialised modifiers used in progressions etc:
minor_mod = ChordModifier('minor')
dim_mod = ChordModifier('diminished')
aug_mod = ChordModifier('augmented')
