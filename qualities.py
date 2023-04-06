# OOP representation of major/minor quality that is invertible and has a null (indeterminate) value
from util import reverse_dict, unpack_and_reverse_dict, test, log

# TBI: double dim/aug qualities?

#### interval qualities:

quality_aliases = {'major': ['maj', 'M'],
           'minor': ['min', 'm'],
           'perfect': ['indeterminate', 'ind', 'null', 'perf', 'P'],
           'augmented': ['aug', 'A', '+'],
           'diminished': ['dim', 'd', '°', 'o', '0']}
alias_qualities = unpack_and_reverse_dict(quality_aliases, include_keys=True)

quality_values = {'diminished': -2,
                     'minor': -1,
                     'perfect': 0,
                     'major': 1,
                     'augmented': 2}
value_qualities = reverse_dict(quality_values)




class Quality:
    """class representing interval quality: major/minor-ness
    as well as perfect/augmented/diminished qualities
    with inversion method defined for the major-minor and aug-dim relationship"""
    def __init__(self, name=None, value=None):
        if name is not None:
            assert value is None, "Quality init must provide one of 'name' OR 'value', but got both"
            self.name, self.value = self._parse_input(name)
        elif value is not None:
            assert name is None, "Quality init must provide one of 'name' OR 'value', but got both"

            self.value = value
            self.name = value_qualities[value]
        else:
            raise Exception("Quality init must provide one of 'name' or 'value', but got neither")

        self.major = self.value == 1
        self.minor = self.value == -1
        self.perfect = self.value == 0
        self.augmented = self.value == 2
        self.diminished = self.value == -2

        # if we want to check whether this quality is major-ish (i.e. major or augmented), etc., we have these:
        self.major_ish = self.value >= 1
        self.minor_ish = self.value <= -1

    def _parse_input(self, inp):
        """accepts either a string denoting quality name, or an existing quality.
        sanitises input and returns the corresponding canonical name and quality value"""
        if isinstance(inp, str):
            # case-insensitive except for the crucial distinction between m and M:
            name = inp.lower() if len(inp) > 1 else inp

            if name in alias_qualities.keys():
                # cast to canonical string name (major/minor/perfect etc.) from possible aliases:
                canonical_name = alias_qualities[name]
                value = quality_values[canonical_name]
                return canonical_name, value
            else:
                raise Exception(f'Quality object init received unknown quality name: {inp}')

        elif isinstance(inp, Quality):
            # catch if we have been fed an existing Quality,
            # in which case just re-init:
            return inp.name, inp.value
        else:
            raise Exception(f'Quality object initialised using name arg, expected string (or Quality object) but got type: {type(name)}')


    def __invert__(self):
        """invert major to minor, aug to dim, or vice versa"""
        return Quality(value = self.value * -1)

    def __eq__(self, other):
        """qualities are equal to other qualities with the same name/value"""
        return self.value == other.value

    def __str__(self):
        return f'~Quality:{self.name}~'

    def __repr__(self):
        return str(self)

    # interval offsets with respect to major or perfect qualities:
    @property
    def offset_wrt_major(self):
        """offsets relative to a major interval are 0 for major, -1 for minor, +1 for augmented etc."""
        assert self.value != 0, f"{self.name} quality should not have its offset compared to a major interval"
        return offsets_wrt_major[self.name]

    @property
    def offset_wrt_perfect(self):
        """offsets relative to a perfect interval are -1 if diminished and +1 if augmented"""
        assert self.value not in [-1, 1], f"{self.name} quality should not have its offset compared to a perfect interval"
        return offsets_wrt_perfect[self.name]

    @staticmethod
    def from_offset_wrt_major(offset):
        return Quality(major_offsets[offset])

    @staticmethod
    def from_offset_wrt_perfect(offset):
        return Quality(perfect_offsets[offset])

# interval semitone distances from major or perfect interval degrees:

offsets_wrt_major = {'diminished': -2,
                     'minor': -1,
                     'major': 0,
                     'augmented': 1}

offsets_wrt_perfect = {'diminished': -1,
                       'perfect': 0,
                       'augmented': 1}

major_offsets = reverse_dict(offsets_wrt_major)
perfect_offsets = reverse_dict(offsets_wrt_perfect)

###############################################################

# pre-initialised interval qualities:

Major = Maj = Quality('major')
Minor = Min = Quality('minor')
Perfect = Perf = Quality('perfect')
Augmented = Aug = Quality('augmented')
Diminished = Dim = Quality('diminished')

#################################################################


class ChordQualifier:
    """a class representing the ways in which a Chord can be different from a major triad"""
    def __init__(self, alias=None, remove=None, add=None, make=None, modify=None, verify=None):
        """each Qualifier can be instantiated by an alias, which searches the aliases of existing Qualifiers,
        but is fully identified by its keyword args:
        remove (int or iterable): specify chord degree/s to remove, error if the specified degree does not exist.
        add (int, iterable or dict): specify a chord degree to add, and optionally an interval value to modify it by.
        make (dict): sets a chord degree to a specific distance-from-default, whether it exists or not
        modify (dict): specify an existing chord degree to modify up or down by some number of semitones
        verify (dict): specify that certain chord degrees must be satisfied:
                       either present (True), absent (False) or a specific value (int)"""

        if alias is not None:
            assert (remove is None and add is None and modify is None), "ChordQualifier must have either an alias OR some keyword args"
            remove, add, make, modify, verify = self._parse_name(alias)
        else:
            # must have one or more keyword args:
            kwargs = [remove, add, make, modify, verify]
            assert len([kw for kw in kwargs if kw is not None]) >= 1

        removals, additions, makes, modifications, verifications = remove, add, make, modify, verify

        # remove any number of degrees:
        if removals is not None:
            assert isinstance(removals, (int, list, tuple)), f'"remove" arg to ChordQualifier expected int, or iterable of ints, but got: {type(additions)}'
            self.removals = [removals] if isinstance(removals, int) else removals
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
                raise TypeError(f'"add" arg to ChordQualifier expected int, or iterable/dict of ints, but got: {type(additions)}')
        else:
            self.additions = {}

        if make is not None:
            assert isinstance(make, dict), f'"make" arg to ChordQualifier must be a dict, but got: {type(make)}'
            self.makes = makes
        else:
            self.makes = {}

        if modifications is not None:
            assert isinstance(modifications, dict), f'"modify" arg to ChordQualifier must be a dict, but got: {type(modifications)}'
            for d, v in modifications.items():
                assert v != 0, f'"modify" arg to ChordQualifier tried to modify degree {d} by 0, which does nothing'
            self.modifications = modifications
        else:
            self.modifications = {}

        if verifications is not None:
            assert isinstance(verifications, dict), f'"verify" arg to ChordQualifier must be a dict, but got: {type(verifications)}'
            self.verifications = verifications

    def apply(self, factors):
        """modify a ChordFactors object with the alterations specified in this Qualifier"""
        assert isinstance(factors, ChordFactors), f"ChordQualifiers can only be applied to ChordFactors, but was attempted on: {type(factors)}"
        # in order: remove, add, modify

        # remove any number of existing degrees
        for d in self.removals:
            assert d in factors.keys(), f"ChordQualifier {self.name} tried to remove missing degree={d} from Chord with factors={factors}"
            del factors[d]

        # add any number of degrees:
        for d, v in self.additions.items():
            assert d not in factors.keys(), f"ChordQualifier {self.name} tried to add existing degree={d} to factors because it already exists: {factors}"
            factors[d] = v

        for d, v in self.makes.items():
            factors[d] = v

        # modify any number of existing degrees
        for d, v in self.modifications.items():
            assert d in factors.keys(), f"ChordQualifier {self.name} tried to modify missing degree={d} from factors={factors}"
            factors[d] += v

        # verify that certain degrees are present, absent or modified:
        for d, v in self.verifications.items():
            if v is False:
                assert d not in factors.keys(), f'ChordQualifier {self.name} verification failed, expected no degree={d} in factors={factors}'
            elif v is True:
                assert d in factors.keys(), f'ChordQualifier {self.name} verification failed, expected degree={d} in factors={factors}'
            elif isinstance(v, int):
                assert factors[d] == v, f'ChordQualifier {self.name} verification failed, expected degree={d} to be {v}, but was {factors[d]}'

    def valid_on(self, other):
        """returns True if this is a valid qualifier to apply to a given ChordFactors object, and false otherwise"""
        proxy = deepcopy(other)
        try:
            self.apply(proxy)
        except:
            return False
        else:
            return True

    def describe(self):
        """Describes this ChordQualifier object in natural language"""
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
            modifications.append(f'{m_name} the {d_name})
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
        return '\n'.join([removals, additions, makes, modifications, verifications])


    def __str__(self):
        name = f': {self.name}' if self.name is not None else ''
        return f'ChordQualifier{self.name}\n' + self.describe()

    def __repr__(self):
        return str(self)

    def __hash__(self):
        tuples = [tuple(x) for x in [self.removals, self.additions, self.makes.keys(), self.makes.values(),
                  self.modifications.keys(), self.modifications.values(), self.verifications.keys(), self.verifications.values()]]
        return hash(tuple(tuples))

# # qualifiers not used in actual chords, but which might be used by chord_qualifier concatenations:
# misc_qualifiers = {'raise5': ChordQualifier(modify={5:+1}),
#                    'lower5': ChordQualifier(modify={5:-1}),
#                    }
#
# chord_formulas =  {'♭5': ChordQualifier(make={5:-1}),
#                    '♯5': ChordQualifier(make={5:+1}),
#                    '♭7': ChordQualifier(make={7:-1}),
#                    '♯7': ChordQualifier(make={7:+1}),
#                    '♭9': ChordQualifier(make={9:-1}),
#                    '♯9': ChordQualifier(make={9:+1}),
#                    '♭11': ChordQualifier(make={11:-1}),
#                    '♯11': ChordQualifier(make={11:+1})}

# chord 'types' are those used to characterise a chord in its completeness:
chord_types =  {'m': ChordQualifier(make={3: -1}),
                '5': ChordQualifier(remove=3, verify={5:0}),
                'dim': ChordQualifier(modify={3:-1, 5:-1}),
                'aug': ChordQualifier(modify={5:+1}, verify={3:0}),
                '6': ChordQualifier(add=6),

                '7': ChordQualifier(make={7: -1}), # dominant 7th
                'maj7': ChordQualifier(make={7: 0}, verify={3:0}),
                'dim7': ChordQualifier(make={3:-1, 5:-1, 7:-2}),
                # m7 is an implicit concatenation of 'm' and '7'
                # mmaj7 is an implicit concatenation of 'm' and 'maj7'

                # explicit concatenations:
                'hdim7': ['dim', '7'],    # half diminished 7th (diminished triad with minor 7th)
                '9': ['7', '♮9'],          # i.e. dominant 9th
                'm9': ['m7', '♮9'],      # minor 9th
                'maj9': ['maj7', '♮9'],    # major 9th
                'dmin9': ['7', '♭9'],         # dominant minor 9th

                '11': ['9', '♮11'],
                'm11': ['m9', '♮11'],
                'maj11': ['maj9', '♮11'],
                }


# chord 'modifiers' are those that could conceivably modify an existing chord type:
chord_modifiers = {'(no5)': ChordQualifier(remove=5),
                    'sus4': ChordQualifier(remove=3, add=4),
                    'sus2': ChordQualifier(remove=3, add=2),

                    'add9': ChordQualifier(add={9:0}, verify={7: False}),
                    'add11': ChordQualifier(add=11, verify={9: False}),
                    'add4': ChordQualifier(add=4),

                    # # alterations:
                    # '♭5': ChordQualifier(make={5:-1}),
                    # '♯5': ChordQualifier(make={5:+1}),
                    # '♭7': ChordQualifier(make={7:-1}),
                    # '♯7': ChordQualifier(make={7:+1}),
                    # '♭9': ChordQualifier(make={9:-1}),
                    # '♯9': ChordQualifier(make={9:+1}),
                    # '♭11': ChordQualifier(make={11:-1}),
                    # '♯11': ChordQualifier(make={11:+1}),
                    }


# string replacements for chord searching:
qualifier_aliases = {'': ['maj', 'maj3', 'M', 'Ma', 'major', 'dominant', 'dom'],
                     'm': ['min', 'min3', '-', 'minor'],
                     'sus': ['s', 'suspended'],
                     '4': ['4th', 'four', 'fourth'],
                     '2': ['2nd', 'two', 'second'],
                     '6': ['add6'], # no such thing as an add6
                     'dim': ['o', '°', 'diminished'],
                     'aug': ['+','augmented'],
                     'hdim': ['ø', 'half diminished', 'half dim'],
                     'add': ['added'],
                     '♯': ['#', 'sharp', 'sharpened', 'raised'],
                     '♭': ['b', 'flat', 'flattened', 'lowered'],
                     '5': ['five', 'fifth', '5th'],
                     '7': ['seven', '7th', 'seventh'],
                     'maj7': ['Δ', 'Δ7'],
                     '9': ['nine', '9th', 'ninth'],
                     '11': ['eleven', '11th', 'eleventh']
                     }


def parse_chord_qualifiers(qual_str):
    """given a string of qualifiers that typically follows a chord root,
    e.g. 7sus4add11♯5,
    recursively parse them into a list of ChordQualifier objects"""

###############################

def unit_test():
    # test quality initialisation:
    test(Quality('major'), Quality('M'))
    test(Quality('Indeterminate'), Quality(value=0))
    # test quality inversion:
    test(~Quality('major'), Quality('minor'))
    test(~Quality('dim'), Quality('aug'))
    # test quality from offset:
    test(Quality.from_offset_wrt_major(-1), Quality('minor'))
    test(Quality.from_offset_wrt_perfect(1), Quality('augmented'))

if __name__ == '__main__':
    unit_test()
