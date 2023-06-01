from ..parsing import parse_out_note_names, parse_alteration
from .testing_tools import compare

def unit_test():
    compare(parse_out_note_names('CbbBbAGbE##C'), ['Cbb', 'Bb', 'A', 'Gb', 'E##', 'C'])
    compare(parse_out_note_names('Cbb-Bb-A-Gb-E##-C'), ['Cbb', 'Bb', 'A', 'Gb', 'E##', 'C'])
    compare(parse_alteration('b5'), {5:-1})
    compare(parse_alteration('#11'), {11:+1})
    compare(parse_alteration('7'), {7:0})
