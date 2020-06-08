"""Lazy utils."""


class static_cached_property:
    """A static cached property decorator.

    Similar to functools.cached_property (in python 3.8), but instead of maintaining a
    cache, replaces the attr on the owner with the cached result."""
    def __init__(self, func):
        self.func = func
        self.name = None

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner=None):
        result = self.func()
        if instance:
            setattr(instance, self.name, result)
        elif owner:
            setattr(owner, self.name, result)
        return result
