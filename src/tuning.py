from . import _settings
from .util import log, euclidean_gcd
import math
import ipdb

rational_range = range(1, 300)
# must round due to floating-point precision problems:
rational_ratios_to_rational_reals = {(a,b): round(a/b,8) for i, a in enumerate(rational_range) for b in rational_range[:i] if 1<=(a/b)<=2}
rational_reals_to_rational_ratios = {}
for ratio, real in rational_ratios_to_rational_reals.items():
    if real not in rational_reals_to_rational_ratios:
        rational_reals_to_rational_ratios[real] = ratio
    else:
        # conflict: use the one with the lowest sides
        old_ratio, new_ratio = rational_reals_to_rational_ratios[real], ratio
        old_gcd = euclidean_gcd(*old_ratio)
        new_gcd = euclidean_gcd(*new_ratio)
        if old_gcd > new_gcd:
            # new is better, so overwrite it
            rational_reals_to_rational_ratios[real] = new_ratio
rational_ratios = sorted(list(rational_reals_to_rational_ratios.values()))

def obtain_tuning(harmonic_ratios):
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
    log(f'Obtaining tunings according to tuning_mode={_settings.TUNING_MODE}')
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

# five-limit tuning:
limit5_reals = []
power_range = (-5,5)
for power2 in range(*power_range):
    for power3 in range(*power_range):
        for power5 in range(*power_range):
            limit5_real = 2**power2 * 3**power3 * 5**power5
            if 1 <= limit5_real <= 2:
                limit5_reals.append(round(limit5_real,8))
limit5_ratios_to_reals = {}
limit5_reals_to_ratios = {}
for real5 in limit5_reals:
    if real5 in rational_reals_to_rational_ratios:
        ratio5 = rational_reals_to_rational_ratios[real5]
        limit5_ratios_to_reals[ratio5] = real5
        if real5 not in limit5_reals_to_ratios:
            limit5_reals_to_ratios[real5] = ratio5
        else:
            # conflict: use the one with the lowest sides
            old_ratio, new_ratio = ratio5, limit5_reals_to_ratios[real5]
            old_gcd = euclidean_gcd(*old_ratio)
            new_gcd = euclidean_gcd(*new_ratio)
            if old_gcd > new_gcd:
                # new is better, so overwrite it
                limit5_reals_to_ratios[real5] = ratio5

limit5_ratios = sorted(list(set(list(limit5_reals_to_ratios.values()))))
just_ratios, just_steps = obtain_tuning(limit5_ratios)
# equal temperament tuning:
equal_ratios, equal_steps = obtain_tuning(rational_ratios)

def __getattr__(name):
    if _settings.TUNING_MODE.upper() == 'JUST':
        if name == 'ratios':
            return just_ratios
        elif name == 'steps':
            return just_steps
    elif _settings.TUNING_MODE.upper() == 'EQUAL':
        if name == 'ratios':
            return equal_ratios
        elif name == 'steps':
            return equal_steps
    else:
        raise Exception(f'Invalid tuning mode {_settings.TUNING_MODE}; must be one of JUST or EQUAL')
