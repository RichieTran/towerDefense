"""
Grid / Map System
=================

Represents the play field as a 2D grid of cells, each with a terrain type.
Towers can only be placed on BUILDABLE cells. PATH cells define where
enemies walk (and can be used to auto-generate Tracks).

How it fits in the engine:
    - ``GameState.place_tower()`` checks ``grid.is_buildable(x, y)`` before
      allowing placement.
    - The grid can be initialized from a 2D list of terrain values, a file,
      or procedurally generated.
    - Rendering layers use the grid to draw terrain sprites.

Example::

    grid = Grid(rows=10, cols=15)
    grid.set_cell(3, 5, TerrainType.BUILDABLE)
    if grid.is_buildable(3, 5):
        grid.place_tower(3, 5)
"""

from __future__ import annotations

from enum import Enum, auto
from typing import List, Optional, Tuple


class TerrainType(Enum):
    """Terrain types for each grid cell.

    EMPTY:     Default; cannot build, enemies don't walk here.
    PATH:      Enemy walking route. Cannot build.
    BUILDABLE: Towers can be placed here.
    BLOCKED:   Impassable; cannot build or walk.
    """

    EMPTY = auto()
    PATH = auto()
    BUILDABLE = auto()
    BLOCKED = auto()


class Grid:
    """A 2D grid representing the game map.

    Example::

        grid = Grid(rows=10, cols=15)
        grid.set_cell(0, 0, TerrainType.BUILDABLE)
        grid.place_tower(0, 0)
        neighbors = grid.get_neighbors(5, 5)

    Attributes:
        rows:   Number of rows.
        cols:   Number of columns.
        _cells: 2D list of TerrainType values.
        _tower_positions: Set of (row, col) tuples where towers are placed.
    """

    def __init__(self, rows: int = 10, cols: int = 10) -> None:
        self.rows = rows
        self.cols = cols
        self._cells: List[List[TerrainType]] = [
            [TerrainType.EMPTY for _ in range(cols)] for _ in range(rows)
        ]
        self._tower_positions: set[Tuple[int, int]] = set()

    def get_cell(self, row: int, col: int) -> TerrainType:
        """Get the terrain type at a grid position.

        Args:
            row: Row index (0-based).
            col: Column index (0-based).

        Returns:
            The TerrainType of the cell.

        Raises:
            IndexError: If (row, col) is out of bounds.
        """
        self._check_bounds(row, col)
        return self._cells[row][col]

    def set_cell(self, row: int, col: int, terrain: TerrainType) -> None:
        """Set the terrain type at a grid position.

        Args:
            row:     Row index.
            col:     Column index.
            terrain: The TerrainType to assign.

        Raises:
            IndexError: If (row, col) is out of bounds.
        """
        self._check_bounds(row, col)
        self._cells[row][col] = terrain

    def is_buildable(self, row: int, col: int) -> bool:
        """Check if a tower can be placed at this cell.

        A cell is buildable if its terrain is BUILDABLE and no tower
        is already there.

        Args:
            row: Row index.
            col: Column index.

        Returns:
            True if a tower can be placed here.
        """
        if not self._in_bounds(row, col):
            return False
        if (row, col) in self._tower_positions:
            return False
        return self._cells[row][col] == TerrainType.BUILDABLE

    def place_tower(self, row: int, col: int) -> bool:
        """Mark a cell as occupied by a tower.

        Args:
            row: Row index.
            col: Column index.

        Returns:
            True if the tower was placed, False if not buildable.

        Side effects:
            Adds (row, col) to ``_tower_positions``.
        """
        if not self.is_buildable(row, col):
            return False
        self._tower_positions.add((row, col))
        return True

    def remove_tower(self, row: int, col: int) -> bool:
        """Remove a tower from a cell.

        Args:
            row: Row index.
            col: Column index.

        Returns:
            True if a tower was removed, False if no tower was there.

        Side effects:
            Removes (row, col) from ``_tower_positions``.
        """
        if (row, col) in self._tower_positions:
            self._tower_positions.discard((row, col))
            return True
        return False

    def get_neighbors(self, row: int, col: int) -> List[Tuple[int, int]]:
        """Get the 4-directional neighbors of a cell (up, down, left, right).

        Args:
            row: Row index.
            col: Column index.

        Returns:
            List of (row, col) tuples for valid neighboring cells.
        """
        neighbors = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = row + dr, col + dc
            if self._in_bounds(nr, nc):
                neighbors.append((nr, nc))
        return neighbors

    def load_from_2d_list(self, data: List[List[int]]) -> None:
        """Initialize the grid from a 2D list of integer terrain values.

        Mapping: 0=EMPTY, 1=PATH, 2=BUILDABLE, 3=BLOCKED.

        Args:
            data: 2D list where each element is an int (0-3).

        Side effects:
            Overwrites all cell terrain types. Resizes rows/cols to match data.

        TODO: Support loading from a file (JSON, plain text, Tiled TMX, etc.)
        """
        mapping = {
            0: TerrainType.EMPTY,
            1: TerrainType.PATH,
            2: TerrainType.BUILDABLE,
            3: TerrainType.BLOCKED,
        }
        self.rows = len(data)
        self.cols = len(data[0]) if data else 0
        self._cells = [
            [mapping.get(val, TerrainType.EMPTY) for val in row] for row in data
        ]
        self._tower_positions.clear()

    def __repr__(self) -> str:
        """Debug-friendly string showing the grid with single-char terrain codes."""
        symbols = {
            TerrainType.EMPTY: ".",
            TerrainType.PATH: "#",
            TerrainType.BUILDABLE: "B",
            TerrainType.BLOCKED: "X",
        }
        lines = []
        for r in range(self.rows):
            row_str = ""
            for c in range(self.cols):
                if (r, c) in self._tower_positions:
                    row_str += "T"
                else:
                    row_str += symbols.get(self._cells[r][c], "?")
            lines.append(row_str)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.rows and 0 <= col < self.cols

    def _check_bounds(self, row: int, col: int) -> None:
        if not self._in_bounds(row, col):
            raise IndexError(f"Cell ({row}, {col}) out of bounds for {self.rows}x{self.cols} grid.")
