from ._settings import TUNING_SYSTEM, A4_PITCH, NOTE_RANGE
from .util import log, euclidean_gcd
import math


### TBI: implement meantone?

# 12-TET ('equal') tuning:
# find equal temperament by placing 13 notes in a line:
root, octave = 1.0, 2.0
log_start, log_end = math.log(root), math.log(octave)
log_step = (log_end - log_start) / 12
log_steps = [log_start + (i*log_step) for i in range(13)]
equal_steps = [math.exp(s) for s in log_steps]

# 'rational' tuning: approximate 12-TET but with rational side lengths up to 50.
# this is imperceptibly different from 12-TET, but having rational side lengths
# allows for much easier consonance calculation.

def build_rational_harmonics(harmonic_range):
    # must round due to floating-point precision problems:
    rational_harmonics_to_rational_reals = {(a,b): round(a/b,8) for i, a in enumerate(harmonic_range) for b in harmonic_range[:i] if 1<=(a/b)<=2}
    rational_reals_to_rational_harmonics = {}
    for ratio, real in rational_harmonics_to_rational_reals.items():
        if real not in rational_reals_to_rational_harmonics:
            rational_reals_to_rational_harmonics[real] = ratio
        else:
            # conflict: use the one with the lowest sides
            old_ratio, new_ratio = rational_reals_to_rational_harmonics[real], ratio
            old_gcd = euclidean_gcd(*old_ratio)
            new_gcd = euclidean_gcd(*new_ratio)
            if old_gcd > new_gcd:
                # new is better, so overwrite it
                rational_reals_to_rational_harmonics[real] = new_ratio
    rational_harmonics = sorted(list(rational_reals_to_rational_harmonics.values()))
    return rational_reals_to_rational_harmonics, rational_harmonics

# 'rational' tuning uses side lengths up to a reasonable limit (in this case 50)
rational_reals_to_harmonics, rational_harmonics = build_rational_harmonics(range(1,100))
# whereas 'equal' tuning does not necessarily guarantee rational numbers, but
# under this simplifying assumption we choose rationals that are imperceptibly close,
# by allowing side lengths up to 200:
equal_reals_to_harmonics, equal_harmonics = build_rational_harmonics(range(1,1000))

def obtain_tuning(harmonic_ratios):
    """given a set of allowable harmonic ratios, finds a series of ratios and steps
    for the 12 notes inside an octave that gets closest to 12-tone equal temperament.
    if the harmonic ratios are limit-5, this gets us something like just intonation.
    if they are rational ratios, this gets us close to 12-tone equal temperament
        (but avoiding any irrational frequency ratios from root)"""
    harmonic_reals = [(a/b) for (a,b) in harmonic_ratios]
    ratios_to_reals, reals_to_ratios = {}, {}
    for ratio, real in zip(harmonic_ratios, harmonic_reals):
        if real not in reals_to_ratios:
            reals_to_ratios[real] = ratio
            ratios_to_reals[ratio] = real
        else:
            # conflict: use the one with the lowest sides
            old_ratio, new_ratio = reals_to_ratios[real], ratio
            old_gcd = euclidean_gcd(*old_ratio)
            new_gcd = euclidean_gcd(*new_ratio)
            if old_gcd > new_gcd:
                # new is better, so overwrite it
                reals_to_ratios[real] = ratio
    harmonic_reals = sorted(reals_to_ratios.keys())
    harmonic_ratios = [reals_to_ratios[re] for re in harmonic_reals]

    # find equal temperament by placing 13 notes in a line:
    root, octave = 1.0, 2.0
    log_start, log_end = math.log(root), math.log(octave)
    log_step = (log_end - log_start) / 12
    log_steps = [log_start + (i*log_step) for i in range(13)]
    theoretical_steps = [math.exp(s) for s in log_steps]

    # 12-note just intonation tuning loop:
    steps_to_ratios = [(1,1)]
    real_idx = 0
    for i in range(1, 12):
        step = theoretical_steps[i]
        log(f'\nSearching for number close to desired step interval: {step:.3f}')
        # find the next real that is higher than this step:
        real = harmonic_reals[real_idx]
        while real < step:
            prev_real = real
            real_idx += 1
            real = harmonic_reals[real_idx]
        log(f' Stopped at real: {real:.3f} (ratio: {reals_to_ratios[real]}), previous value: {prev_real:.3f} (ratio: {reals_to_ratios[prev_real]})')
        # check if this real or the previous one is closer to our perfect step interval:
        prev_dist, cur_dist = abs(prev_real - step), abs(real - step)
        if prev_dist > cur_dist:
            chosen_ratio = reals_to_ratios[real]
            log(f'  Current real is closer ({real:.3f} vs {prev_real:.3f}), so accepting its ratio of: {chosen_ratio}')
        else:
            chosen_ratio = reals_to_ratios[prev_real]
            log(f'  Previous real is closer ({prev_real:.3f} vs {real:.3f}), so accepting its ratio of: {chosen_ratio}')
        steps_to_ratios.append(chosen_ratio)

    obtained_steps = [r[0]/r[1] for r in steps_to_ratios]
    # final step/ratio is always the 2:1 octave:
    obtained_steps.append(2.0)
    steps_to_ratios.append((2,1))

    return steps_to_ratios, obtained_steps

# equal temperament tuning:
rational_ratios, rational_steps = obtain_tuning(rational_harmonics)
equal_approximation_ratios, equal_approximation_steps = obtain_tuning(equal_harmonics)


# five-limit tuning:
limit5_reals = []
power_range = (-5,5)
for power2 in range(*power_range):
    for power3 in range(*power_range):
        for power5 in range(*power_range):
            limit5_real = 2**power2 * 3**power3 * 5**power5
            if 1 <= limit5_real <= 2:
                limit5_reals.append(round(limit5_real,8))
limit5_harmonics_to_reals = {}
limit5_reals_to_harmonics = {}
for real5 in limit5_reals:
    if real5 in rational_reals_to_harmonics:
        ratio5 = rational_reals_to_harmonics[real5]
        limit5_harmonics_to_reals[ratio5] = real5
        if real5 not in limit5_reals_to_harmonics:
            limit5_reals_to_harmonics[real5] = ratio5
        else:
            # conflict: use the one with the lowest sides
            old_ratio, new_ratio = ratio5, limit5_reals_to_harmonics[real5]
            old_gcd = euclidean_gcd(*old_ratio)
            new_gcd = euclidean_gcd(*new_ratio)
            if old_gcd > new_gcd:
                # new is better, so overwrite it
                limit5_reals_to_harmonics[real5] = ratio5

limit5_harmonics = sorted(list(set(list(limit5_reals_to_harmonics.values()))))
just_ratios, just_steps = obtain_tuning(limit5_harmonics)

cache = {'JUST': (just_ratios, just_steps),
         'RATIONAL': (rational_ratios, rational_steps),
         'EQUAL': (equal_approximation_ratios, equal_steps)}

INTONATION = TUNING_SYSTEM.upper()
assert INTONATION in cache.keys(), f'{INTONATION} as defined in _settings is not a valid tuning; try JUST, EQUAL or RATIONAL'

# define pitches for each note value:
v_start, v_end = NOTE_RANGE
value_range = range(v_start,v_end) # 0-100 goes from Ab0 to C9

# for equal tuning this is easily calculable by formula:
equal_value_pitches = {v: round(2 ** ((v-49)/12) * A4_PITCH, 3) for v in value_range}

# for non-equal tunings this is more complicated:
just_value_pitches = {}
rational_value_pitches = {}
# outer loop ranges across all the octaves we need to cover:
for A_octave in range((v_start-1)//12,((v_end-1)//12 + 1)):
    A_value = (A_octave*12)+1
    # the pitch of this octave's A is a (repeated) halving or doubling from reference A:
    A_pitch = A4_PITCH / 2**(4-A_octave)
    # inner loop ranges from A - Ab in this octave, unless that is outside our desired range:
    start_val = max(A_value, v_start)
    end_val = min(((A_octave+1)*12)+1, v_end)
    # print(f'Will calculate from {start_val} to {end_val}, exclusive')
    # print(f'Inside octave {A_octave}, where A_value is {A_value} ({OctaveNote(A_value)}) and A_pitch is {A_pitch}')
    for v in range(start_val, end_val):
        if v == A_value:
            # just use the A pitch without further calculation
            just_value_pitches[v] = rational_value_pitches[v] = A_pitch
        else:
            interval_from_A = v - A_value
            just_value_pitches[v] = round(A_pitch * just_steps[interval_from_A],3)
            rational_value_pitches[v] = round(A_pitch * rational_steps[interval_from_A],3)

value_pitches = {'EQUAL': equal_value_pitches,
                 'JUST': just_value_pitches,
                 'RATIONAL': rational_value_pitches}

def get_pitch(value, intonation=None):
    """get the pitch of a specified OctaveNote value according to a specified intonation system,
    which should be one of EQUAL, JUST, or RATIONAL. if unspecified, uses the default intonation
    as specified in _settings.TUNING_SYSTEM"""
    if intonation is None:
        intonation = INTONATION # fall back on default
    else:
        intonation = intonation.upper()
    return value_pitches[intonation][value]

def get_ratios(intonation=None):
    if intonation is None:
        intonation = INTONATION # fall back on default
    else:
        intonation = intonation.upper()
    return cache[intonation][0]

def get_steps(intonation=None):
    if intonation is None:
        intonation = INTONATION # fall back on default
    else:
        intonation = intonation.upper()
    return cache[intonation][1]

def set_intonation(intonation):
    """set the global tuning intonation system to one of: JUST, RATIONAL, or EQUAL"""
    global INTONATION
    intonation = intonation.upper()
    assert intonation in cache.keys(), f'{INTONATION} is not a valid tuning mode: try JUST, RATIONAL, or EQUAL'
    INTONATION = intonation

def get_intonation():
    return INTONATION

def __getattr__(name):
    ratios, steps = cache[INTONATION]
    if name == 'ratios':
        return ratios
    elif name == 'steps':
        return steps
