"""
Tower Defense Engine — Demo Entry Point
========================================

Demonstrates how to load a level and run a simulated game loop.
Levels are self-contained modules in the ``levels/`` package — each one
exposes a ``create()`` function that returns a ready-to-play GameState.

Run::

    python gui.py
"""

from engine.events import EventBus, EventType
from engine.towers import ArrowTower, CannonTower, FrostTower, AntiAirTower
from levels import forest_clearing


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
    """Load the Forest Clearing level and run a simulated game loop."""
    # --- Load level ---
    state, event_bus = forest_clearing.create()
    setup_event_logging(event_bus)

    print("=== Tower Defense Engine Demo ===")
    print(f"Level: Forest Clearing ({state.grid.rows}x{state.grid.cols})\n")
    print("Map:")
    print(state.grid)
    print(f"\nTrack: {len(state.track.waypoints)} waypoints, "
          f"length={state.track.total_length():.1f}")
    print(f"Lives: {state.lives}  Gold: {state.gold}  "
          f"Waves: {len(state.wave_manager.waves)}\n")

    # --- Place some towers ---
    print("--- Placing towers ---")
    state.place_tower(ArrowTower(), (0, 3))   # clearing near spawn
    state.place_tower(CannonTower(), (2, 1))  # overlooks the east bend
    state.place_tower(FrostTower(), (4, 8))   # slows enemies on the long straight
    state.place_tower(AntiAirTower(), (6, 6)) # covers the final stretch for flyers
    print(f"Gold remaining: {state.gold}\n")

    print("Map with towers:")
    print(state.grid)
    print()

    # --- Simulate all waves ---
    # TODO: Replace this with a real-time loop driven by a clock/renderer.
    #       This loop uses fixed dt for demonstration purposes.

    DT = 0.1  # 100ms per simulated tick
    MAX_TICKS = 3000  # safety cap

    total_waves = len(state.wave_manager.waves)
    for wave_num in range(1, total_waves + 1):
        if not state.start_wave():
            print("No more waves!")
            break

        tick = 0
        while tick < MAX_TICKS and not state.game_over:
            state.update(DT)
            tick += 1

            if state.is_wave_complete():
                break

        print(f"  Wave {wave_num}/{total_waves} done — Lives: {state.lives}, "
              f"Gold: {state.gold}, Score: {state.score}, "
              f"Ticks: {tick}\n")

        if state.game_over:
            break

    if not state.game_over:
        print("=== All waves survived! ===")
    print(f"Final — Lives: {state.lives}, Gold: {state.gold}, Score: {state.score}")


if __name__ == "__main__":
    main()
