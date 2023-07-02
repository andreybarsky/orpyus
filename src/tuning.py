from . import _settings
import math
# just intonation that attempts to find close matches to equal temperament:

ratio_max_left = ratio_max_right = _settings.RATIO_MAX

def just_intonation(ratio_max_left=ratio_max_left, ratio_max_right=ratio_max_right):
    harmonic_ratios = [(a,b) for a in range(1,RATIO_MAX_LEFT+1) for b in range(a,RATIO_MAX_RIGHT+1)]
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
        iv = Interval(i)
        print(f'\n{iv} ({iv.ratio}, {(iv.ratio[0] / iv.ratio[1]):.3f}): Searching for number close to desired step interval: {step:.3f}')
        # find the next real that is higher than this step:
        real = harmonic_reals[real_idx]
        while real < step:
            prev_real = real
            real_idx += 1
            real = harmonic_reals[real_idx]
        print(f' Stopped at real: {real:.3f} (ratio: {reals_to_ratios[real]}), previous value: {prev_real:.3f} (ratio: {reals_to_ratios[prev_real]})')
        # check if this real or the previous one is closer to our perfect step interval:
        prev_dist, cur_dist = abs(prev_real - step), abs(real - step)
        if prev_dist > cur_dist:
            chosen_ratio = reals_to_ratios[real]
            print(f'  Current real is closer ({real:.3f} vs {prev_real:.3f}), so accepting its ratio of: {chosen_ratio}')
        else:
            chosen_ratio = reals_to_ratios[prev_real]
            print(f'  Previous real is closer ({prev_real:.3f} vs {real:.3f}), so accepting its ratio of: {chosen_ratio}')
        steps_to_ratios.append(chosen_ratio)

    just_steps = [r[0]/r[1] for r in steps_to_ratios]
    return steps_to_ratios, just_steps
