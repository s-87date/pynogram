# -*- coding: utf-8 -*-
"""Define nonogram solver that solves line-by-line"""

from __future__ import unicode_literals, print_function

import logging
import time

from six.moves import (
    zip, range,
)

from pynogram.core.common import (
    UNKNOWN, BOX, SPACE,
    is_color_cell,
)
from pynogram.core.line import solve_line
# from pynogram.core.line.machine import assert_match
from pynogram.utils.priority_dict import PriorityDict

LOG = logging.getLogger(__name__)


def _is_pixel_updated(old, new):
    if old == new:
        return False

    if is_color_cell(old):
        # old value contains more '1'-s in the binary representation
        assert old > new
    else:
        assert old == UNKNOWN
        assert new in (BOX, SPACE)

    return True


def solve_row(board, index, is_column, method):
    """
    Solve a line with the solving `method`.
    If the line gets partially solved,
    put the crossed lines into queue.

    Return the list of new jobs that should be solved next (one for each solved cell).
    """

    # start = time.time()

    if is_column:
        row_desc = board.columns_descriptions[index]
        row = tuple(board.get_column(index))
        # desc = 'column'
    else:
        row_desc = board.rows_descriptions[index]
        row = tuple(board.get_row(index))
        # desc = 'row'

    # pre_solution_rate = board.line_solution_rate(row)

    # if board.is_line_solved(row):
    #     # do not check solved lines in trusted mode
    #     if contradiction_mode:
    #         assert_match(row_desc, row)
    #     return 0, ()

    # LOG.debug('Solving %s %s: %s. Partial: %s', index,
    #           'column' if is_column else 'row', row_desc, row)

    updated = solve_line(row_desc, row, method=method, normalized=True)

    new_jobs = []

    # if board.line_solution_rate(updated) > pre_solution_rate:
    if row != updated:
        # LOG.debug('Queue: %s', jobs_queue)
        # LOG.debug(row)
        # LOG.debug(updated)
        for i, (pre, post) in enumerate(zip(row, updated)):
            if _is_pixel_updated(pre, post):
                new_jobs.append((not is_column, i))
        # LOG.debug('Queue: %s', jobs_queue)
        # LOG.debug('New info on %s %s: %s', desc, index, [job_index for _, job_index in new_jobs])

        if is_column:
            board.set_column(index, updated)
        else:
            board.set_row(index, updated)

    # LOG.debug('%ss solution: %.6f sec', desc, time.time() - start)
    return new_jobs


def solve(board,
          row_indexes=None, column_indexes=None,
          contradiction_mode=False, methods=None):
    """
    Solve the nonogram to the most using two methods (by default):
    - firstly with simple right-left overlap algorithm
    - then with FSM and reverse tracking

    All methods use priority queue to store the lines needed to solve.

    Return the total number of solved cells.
    """

    if methods is None:
        if board.is_colored:
            if board.has_blots:
                methods = ('blot_color',)
            else:
                methods = ('bgu_color',)
        else:
            if board.has_blots:
                methods = ('blot',)
            else:
                # methods = ('simpson', 'reverse_tracking')
                methods = ('bgu',)

    if not isinstance(methods, (tuple, list)):
        methods = [methods]

    total_cells_solved = 0
    for method in methods:
        cells_solved, jobs = _solve_with_method(
            board, method,
            row_indexes=row_indexes,
            column_indexes=column_indexes,
            contradiction_mode=contradiction_mode)

        total_cells_solved += cells_solved
        row_indexes = [index for is_column, index in jobs if not is_column]
        column_indexes = [index for is_column, index in jobs if is_column]

    return total_cells_solved


def _solve_with_method(
        board, method,
        row_indexes=None, column_indexes=None,
        contradiction_mode=False):
    """Solve the nonogram to the most using given method"""

    # `is_solved_full` is cost, so minimize calls to it.
    # Do not call if only a handful of lines has to be solved
    if row_indexes is None or column_indexes is None or \
            len(row_indexes) > 2 or len(column_indexes) > 2:

        # do not shortcut in contradiction_mode
        if not contradiction_mode and board.is_solved_full:
            return 0, ()

    has_blots = board.has_blots

    start = time.time()
    lines_solved = 0

    # every job is a tuple (is_column, index)
    #
    # Why `is_column`, not `is_row`?
    # To assign more priority to the rows:
    # when adding row, `is_column = False = 0`
    # when adding column, `is_column = True = 1`
    # heap always pops the lowest item, so the rows will go first

    LOG.debug('Solving %s rows and %s columns with %r method',
              row_indexes, column_indexes, method)

    line_jobs = PriorityDict()
    all_jobs = set()

    def _add_job(job, _priority):
        line_jobs[job] = _priority
        all_jobs.add(job)

    if row_indexes is None:
        row_indexes = range(board.height)
    for row_index in row_indexes:
        # the more this line solved
        # priority = 1 - board.row_solution_rate(row_index)

        # the closer to edge
        # priority = 1 - abs(2.0 * row_index / board.height - 1)

        # the more 'dense' this line
        # priority = 1 - board.densities[False][row_index]

        new_job = (False, row_index)

        priority = 0
        if has_blots:
            # the more attempts the less priority
            priority = board.attempts_to_try(*new_job)

        _add_job(new_job, priority)

    if column_indexes is None:
        column_indexes = range(board.width)
    for column_index in column_indexes:
        # the more this line solved
        # priority = 1 - board.column_solution_rate(column_index)

        # the closer to edge
        # priority = 1 - abs(2.0 * column_index / board.width - 1)

        # the more 'dense' this line
        # priority = 1 - board.densities[True][column_index]

        new_job = (True, column_index)

        priority = 0
        if has_blots:
            # the more attempts the less priority
            priority = board.attempts_to_try(*new_job)

        _add_job(new_job, priority)

    total_cells_solved = 0

    for (is_column, index), priority in line_jobs.sorted_iter():
        # LOG.info('Solving %s %s with priority %s', index,
        #          'column' if is_column else 'row', priority)

        new_jobs = solve_row(board, index, is_column, method)

        total_cells_solved += len(new_jobs)
        for new_job in new_jobs:
            new_priority = priority - 1
            if board.has_blots:
                # the more attempts the less priority
                new_priority = board.attempts_to_try(*new_job)

            # lower priority = more priority
            _add_job(new_job, new_priority)

        lines_solved += 1

    # all the following actions applied only to verified solving
    if not contradiction_mode:
        board.solution_round_completed()

        # rate = board.solution_rate
        # if rate != 1:
        #     LOG.warning('The nonogram is not solved full (%r). The rate is %.4f',
        #                 method, rate)
        LOG.info('Full solution: %.6f sec', time.time() - start)
        LOG.info('Lines solved: %i', lines_solved)

    return total_cells_solved, all_jobs
