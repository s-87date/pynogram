# -*- coding: utf-8 -*
"""Define common solving utilities"""

from __future__ import unicode_literals, print_function

from pyngrm.utils.cache import Cache


class NonogramError(ValueError):
    """
    Represents an error occurred when trying
    to solve a nonogram which has an internal contradiction.
    """
    pass


class LineSolutionsMeta(type):
    """
    A metaclass for line solvers.
    It adds the solutions_cache to the solver class.
    """

    def __new__(mcs, *args, **kwargs):
        new_cls = super(LineSolutionsMeta, mcs).__new__(mcs, *args, **kwargs)
        new_cls.solutions_cache = Cache(10000)
        return new_cls
