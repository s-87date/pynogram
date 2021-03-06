# -*- coding: utf-8 -*-
"""
Defines various renderers for the game of nonogram
"""

from __future__ import unicode_literals, print_function, division

from itertools import combinations

try:
    from abc import ABC
except ImportError:
    from abc import ABCMeta

    # https://stackoverflow.com/a/38668373
    ABC = ABCMeta(str('ABC'), (object,), {'__slots__': ()})

import codecs
import logging
from sys import stdout

from six import (
    integer_types, text_type,
    iteritems, itervalues,
    PY2,
)

from pynogram.core.common import (
    UNKNOWN, BOX, SPACE, SPACE_COLORED,
    is_list_like,
    Color,
    is_color_cell,
    BlottedBlock,
)
from pynogram.utils.iter import (
    pad,
    split_seq,
    max_safe,
)
from pynogram.utils.other import (
    two_powers, from_two_powers,
)

_LOG_NAME = __name__
LOG = logging.getLogger(_LOG_NAME)

# prevent "UnicodeEncodeError: 'ascii' codec can't encode character ..."
# when redirecting output
if PY2:
    stdout = codecs.getwriter('utf8')(stdout)


class Cell(object):
    """Represent basic rendered cell"""

    DEFAULT_ICON = ' '

    def __init__(self, icon=None):
        self.icon = icon or self.DEFAULT_ICON

    def ascii_icon(self):
        """How the cell can be printed as a text"""
        return self.DEFAULT_ICON

    def __repr__(self):
        return '{}()'.format(self.__class__.__name__)


class ThumbnailCell(Cell):
    """
    Represent upper-left cell
    (where the thumbnail of the puzzle usually drawn).
    """
    DEFAULT_ICON = '#'


class ClueCell(Cell):
    """
    Represent cell that is part of description (clue).
    They are usually drawn on the top and on the left.
    """

    BLOTTED_SYMBOL = '?'

    def __init__(self, value):
        super(ClueCell, self).__init__()
        if is_list_like(value):
            self.value, self.color = value
        else:
            self.value, self.color = value, None

    def ascii_icon(self):
        """
        Gets a symbolic representation of a cell given its state
        and predefined table `icons`
        """
        if isinstance(self.value, integer_types):
            return text_type(self.value)

        if self.value == BlottedBlock:
            return self.BLOTTED_SYMBOL

        return self.DEFAULT_ICON

    def __repr__(self):
        return '{}(({}, {}))'.format(
            self.__class__.__name__,
            self.value, self.color)


class GridCell(Cell):
    """Represent the main area cell"""

    def __init__(self, value, renderer, colored=False):
        super(GridCell, self).__init__()

        self.renderer = renderer
        self.colored = colored
        if self.colored:
            self.value = tuple(two_powers(value))
        else:
            self.value = value

    def ascii_icon(self):
        value = self.value
        icons = self.renderer.icons

        if not self.colored:
            return icons[self.value]

        if len(value) == 1:
            value = value[0]
        else:
            # multiple colors
            value = UNKNOWN

        symbol = self.renderer.board.symbol_for_color_id(value)
        if symbol is not None:
            return symbol

        return icons.get(value, self.DEFAULT_ICON)

    def __repr__(self):
        return '{}({})'.format(
            self.__class__.__name__, self.value)


class _DummyBoard(object):
    """
    Stub for renderer initialization
    when it created before the corresponding board
    """
    rows_descriptions = columns_descriptions = ()
    width = height = 0


class Renderer(object):
    """Defines the abstract renderer for a nonogram board"""

    def __init__(self, board=None):
        self.cells = None
        self.board = None
        self.board_init(board)

    def board_init(self, board=None):
        """Initialize renderer's properties dependent on board it draws"""
        if board:
            LOG.info('Init %r renderer with board %r',
                     self.__class__.__name__, board)
        else:
            if self.board:
                return  # already initialized, do nothing
            board = _DummyBoard()
        self.board = board

    @property
    def full_height(self):
        """The full visual height of a board"""
        return self.header_height + self.board.height

    @property
    def full_width(self):
        """The full visual width of a board"""
        return self.side_width + self.board.width

    @property
    def header_height(self):
        """The size of the header block with columns descriptions"""
        return max_safe(map(len, self.board.columns_descriptions), default=0)

    @property
    def side_width(self):
        """The width of the side block with rows descriptions"""
        return max_safe(map(len, self.board.rows_descriptions), default=0)

    def render(self):
        """Actually print out the board"""
        raise NotImplementedError()

    def draw(self, cells=None):
        """Calculate all the cells and draw an image of the board"""
        self.draw_header()
        self.draw_side()
        self.draw_grid(cells=cells)
        self.render()

    def draw_header(self):
        """
        Changes the internal state to be able to draw columns descriptions
        """
        raise NotImplementedError()

    def draw_side(self):
        """
        Changes the internal state to be able to draw rows descriptions
        """
        raise NotImplementedError()

    def draw_grid(self, cells=None):
        """
        Changes the internal state to be able to draw a main grid
        """
        raise NotImplementedError()

    @property
    def is_colored(self):
        """Whether the linked board is colored board"""
        return self.board.is_colored


class StreamRenderer(Renderer, ABC):
    """
    Simplify textual rendering of a board to a stream (stdout by default)
    """

    DEFAULT_ICONS = {
        UNKNOWN: '_',
        BOX: 'X',
        SPACE: '.',
    }

    def __init__(self, board=None, stream=stdout, icons=None):
        self.stream = stream
        if icons is None:
            icons = dict(self.DEFAULT_ICONS)
        self.icons = icons
        super(StreamRenderer, self).__init__(board)

    def _print(self, *args):
        return print(*args, file=self.stream)


class BaseAsciiRenderer(StreamRenderer):
    """
    Renders a board as a simple text table (without grid)
    """

    __rend_name__ = 'text'

    def board_init(self, board=None):
        super(BaseAsciiRenderer, self).board_init(board)
        LOG.info('init cells: %sx%s', self.full_width, self.full_width)

        self.cells = [[Cell()] * self.full_width
                      for _ in range(self.full_height)]

    def cell_icon(self, cell):
        """
        Get a symbolic representation of a cell given its state
        and predefined table `icons`
        """
        return cell.ascii_icon()

    def render(self):
        for row in self.cells:
            res = []
            for index, cell in enumerate(row):
                ico = self.cell_icon(cell)

                # do not pad the last symbol in a line
                if len(ico) == 1:
                    if index < len(row) - 1:
                        ico += ' '

                res.append(ico)

            self._print(''.join(res))

    def draw_header(self):
        for i in range(self.header_height):
            for j in range(self.side_width):
                self.cells[i][j] = ThumbnailCell()

        for j, col in enumerate(self.board.columns_descriptions):
            rend_j = j + self.side_width
            if not col:
                col = [0]

            rend_column = [ClueCell(val) for val in col]
            rend_column = pad(rend_column, self.header_height, Cell())

            # self.cells[:self.header_height, rend_j] = rend_column
            for i, cell in enumerate(rend_column):
                self.cells[i][rend_j] = cell

    def draw_side(self):
        for i, row in enumerate(self.board.rows_descriptions):
            rend_i = i + self.header_height
            # row = list(row)
            if not row:
                row = [0]

            rend_row = [ClueCell(val) for val in row]
            rend_row = pad(rend_row, self.side_width, Cell())
            self.cells[rend_i][:self.side_width] = rend_row

    def draw_grid(self, cells=None):
        if cells is None:
            cells = self.board.cells

        is_colored = self.is_colored

        for i, row in enumerate(cells):
            rend_i = i + self.header_height
            for j, val in enumerate(row):
                rend_j = j + self.side_width
                self.cells[rend_i][rend_j] = GridCell(
                    val, self, colored=is_colored)


class AsciiRenderer(BaseAsciiRenderer):
    """
    Renders the board as a full-blown ASCII table
    with headers, grid and borders
    """

    __rend_name__ = 'text-grid'

    DEFAULT_ICONS = {
        UNKNOWN: '?',
        BOX: '#',
        SPACE: ' ',
    }

    # cannot fit the value more than '999'
    CELL_WIDTH = 3
    HORIZONTAL_LINE_PAD = '-'
    VERTICAL_GRID_SYMBOL = '|'
    HEADER_DELIMITER = '='
    SIDE_DELIMITER_SIZE = 2
    GRID_CROSS_SYMBOL = '+'
    CORNER_SYMBOL = GRID_CROSS_SYMBOL

    BOLD_LINE_HORIZONTAL = HORIZONTAL_LINE_PAD
    BOLD_LINE_VERTICAL_SIZE = 1
    BOLD_LINE_EVERY = 5

    def _cell_horizontal_border(self, header=False, bold=False):
        if header:
            padding = self.HEADER_DELIMITER
        elif bold:
            padding = self.BOLD_LINE_HORIZONTAL
        else:
            padding = self.HORIZONTAL_LINE_PAD

        return padding * self.CELL_WIDTH

    def _side_delimiter(self, grid=False):
        """
        Separates side descriptions from the main grid.
        Default values are '||' for the data rows or
        '++' for the 'grid' rows.
        """
        size = self.SIDE_DELIMITER_SIZE

        if grid:
            delimiter = self.GRID_CROSS_SYMBOL
        else:
            delimiter = self.VERTICAL_GRID_SYMBOL
        return delimiter * size

    def _horizontal_grid(self, size, header=False, bold=False, side=False):
        if side:
            # there should be no bold lines on a side
            # so it's a standard grid cross symbol
            bold_cross_symbol = self.GRID_CROSS_SYMBOL
        else:
            bold_cross_symbol = self.BOLD_LINE_VERTICAL_SIZE * self.GRID_CROSS_SYMBOL

        return bold_cross_symbol.join(
            self.GRID_CROSS_SYMBOL.join(block)
            for block in
            split_seq(
                [self._cell_horizontal_border(header=header, bold=bold)] * size,
                self.BOLD_LINE_EVERY))

    def _grid_row(self, border=False, header=False, data_row_index=None):
        """
        The whole string representing a grid row.
        When `border` is True it's the most upper or lower row.
        When `data_row_index` provided, draw a bold line if it's divisible by 5
        """
        if border:
            if header:
                raise ValueError(
                    'Cannot print a row that separates headers as a border row')
            end = self.CORNER_SYMBOL
        else:
            end = self.VERTICAL_GRID_SYMBOL

        bold = False
        if data_row_index:
            if data_row_index > 0 and (data_row_index % self.BOLD_LINE_EVERY == 0):
                bold = True

        return ''.join([
            end,
            self._horizontal_grid(self.side_width, header=header, bold=bold, side=True),
            self._side_delimiter(grid=True),
            self._horizontal_grid(self.board.width, header=header, bold=bold),
            end,
        ])

    # not a class method to enable live reloading of CELL_WIDTH
    def cell_icon(self, cell):
        ico = super(AsciiRenderer, self).cell_icon(cell)
        max_width = self.CELL_WIDTH
        padded = max_width - len(ico)
        if padded < 0:
            raise ValueError('Cannot fit the value {} into cell width {}'.format(
                ico, max_width))

        # pre-formatted to pad later
        res = '{}%s{}' % ico

        space_padding = ' ' * int(padded / 2)

        # e.g. 3 --> ' 3 '
        # but 13 --> ' 13'
        if padded % 2 == 0:
            return res.format(space_padding, space_padding)

        return res.format(space_padding + ' ', space_padding)

    def _value_row(self, values):
        sep = self.VERTICAL_GRID_SYMBOL
        bold_sep = self.BOLD_LINE_VERTICAL_SIZE * sep

        for i, cell in enumerate(values):
            if i == self.side_width:
                yield self._side_delimiter()
            else:
                # only on a data area, every 5 column
                if i > self.side_width and \
                        (i - self.side_width) % self.BOLD_LINE_EVERY == 0:
                    yield bold_sep
                else:
                    yield sep

            yield self.cell_icon(cell)

        yield sep

    def render(self):
        for i, row in enumerate(self.cells):
            if i == 0:
                grid_row = self._grid_row(border=True)
            elif i == self.header_height:
                grid_row = self._grid_row(header=True)
            else:
                grid_row = self._grid_row(data_row_index=i - self.header_height)
            self._print(grid_row)
            self._print(''.join(self._value_row(row)))

        self._print(self._grid_row(border=True))


class AsciiRendererWithBold(AsciiRenderer):
    """
    AsciiRenderer that also splits the whole board into
    5x5 squares using 'bold' grid lines
    """

    __rend_name__ = 'text-grid-bold'

    SIDE_DELIMITER_SIZE = 3
    BOLD_LINE_HORIZONTAL = AsciiRenderer.HEADER_DELIMITER
    BOLD_LINE_VERTICAL_SIZE = 2


class SvgRenderer(StreamRenderer):
    """
    Draws the board like an SVG image (best representation for web)
    """

    __rend_name__ = 'svg'

    DEFAULT_CELL_SIZE_IN_PIXELS = 15
    BOLD_EVERY = 5

    GRID_STROKE_WIDTH = 1
    GRID_BOLD_STROKE_WIDTH = 2

    @property
    def clues_font_size(self):
        """The size of the descriptions text"""
        return self.cell_size * 0.6

    def __init__(self, board=None, stream=stdout, size=DEFAULT_CELL_SIZE_IN_PIXELS):
        super(SvgRenderer, self).__init__(board, stream)

        # decrease startup time when do not need this renderer
        from svgwrite import Drawing

        self.cell_size = size
        self.color_symbols = dict()
        self.drawing = Drawing(size=(
            self.full_width + self.cell_size,
            self.full_height + self.cell_size))
        self._add_definitions()

    def _color_id_by_name(self, color):
        color_id = self.board.color_id_by_name(color)
        if color_id:
            return color_id

        if is_list_like(color):
            return from_two_powers(
                self.board.color_id_by_name(single_color)
                for single_color in color)

        return None

    def _add_symbol(self, id_, color, *parts, **kwargs):
        drawing = self.drawing
        symbol = drawing.symbol(id_=id_, **kwargs)
        for part in parts:
            symbol.add(part)

        if color is not None:
            # SPACE is already an ID
            if color not in (SPACE, SPACE_COLORED):
                if self.is_colored:
                    color = self._color_id_by_name(color)

            self.color_symbols[color] = id_

        drawing.defs.add(symbol)

    def _add_definitions(self):
        drawing = self.drawing

        # dynamic style rules
        drawing.defs.add(drawing.style(
            'g.grid-lines line {stroke-width: %i} '
            'g.grid-lines line.bold {stroke-width: %i} '
            'g.header-clues text, g.side-clues text {font-size: %f} ' % (
                self.GRID_STROKE_WIDTH,
                self.GRID_BOLD_STROKE_WIDTH,
                self.clues_font_size,
            )
        ))

        self._add_colors_def()

        self._add_symbol(
            'check', None,
            drawing.circle(
                r=40, stroke_width=10, center=(50, 50)
            ),
            drawing.polyline(
                stroke_width=12,
                points=[(35, 35), (35, 55), (75, 55)],
                transform='rotate(-45 50 50)'
            ),
            stroke='green', fill='none'
        )

        self.check_icon_size = 100

    def _add_colors_def(self):
        drawing = self.drawing
        white_color = Color.white().name

        cell_size = self.cell_size
        rect_size = (cell_size, cell_size)

        upper_triangle_points = ((0, 0), (0, cell_size), (cell_size, 0))
        lower_triangle_points = ((0, cell_size), (cell_size, 0), (cell_size, cell_size))

        # three_colored_flag_rect_size = (cell_size / 3, cell_size)
        # three_colored_flag_insert_points = [(0, 0), (cell_size / 3, 0), (2 * cell_size / 3, 0)]
        three_color_triangle_size = round(cell_size * ((1 / 2) ** 0.5), 2)
        three_color_triangle_coord = round(cell_size - three_color_triangle_size, 2)

        three_colors_upper_points = [
            (0, 0), (0, three_color_triangle_size), (three_color_triangle_size, 0)]
        three_colors_lower_points = [
            (cell_size, three_color_triangle_coord),
            (three_color_triangle_coord, cell_size),
            (cell_size, cell_size),
        ]

        # rendering should be predictable
        colors = []
        if self.is_colored:
            for color_name in sorted(self.board.color_map):
                colors.append((color_name, self._color_from_name(color_name)))

            space_color = SPACE_COLORED
        else:
            colors.append((BOX, 'black'))
            space_color = SPACE

        for color_name, fill_color in colors:
            if color_name != white_color:
                self._add_symbol(
                    'color-%s' % color_name, color_name,
                    drawing.rect(
                        size=rect_size,
                        fill=fill_color,
                    ))

        if self.is_colored:
            for (color_name, fill_color), (color_name2, fill_color2) in combinations(colors, 2):
                LOG.info('Transient symbol: %s, %s + %s, %s',
                         color_name, fill_color, color_name2, fill_color2)
                color_tuple = (color_name, color_name2)

                self._add_symbol(
                    'x2-%s' % '-'.join(map(str, color_tuple)), color_tuple,
                    drawing.polygon(
                        points=upper_triangle_points,
                        fill=fill_color,
                    ),
                    drawing.polygon(
                        points=lower_triangle_points,
                        fill=fill_color2,
                    ),
                )

            for (color_name, fill_color), (color_name2, fill_color2), (
                    color_name3, fill_color3) in combinations(colors, 3):
                LOG.info('Transient symbol: %s, %s + %s, %s + %s, %s',
                         color_name, fill_color,
                         color_name2, fill_color2,
                         color_name3, fill_color3)
                color_tuple = (color_name, color_name2, color_name3)

                self._add_symbol(
                    'x3-%s' % '-'.join(map(str, color_tuple)), color_tuple,
                    # drawing.rect(
                    #     insert=three_colored_flag_insert_points[0],
                    #     size=three_colored_flag_rect_size,
                    #     fill=fill_color,
                    # ),
                    # drawing.rect(
                    #     insert=three_colored_flag_insert_points[1],
                    #     size=three_colored_flag_rect_size,
                    #     fill=fill_color2,
                    # ),
                    # drawing.rect(
                    #     insert=three_colored_flag_insert_points[2],
                    #     size=three_colored_flag_rect_size,
                    #     fill=fill_color3,
                    # ),
                    drawing.rect(
                        size=rect_size,
                        fill=fill_color,
                    ),
                    drawing.polygon(
                        points=three_colors_upper_points,
                        fill=fill_color2,
                    ),
                    drawing.polygon(
                        points=three_colors_lower_points,
                        fill=fill_color3,
                    ),
                )

        # it's a little circle
        self._add_symbol(
            'space', space_color,
            drawing.circle(
                r=cell_size / 10
            ))

    @property
    def pixel_side_width(self):
        """Horizontal clues side width in pixels"""
        return self.side_width * self.cell_size

    @property
    def pixel_header_height(self):
        """Vertical clues header height in pixels"""
        return self.header_height * self.cell_size

    @property
    def pixel_board_width(self):
        """The width of the main area in pixels"""
        return self.board.width * self.cell_size

    @property
    def pixel_board_height(self):
        """The height of the main area in pixels"""
        return self.board.height * self.cell_size

    @property
    def full_width(self):
        """Full width of the SVG board representation"""
        return self.pixel_side_width + self.pixel_board_width

    @property
    def full_height(self):
        """Full height of the SVG board representation"""
        return self.pixel_header_height + self.pixel_board_height

    def _color_from_name(self, color_name):
        return self.board.rgb_for_color_name(color_name)

    def block_svg(self, value, is_column, clue_number, block_number):
        """
        Return the SVG element for the clue number (colored case included)
        """
        # left to right, bottom to top
        block_number = -block_number

        shift = (0.85, -0.3) if is_column else (-0.3, 0.75)
        i, j = (clue_number, block_number) if is_column else (block_number, clue_number)

        if isinstance(value, (list, tuple)):
            # colored board
            value, color_id = value[:2]
        else:
            color_id = None

        block_color = None
        if color_id is not None:
            id_ = self.color_symbols[color_id]

            if is_column:
                color_box = (i, j - 1)
            else:
                color_box = (i - 1, j)

            # drawing.g(class_=id_)
            insert_point = (
                self.pixel_side_width + (color_box[0] * self.cell_size),
                self.pixel_header_height + (color_box[1] * self.cell_size))

            block_color = (id_, insert_point)

        extra = dict()
        if color_id == Color.black().id_:
            extra['fill'] = 'white'

        if value == BlottedBlock:
            text_value = ClueCell.BLOTTED_SYMBOL
        else:
            text_value = str(value)

        block_text = self.drawing.text(
            text_value,
            insert=(
                self.pixel_side_width + (i + shift[0]) * self.cell_size,
                self.pixel_header_height + (j + shift[1]) * self.cell_size,
            ),
            **extra
        )

        return block_color, block_text

    def draw_header(self):
        drawing = self.drawing

        drawing.add(drawing.rect(
            size=(self.pixel_side_width, self.pixel_header_height),
            class_='nonogram-thumbnail'))
        drawing.add(drawing.rect(
            insert=(self.pixel_side_width, 0),
            size=(self.pixel_board_width, self.pixel_header_height),
            class_='nonogram-header'))

        header_group = drawing.g(class_='header-clues')
        for i, col_desc in enumerate(self.board.columns_descriptions):
            if self.board.column_solution_rate(i) == 1:
                x_pos = self.pixel_side_width + (i * self.cell_size)
                header_group.add(drawing.rect(
                    insert=(x_pos, 0),
                    size=(self.cell_size, self.pixel_header_height),
                    class_='solved'
                ))

            for j, desc_item in enumerate(reversed(col_desc)):
                color, text = self.block_svg(desc_item, True, i, j)

                # color first, text next (to write on color)
                if color:
                    id_, insert_point = color
                    icon = drawing.use(
                        href='#' + id_,
                        insert=insert_point,
                    )

                    header_group.add(icon)

                header_group.add(text)

        drawing.add(header_group)

    def draw_side(self):
        drawing = self.drawing

        drawing.add(drawing.rect(
            insert=(0, self.pixel_header_height),
            size=(self.pixel_side_width, self.pixel_board_height),
            class_='nonogram-side'))

        side_group = drawing.g(class_='side-clues')
        for j, row_desc in enumerate(self.board.rows_descriptions):
            if self.board.row_solution_rate(j) == 1:
                y_pos = self.pixel_header_height + (j * self.cell_size)
                side_group.add(drawing.rect(
                    insert=(0, y_pos),
                    size=(self.pixel_side_width, self.cell_size),
                    class_='solved'
                ))

            for i, desc_item in enumerate(reversed(row_desc)):
                color, text = self.block_svg(desc_item, False, j, i)

                # color first, text next (to write on color)
                if color:
                    id_, insert_point = color
                    icon = drawing.use(
                        href='#' + id_,
                        insert=insert_point,
                    )

                    side_group.add(icon)

                side_group.add(text)

        drawing.add(side_group)

        if self.board.is_solved_full:
            self._insert_solved_symbol()

    def _insert_solved_symbol(self):
        drawing = self.drawing

        check_icon_size = self.check_icon_size
        left_padding = (self.pixel_side_width - check_icon_size) / 2
        top_padding = (self.pixel_header_height - check_icon_size) / 2
        left_padding = max(left_padding, 0)
        top_padding = max(top_padding, 0)

        drawing.add(drawing.use('#check', insert=(
            left_padding, top_padding
        )))

    @classmethod
    def _color_code(cls, cell):
        if is_color_cell(cell):
            single_colors = two_powers(cell)
            if len(single_colors) > 3:  # allow two and three colors
                # multiple colors
                return UNKNOWN

        return cell

    def draw_grid(self, cells=None):
        if cells is None:
            cells = self.board.cells

        drawing = self.drawing

        drawing.add(drawing.rect(
            insert=(self.pixel_side_width, self.pixel_header_height),
            size=(self.pixel_board_width, self.pixel_board_height),
            class_='nonogram-grid'))

        cell_groups = dict()
        for cell_value, id_ in iteritems(self.color_symbols):
            cell_groups[cell_value] = drawing.g(class_=id_)

        space_cell = SPACE_COLORED if self.is_colored else SPACE

        for j, row in enumerate(cells):
            for i, cell in enumerate(row):
                cell = self._color_code(cell)

                if cell == UNKNOWN:
                    continue

                if cell == space_cell:
                    insert_point = (
                        self.pixel_side_width + (i + 0.5) * self.cell_size,
                        self.pixel_header_height + (j + 0.5) * self.cell_size)
                else:
                    # for boxes colored and black
                    insert_point = (
                        self.pixel_side_width + (i * self.cell_size),
                        self.pixel_header_height + (j * self.cell_size))

                id_ = self.color_symbols[cell]
                icon = drawing.use(
                    href='#' + id_,
                    insert=insert_point)
                cell_groups[cell].add(icon)

        # to get predictable order
        for cell_value, group in sorted(iteritems(cell_groups),
                                        key=lambda x: x[0]):
            drawing.add(group)

        # write grid on top of the colors
        self._insert_grid_lines()

    def _insert_grid_lines(self):
        drawing = self.drawing

        grid_lines = drawing.g(class_='grid-lines')
        for line in self._get_grid_lines():
            grid_lines.add(line)

        drawing.add(grid_lines)

    def _get_grid_lines(self):
        drawing = self.drawing

        # draw horizontal lines
        for i in range(self.board.height + 1):
            extra = dict()

            if i % self.BOLD_EVERY == 0 or i == self.board.height:
                extra['class'] = 'bold'

            y_pos = self.pixel_header_height + (i * self.cell_size)
            yield drawing.line(
                start=(0, y_pos),
                end=(self.full_width, y_pos),
                **extra)

        # draw vertical lines
        for i in range(self.board.width + 1):
            extra = dict()

            if i % self.BOLD_EVERY == 0 or i == self.board.width:
                extra['class'] = 'bold'

            x_pos = self.pixel_side_width + (i * self.cell_size)
            yield drawing.line(
                start=(x_pos, 0),
                end=(x_pos, self.full_height),
                **extra)

    def render(self):
        self.drawing.write(self.stream)
        # self._print(self.drawing.tostring())

    def draw(self, cells=None):
        self.drawing.elements = []
        self.drawing.add(self.drawing.defs)

        super(SvgRenderer, self).draw(cells=cells)


def _register_renderers():
    res = dict()
    for obj in itervalues(globals()):
        if isinstance(obj, type):
            if issubclass(obj, StreamRenderer) and hasattr(obj, '__rend_name__'):
                res[obj.__rend_name__] = obj
    return res


RENDERERS = _register_renderers()
