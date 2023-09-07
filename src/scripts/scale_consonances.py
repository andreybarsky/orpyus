import scales

# display all scale consonances:
all_consonances = {}
for name, factors in scales.canonical_scale_name_factors.items():
    sc = Scale(name)
    all_consonances[sc] = sc.consonance

sorted_scales = sorted(all_consonances, key=lambda x: all_consonances[x], reverse=True)
cons_names = [sc.name for sc in sorted_scales]
cons_values = [all_consonances[sc] for sc in sorted_scales]

df_pent = DataFrame(['Scale Name',
                'Consonance'])
df_other = DataFrame(['Scale Name',
            'Consonance'])
for scale, cons in zip(sorted_scales, cons_values):
    if scale.is_pentatonic():
        df_pent.append([scale.name, round(cons,3)])
    else:
        df_other.append([scale.name, round(cons,3)])
print(f'\n=== Pentatonic scale consonances: ===')
df_pent.show()

print(f'\n=== Other scale consonances: ===')
df_other.show()

import numpy as np
print(f'Highest consonance: {np.max(cons_values):.05f} ({cons_names[np.argmax(cons_values)]})')
print(f'Lowest consonance: {np.min(cons_values):.05f} ({cons_names[np.argmin(cons_values)]})')
