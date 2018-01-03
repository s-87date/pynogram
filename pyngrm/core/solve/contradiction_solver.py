# -*- coding: utf-8 -*
"""Define nonogram solver that uses contradictions"""

from __future__ import unicode_literals, print_function

import logging
import os
import time

from pyngrm.core import UNKNOWN, BOX, invert
from pyngrm.core.solve import NonogramError, NonogramFSM, line_solver

_LOG_NAME = __name__
if _LOG_NAME == '__main__':  # pragma: no cover
    _LOG_NAME = os.path.basename(__file__)

LOG = logging.getLogger(_LOG_NAME)


def try_contradiction(board, row_index, column_index,
                      assumption=BOX, propagate=True):
    """
    Try to find if the given cell can be in an assumed state.
    If the contradiction is found, set the cell
    in an inverted state and propagate the changes if needed.
    """
    # already solved
    if board.cells[row_index][column_index] != UNKNOWN:
        return

    save = board.cells.copy()
    contradiction = False

    try:
        try:
            LOG.debug('Pretend that (%i, %i) is %s',
                      row_index, column_index, assumption)
            board.cells[row_index][column_index] = assumption
            line_solver.solve(
                board,
                row_indexes=(row_index,),
                column_indexes=(column_index,),
                contradiction_mode=True)
        except NonogramError:
            contradiction = True
        else:
            if board.solution_rate == 1:
                LOG.warning("Found one of the solutions!")
    finally:
        # rollback solved cells
        board.cells = save
        if contradiction:
            LOG.info("Found contradiction at (%i, %i)",
                     row_index, column_index)
            board.cells[row_index][column_index] = invert(assumption)

            # try to solve with additional info
            if propagate:
                # solve with only one cell as new info
                line_solver.solve(
                    board,
                    row_indexes=(row_index,),
                    column_indexes=(column_index,))


def _contradictions_round(
        board, assumption,
        propagate_on_cell=True, by_rows=True):
    """
    Solve the nonogram with contradictions
    by trying every cell and the basic `solve` method.

    :param assumption: which state to try: BOX or SPACE
    :param propagate_on_cell: how to propagate changes:
    after each solved cell or in the end of the row
    :param by_rows: iterate by rows (left-to-right) or by columns (top-to-bottom)
    """

    if by_rows:
        for solved_row in range(board.height):
            if board.row_solution_rate(board.cells[solved_row]) == 1:
                continue

            LOG.info('Trying to assume on row %i', solved_row)
            for solved_column in range(board.width):
                try_contradiction(
                    board,
                    solved_row, solved_column,
                    assumption=assumption,
                    propagate=propagate_on_cell
                )

            if not propagate_on_cell:
                # solve with only one row as new info
                line_solver.solve(
                    board, row_indexes=(solved_row,))
    else:
        for solved_column in range(board.width):
            if board.row_solution_rate(board.cells.T[solved_column]) == 1:
                continue

            LOG.info('Trying to assume on column %i', solved_column)
            for solved_row in range(board.height):
                try_contradiction(
                    board,
                    solved_row, solved_column,
                    assumption=assumption,
                    propagate=propagate_on_cell
                )

            if propagate_on_cell:
                # solve with only one column as new info
                line_solver.solve(
                    board, column_indexes=(solved_column,))


def solve(
        board, propagate_on_row=False, by_rows=True):
    """
    Solve the nonogram to the most with contradictions
    and the basic `solve` method.

    :type board: Board
    :param propagate_on_row: how to propagate changes:
    in the end of the row or after each solved cell
    :param by_rows: iterate by rows (left-to-right) or by columns (top-to-bottom)
    """

    line_solver.solve(board)
    if board.solution_rate == 1:
        board.set_solved()
        LOG.info('No need to solve with contradictions')
        return

    LOG.warning('Trying to solve using contradictions method')
    propagate_on_cell = not propagate_on_row
    board.set_solved(False)
    start = time.time()

    solved = board.solution_rate
    counter = 0

    assumption = BOX  # try the different assumptions every time

    while True:
        counter += 1
        LOG.warning('Contradiction round %i (assumption %s)', counter, assumption)

        _contradictions_round(
            board, assumption,
            propagate_on_cell=propagate_on_cell,
            by_rows=by_rows)

        if board.solution_rate > solved:
            board.solution_round_completed()

        if board.solution_rate == 1 or solved == board.solution_rate:
            break

        solved = board.solution_rate
        assumption = invert(assumption)

    board.set_solved()
    if board.solution_rate != 1:
        LOG.warning('The nonogram is not solved full (with contradictions). '
                    'The rate is %.4f', board.solution_rate)
    LOG.info('Full solution: %.6f sec', time.time() - start)
    LOG.info('Cache hit rate: %.4f%%', NonogramFSM.solutions_cache().hit_rate * 100.0)
