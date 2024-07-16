from src.progressions import common_progressions

# guitar-playable variants of the common progressions:
for prog, name in common_progressions.items():
    cprogs = prog.transpose_for_guitar(return_all=True)
    desc = '\n'
    if len(cprogs) == 0:
        cprogs = prog.simplify().transpose_for_guitar(return_all=True)
        desc += '(simplified)\n'
    cprogs_str = desc + '\n'.join([str(p) for p in cprogs]) + '\n===='
    print(f'{name}: {cprogs_str}')
