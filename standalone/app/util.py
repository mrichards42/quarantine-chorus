def oxford_join(strs):
    if len(strs) == 1:
        return strs[0]
    elif len(strs) == 2:
        return f"{strs[0]} and {strs[1]}"
    else:
        return " and ".join([
            ' '.join(x + ',' for x in strs[:-1]),
            strs[-1]
        ])
