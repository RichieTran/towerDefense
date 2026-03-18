"""
Level: Forest Clearing
======================

A small 8x10 beginner-friendly map with a single winding path through a
forest. Enemies enter from the top-left and exit at the bottom-right.
Plenty of buildable clearings along the path for tower placement.

Layout sketch::

    S = spawn (BLOCKED, marks entry)
    E = exit  (BLOCKED, marks base)
    # = path
    B = buildable clearing
    X = blocked (dense trees)
    . = empty (forest, non-buildable)

    S # # B . . . . . .
    . . X # . . . B . .
    . B . # # # . . . .
    . . . B . # . . . .
    . . . . . # # # B .
    . . . . B . . # . .
    . . . . . . B # # E
    . . . . . . . . . .

How to use this level::

    from levels import forest_clearing

    state, event_bus = forest_clearing.create()

    # Place towers
    state.place_tower(ArrowTower(), (0, 3))   # buildable cell at row 0, col 3
    state.place_tower(CannonTower(), (2, 1))  # buildable cell at row 2, col 1

    # Start first wave
    state.start_wave()

    # Game loop
    while not state.game_over:
        state.update(1 / 60)
"""

from engine.enemies import Boss, FlyingEnemy, Grunt, Runner, Tank
from engine.events import EventBus
from engine.game_state import GameState
from engine.grid import Grid
from engine.track import Track, Waypoint
from engine.waves import Wave, WaveEntry, WaveManager


# ---------------------------------------------------------------------------
# Map definition
# ---------------------------------------------------------------------------

# Grid legend: 0=EMPTY, 1=PATH, 2=BUILDABLE, 3=BLOCKED
LAYOUT = [
    [3, 1, 1, 2, 0, 0, 0, 0, 0, 0],  # row 0: spawn → path → buildable clearing
    [0, 0, 3, 1, 0, 0, 0, 2, 0, 0],  # row 1: blocked trees force a turn
    [0, 2, 0, 1, 1, 1, 0, 0, 0, 0],  # row 2: path bends east, clearing to the left
    [0, 0, 0, 2, 0, 1, 0, 0, 0, 0],  # row 3: clearing next to a straight
    [0, 0, 0, 0, 0, 1, 1, 1, 2, 0],  # row 4: path continues east, clearing ahead
    [0, 0, 0, 0, 2, 0, 0, 1, 0, 0],  # row 5: clearing with line of sight
    [0, 0, 0, 0, 0, 0, 2, 1, 1, 3],  # row 6: final stretch to exit
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # row 7: empty buffer row
]

ROWS = len(LAYOUT)
COLS = len(LAYOUT[0])

# Ordered (row, col) pairs tracing the path from spawn to exit.
# These become Waypoints — enemies interpolate between them.
PATH_COORDS = [
    (0, 0),  # spawn point
    (0, 1), (0, 2),
    (1, 3),  # turn south
    (2, 3), (2, 4), (2, 5),  # east
    (3, 5),  # south
    (4, 5), (4, 6), (4, 7),  # east
    (5, 7),  # south
    (6, 7), (6, 8), (6, 9),  # east to exit
]

# Starting resources
STARTING_LIVES = 15
STARTING_GOLD = 200


# ---------------------------------------------------------------------------
# Wave definitions
# ---------------------------------------------------------------------------

def _build_waves() -> WaveManager:
    """Define the enemy waves for this level.

    Wave 1: Gentle intro — a handful of Grunts.
    Wave 2: Mixed — Grunts then Runners to test fire rate.
    Wave 3: Armor check — a Tank supported by Grunts.
    Wave 4: Air raid — Flying enemies force anti-air placement.
    Wave 5: Boss wave — one Boss with Runner escorts.
    """
    waves = [
        # Wave 1 — warm-up
        Wave(entries=[
            WaveEntry(enemy_type=Grunt, count=6, spawn_interval=0.8),
        ]),

        # Wave 2 — speed test
        Wave(entries=[
            WaveEntry(enemy_type=Grunt, count=4, spawn_interval=0.6),
            WaveEntry(enemy_type=Runner, count=5, spawn_interval=0.4),
        ]),

        # Wave 3 — armor check
        Wave(entries=[
            WaveEntry(enemy_type=Grunt, count=3, spawn_interval=0.5),
            WaveEntry(enemy_type=Tank, count=2, spawn_interval=1.5),
            WaveEntry(enemy_type=Grunt, count=4, spawn_interval=0.5),
        ]),

        # Wave 4 — air raid
        Wave(entries=[
            WaveEntry(enemy_type=FlyingEnemy, count=5, spawn_interval=0.6),
            WaveEntry(enemy_type=Runner, count=3, spawn_interval=0.3),
        ]),

        # Wave 5 — boss
        Wave(entries=[
            WaveEntry(enemy_type=Runner, count=4, spawn_interval=0.3),
            WaveEntry(enemy_type=Boss, count=1, spawn_interval=0.0),
            WaveEntry(enemy_type=Runner, count=4, spawn_interval=0.3),
        ]),
    ]
    return WaveManager(waves=waves)


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------

def create() -> tuple[GameState, EventBus]:
    """Create a fully configured GameState for the Forest Clearing level.

    Returns:
        (game_state, event_bus) — ready for tower placement and play.

    Example::

        state, bus = create()
        bus.subscribe(EventType.ENEMY_KILLED, my_on_kill_handler)
        state.place_tower(ArrowTower(), (0, 3))
        state.start_wave()
        state.update(dt)
    """
    # Grid
    grid = Grid(rows=ROWS, cols=COLS)
    grid.load_from_2d_list(LAYOUT)

    # Track
    track = Track(name="forest_path")
    for row, col in PATH_COORDS:
        track.add_waypoint(Waypoint(x=float(col), y=float(row)))

    # Waves
    wave_manager = _build_waves()

    # Event bus
    event_bus = EventBus()

    # Assemble
    state = GameState(
        grid=grid,
        track=track,
        wave_manager=wave_manager,
        event_bus=event_bus,
        lives=STARTING_LIVES,
        gold=STARTING_GOLD,
    )

    return state, event_bus
