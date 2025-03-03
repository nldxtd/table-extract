#!/usr/bin/env python3
# encoding: utf-8
"""Classes used for representing Tables, TableRows and TableCells."""

from itertools import chain
from typing import List

from html_properties import HorizontalAlignment, VerticalAlignment
from canvas import Canvas


class TableCell(Canvas):
    """A table cell.

    Attributes:
        line_width: the original line widths per line (required to adjust
                    annotations after a reformatting)
        vertical_padding: vertical padding that has been introduced due to
                          vertical formatting rules.
    """

    __slots__ = (
        "blocks",
        "current_block",
        "margin",
        "align",
        "valign",
        "_width",
        "line_width",
        "vertical_padding",
    )

    def __init__(self, align: HorizontalAlignment, valign: VerticalAlignment):
        super().__init__()
        self.align = align
        self.valign = valign
        self._width = None
        self.line_width = None
        self.vertical_padding = 0

    def normalize_blocks(self) -> int:
        """Split multi-line blocks into multiple one-line blocks.

        Returns:
            The height of the normalized cell.
        """
        self.flush_inline()
        self.blocks = list(chain(*(line.split("\n") for line in self.blocks)))
        if not self.blocks:
            self.blocks = [""]
        return len(self.blocks)

    @property
    def height(self) -> int:
        """Compute the table cell's height.

        Returns:
            The cell's current height.
        """
        return max(1, len(self.blocks))

    @property
    def width(self) -> int:
        """Compute the table cell's width.

        Returns:
            The cell's current width.
        """
        if self._width:
            return self._width
        return max(
            (len(line) for line in chain(*(block.split("\n") for block in self.blocks)))
        )

    @width.setter
    def width(self, width):
        """Set the table's width and applies the cell's horizontal formatting.

        Args:
            The cell's expected width.
        """
        # save the original line widths before reformatting
        self.line_width = [len(block) for block in self.blocks]

        # record new width and start reformatting
        self._width = width
        format_spec = "{{:{align}{width}}}".format(align=self.align.value, width=width)
        self.blocks = [format_spec.format(b) for b in self.blocks]

    @height.setter
    def height(self, height: int):
        """Set the cell's height to the given value.

        Notes:
            Depending on the height and the cell's vertical formatting this
            might require the introduction of empty lines.
        """
        rows = len(self.blocks)
        if rows < height:
            empty_line = [""]
            if self.valign == VerticalAlignment.bottom:
                self.vertical_padding = height - rows
                self.blocks = self.vertical_padding * empty_line + self.blocks
            elif self.valign == VerticalAlignment.middle:
                self.vertical_padding = (height - rows) // 2
                self.blocks = (
                    self.vertical_padding * empty_line
                    + self.blocks
                    + ((height - rows + 1) // 2 * empty_line)
                )
            else:
                self.blocks = self.blocks + ((height - rows) * empty_line)
        

class TableRow:
    """A single row within a table.

    Attributes:
        columns: the table row's columns.
        cell_separator: string used for separating columns from each other.
    """

    __slots__ = ("columns", "cell_separator")

    def __init__(self, cell_separator: str):
        self.columns: List[TableCell] = []
        self.cell_separator = cell_separator

    def __len__(self):
        return len(self.columns)

    def get_text(self) -> str:
        """Return a text representation of the TableRow."""
        row_lines = [
            self.cell_separator.join(line)
            for line in zip(*[column.blocks for column in self.columns])
        ]
        return "\n".join(row_lines)

    @property
    def width(self) -> int:
        """Compute and return the width of the current row."""
        if not self.columns:
            return 0

        return sum((cell.width for cell in self.columns)) + len(self.cell_separator) * (
            len(self.columns) - 1
        )


class Table:
    """An HTML table.

    Attributes:
        rows: the table's rows.
        left_margin_len: length of the left margin before the table.
        cell_separator: string used for separating cells from each other.
    """

    __slots__ = ("rows", "left_margin_len", "cell_separator")

    def __init__(self, left_margin_len: int, cell_separator: str):
        self.rows = []
        self.left_margin_len = left_margin_len
        self.cell_separator = cell_separator

    def add_row(self):
        """Add an empty :class:`TableRow` to the table."""
        self.rows.append(TableRow(self.cell_separator))

    def add_cell(self, table_cell: TableCell):
        """Add  a new :class:`TableCell` to the table's last row.

        .. note::
            If no row exists yet, a new row is created.
        """
        if not self.rows:
            self.add_row()
        self.rows[-1].columns.append(table_cell)

    def _set_row_height(self):
        """Set the cell height for all :class:`TableCell`s in the table."""
        for row in self.rows:
            max_row_height = (
                max((cell.normalize_blocks() for cell in row.columns))
                if row.columns
                else 0
            )
            for cell in row.columns:
                cell.height = max_row_height

    def _set_column_width(self):
        """Set the column width for all :class:`TableCell`s in the table."""
        # determine maximum number of columns
        max_columns = max((len(row.columns) for row in self.rows))

        for cur_column_idx in range(max_columns):
            # determine the required column width for the current column
            max_column_width = max(
                (
                    row.columns[cur_column_idx].width
                    for row in self.rows
                    if len(row) > cur_column_idx
                )
            )

            # set column width for all TableCells in the current column
            for row in self.rows:
                if len(row) > cur_column_idx:
                    row.columns[cur_column_idx].width = max_column_width

    def get_text(self) -> str:
        """Return and render the text of the given table."""
        if not self.rows:
            return "\n"

        self._set_row_height()
        self._set_column_width()
        return "\n".join((row.get_text() for row in self.rows)) + "\n"
