"""
Tower Defense Engine — Demo Entry Point
========================================

Demonstrates how to wire together all engine subsystems into a runnable
game loop skeleton. No rendering or real-time input — just instantiation,
a few simulated frames, and event logging to prove the systems work.

Run::

    python main.py
"""

from engine.track import Track, Waypoint
from engine.grid import Grid, TerrainType
from engine.enemies import Grunt, Runner, Tank, FlyingEnemy
from engine.towers import ArrowTower, CannonTower, FrostTower, MageTower, AntiAirTower
from engine.waves import Wave, WaveEntry, WaveManager
from engine.events import EventBus, EventType
from engine.game_state import GameState


def build_map() -> tuple[Grid, Track]:
    """Create a sample grid and track.

    Returns:
        (grid, track) — a 10x15 grid with a winding path and buildable cells,
        and a Track following that path.
    """
    # Legend: 0=empty, 1=path, 2=buildable, 3=blocked
    layout = [
        [3, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 0, 2, 0, 2, 0, 0, 0, 0, 0, 0, 0],
        [0, 2, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 2, 0, 1, 0, 2, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 2, 0, 0, 0, 2, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 3],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ]

    grid = Grid(rows=10, cols=15)
    grid.load_from_2d_list(layout)

    # Build a track that follows the PATH cells
    track = Track(name="main")
    path_coords = [
        (0, 1), (0, 2), (0, 3),
        (1, 3),
        (2, 3), (2, 4), (2, 5), (2, 6), (2, 7),
        (3, 7),
        (4, 7), (4, 8), (4, 9), (4, 10),
        (5, 10),
        (6, 10), (6, 11), (6, 12),
        (7, 12),
        (8, 12), (8, 13),
    ]
    for row, col in path_coords:
        track.add_waypoint(Waypoint(x=float(col), y=float(row)))

    return grid, track


def build_waves() -> WaveManager:
    """Define a few sample waves.

    Returns:
        A WaveManager preloaded with 3 waves.
    """
    wave1 = Wave(entries=[
        WaveEntry(enemy_type=Grunt, count=8, spawn_interval=0.6),
    ])
    wave2 = Wave(entries=[
        WaveEntry(enemy_type=Grunt, count=5, spawn_interval=0.5),
        WaveEntry(enemy_type=Runner, count=4, spawn_interval=0.3),
    ])
    wave3 = Wave(entries=[
        WaveEntry(enemy_type=Tank, count=2, spawn_interval=1.0),
        WaveEntry(enemy_type=Grunt, count=6, spawn_interval=0.4),
        WaveEntry(enemy_type=FlyingEnemy, count=3, spawn_interval=0.5),
    ])

    return WaveManager(waves=[wave1, wave2, wave3])


def setup_event_logging(bus: EventBus) -> None:
    """Subscribe to all events and print them for debugging.

    Args:
        bus: The EventBus to subscribe to.
    """
    bus.subscribe(EventType.WAVE_START, lambda d: print(f"[EVENT] Wave {d['wave_number']} started"))
    bus.subscribe(EventType.WAVE_COMPLETE, lambda d: print(f"[EVENT] Wave {d['wave_number']} complete!"))
    bus.subscribe(EventType.ENEMY_KILLED, lambda d: print(f"[EVENT] Enemy killed! +{d['reward']}g"))
    bus.subscribe(EventType.ENEMY_REACHED_END, lambda d: print(f"[EVENT] Enemy leaked! -{d['lives_lost']} life"))
    bus.subscribe(EventType.TOWER_PLACED, lambda d: print(f"[EVENT] {d['tower'].name} placed at {d['position']}"))
    bus.subscribe(EventType.TOWER_SOLD, lambda d: print(f"[EVENT] {d['tower'].name} sold for {d['refund']}g"))
    bus.subscribe(EventType.GAME_OVER, lambda d: print(f"[EVENT] GAME OVER — score: {d['score']}"))


def main() -> None:
    """Wire everything together and run a simulated game loop."""
    # --- Setup ---
    grid, track = build_map()
    wave_manager = build_waves()
    event_bus = EventBus()

    state = GameState(
        grid=grid,
        track=track,
        wave_manager=wave_manager,
        event_bus=event_bus,
        lives=20,
        gold=300,
    )

    setup_event_logging(event_bus)

    print("=== Tower Defense Engine Demo ===\n")
    print("Map:")
    print(grid)
    print(f"\nTrack '{track.name}': {len(track.waypoints)} waypoints, "
          f"length={track.total_length():.1f}\n")

    # --- Place some towers ---
    print("--- Placing towers ---")
    state.place_tower(ArrowTower(), (1, 5))
    state.place_tower(CannonTower(), (3, 9))
    state.place_tower(FrostTower(), (5, 9))
    state.place_tower(AntiAirTower(), (7, 11))
    print(f"Gold remaining: {state.gold}\n")

    print("Map with towers:")
    print(grid)
    print()

    # --- Simulate a few waves ---
    # TODO: Replace this with a real-time loop driven by a clock/renderer.
    #       This loop uses fixed dt for demonstration purposes.

    DT = 0.1  # 100ms per simulated tick
    MAX_TICKS = 2000  # safety cap

    for wave_num in range(1, 4):
        if not state.start_wave():
            print("No more waves!")
            break

        tick = 0
        while tick < MAX_TICKS and not state.game_over:
            state.update(DT)
            tick += 1

            if state.is_wave_complete():
                break

        print(f"  Wave {wave_num} done — Lives: {state.lives}, "
              f"Gold: {state.gold}, Score: {state.score}, "
              f"Ticks: {tick}\n")

        if state.game_over:
            break

    if not state.game_over:
        print("=== All waves survived! ===")
    print(f"Final — Lives: {state.lives}, Gold: {state.gold}, Score: {state.score}")


if __name__ == "__main__":
    main()
