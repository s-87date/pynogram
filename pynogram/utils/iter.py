# -*- coding: utf-8 -*-
"""
Here lie the utilities methods that does not depend on any domain
e.g. manipulations with collections or streams.
"""

from __future__ import unicode_literals, print_function, division

import sys
from functools import partial, wraps
from itertools import islice


def merge_dicts(*dict_args, **kwargs):
    """
    Thanks Aaron Hall http://stackoverflow.com/a/26853961/
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    """
    _type = kwargs.get('type', dict)
    # noinspection PyCallingNonCallable
    result = _type()
    for dictionary in dict_args:
        result.update(dictionary)
    return result


def pad(coll, size, padding, left=True):
    """
    Pad the collection `coll` with `padding` items
    until it reaches the length of `size`.
    By default do padding in the beginning (on the left side).
    """
    padding_size = size - len(coll)
    if padding_size <= 0:
        return coll

    padding = [padding] * padding_size
    new_list = list(coll)
    return padding + new_list if left else new_list + padding


def interleave(list_a, list_b):
    """
    >>> interleave([0, 2, 4, 6], [1, 3, 5])
    [0, 1, 2, 3, 4, 5, 6]

    https://stackoverflow.com/a/7947461
    """
    size_a, size_b = len(list_a), len(list_b)
    if size_a - size_b not in (0, 1):
        raise ValueError("The lists' sizes are too different: ({}, {})"
                         .format(size_a, size_b))
    res = [None] * (size_a + size_b)
    res[::2] = list_a
    res[1::2] = list_b
    return res


def max_safe(*args, **kwargs):
    """
    Returns max element of an iterable.

    Adds a `default` keyword for any version of python that do not support it
    """
    if sys.version_info < (3, 4):  # `default` supported since 3.4
        if len(args) == 1:
            arg = args[0]
            if 'default' in kwargs:
                default = kwargs.pop('default')
                if not arg:
                    return default

                # https://stackoverflow.com/questions/36157995#comment59954203_36158079
                arg = list(arg)
                if not arg:
                    return default

                # if the `arg` was an iterator, it's exhausted already
                # so use a new list instead
                return max(arg, **kwargs)

    return max(*args, **kwargs)


def list_replace(a_list, old, new):
    """
    Replaces every `old` item in `a_list` with `new` item
    """
    for i, item in enumerate(a_list):
        if item == old:
            a_list[i] = new


def split_seq(iterable, size):
    """
    Split `iterable` into chunks with specified `size`
    # http://stackoverflow.com/a/312467/

    :param iterable: any iterable
    :param size: chunk size
    :return: chunks one by one
    """
    iterator = iter(iterable)
    item = list(islice(iterator, size))
    while item:
        yield item
        item = list(islice(iterator, size))


def avg(iterable):
    """
    Return the average value of an iterable of numbers
    """

    # the iterable can be an iterator that gets exhausted
    # while `sum` and `len` will return 0
    list_copy = list(iterable)
    if not list_copy:
        return None

    return sum(list_copy) / len(list_copy)


def expand_generator(func=None, type_=list):
    """
    Escape the common list construction idiom by creating generator functions.
    You can also produce another iterable (e.g. tuple)

    Compare:
    def foo_list():                                  @expand_generator
        foo = []                                     def foo():
        while something:                                 while something:
            if something_more:                               if something_more:
                foo.append('X')          vs                      yield 'X'
            else:                                            else:
                foo.append('Y')                                  yield 'Y'

        return foo

    TODO: consider replacing with Andrey Petrov's `listify`
    https://github.com/shazow/unstdlib.py/blob/master/unstdlib/standard/list_.py#L149
    """
    if func is None:
        return partial(expand_generator, type_=type_)

    @wraps(func)
    def wrapper(*args, **kwargs):
        # noinspection PyArgumentList
        return type_(func(*args, **kwargs))

    return wrapper


def max_continuous_interval(int_list):
    """
    The size of the longest continuous
    number sequence in a list
    """
    int_list = sorted(int_list)

    if not int_list:
        return 0

    max_size = 1
    first, last = int_list[0], int_list[0]
    for number in int_list[1:]:
        if number == last + 1:
            last = number
        else:
            max_size = max(max_size, last - first + 1)  # save previous range
            first, last = number, number

    max_size = max(max_size, last - first + 1)
    return max_size
