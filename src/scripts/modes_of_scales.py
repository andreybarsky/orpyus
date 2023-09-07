import scales, parsing

# which scales are modes of each other?
base_scale_modes = {}
for name, factors in scales.canonical_scale_name_factors.items():
    scale = scales.Scale(name)
    its_modes = scale.modes[1:]
    registered_mode = False
    for m, mode in enumerate(its_modes):
        if mode in base_scale_modes:
            registered_mode = True
            which_mode = (len(mode)+1) - (m+1)
            num_suffix = parsing.num_suffixes[which_mode]
            base_mode_name = mode.name
            if base_mode_name not in base_scale_mode_names:
                print(f'  ++++ {scale.name} is the {which_mode}{num_suffix} mode of {base_mode_name}')
            else:
                print(f'  -- {scale.name} is the {which_mode}{num_suffix} mode of {base_mode_name}')
            break
    if not registered_mode:
        print(f'Registering {scale.name} as a base scale')
        base_scale_modes[scale] = its_modes
