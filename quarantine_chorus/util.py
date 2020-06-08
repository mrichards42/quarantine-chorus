import funcy as F


def deep_merge(*dicts):
    return F.merge_with(
        lambda v: deep_merge(*v) if isinstance(v[0], dict) else v[-1],
        *dicts
    )
