# Tower Defense Engine

A modular, extensible tower defense game engine written in pure Python (standard library only). This is a **framework**, not a playable game — it provides the core systems that a developer can build on to create a complete tower defense game with their choice of rendering, audio, and UI.

## Architecture

```
main.py                  ← Demo entry point: wires systems together, runs a simulated loop
engine/
├── __init__.py          ← Package exports
├── game_state.py        ← Central orchestrator: owns all state, drives the update loop
├── track.py             ← Waypoint paths that enemies follow
├── enemies.py           ← Enemy base class + template subclasses (Grunt, Runner, Tank, etc.)
├── towers.py            ← Tower base class + templates (Arrow, Cannon, Frost, Mage, AntiAir)
├── waves.py             ← Wave definitions and spawn scheduling
├── projectiles.py       ← In-flight projectile movement and damage application
├── effects.py           ← Status effects (slow, burn, armor reduction)
├── events.py            ← Pub/sub event bus for decoupled communication
└── grid.py              ← 2D grid map with terrain types
```

## How the Systems Connect

```
┌──────────────┐     spawns      ┌──────────────┐     move along     ┌──────────────┐
│  WaveManager │ ──────────────→ │   Enemies     │ ──────────────→   │    Track      │
└──────────────┘                 └──────┬───────┘                    └──────────────┘
                                        │ targeted by
                                        ▼
┌──────────────┐     fires       ┌──────────────┐     creates       ┌──────────────┐
│    Towers    │ ──────────────→ │  Projectiles  │ ──────────────→  │   Damage      │
└──────┬───────┘                 └──────────────┘                    └──────────────┘
       │ placed on                                                          │
       ▼                                                                    ▼
┌──────────────┐                                                    ┌──────────────┐
│     Grid     │                                                    │   Effects     │
└──────────────┘                                                    └──────────────┘

                         ┌──────────────┐
         All systems ──→ │   EventBus   │ ──→ UI, Audio, Analytics (your code)
                         └──────────────┘
```

**GameState** is the central orchestrator. Each frame, `GameState.update(dt)`:
1. Spawns enemies from the current wave
2. Moves all enemies along their tracks
3. Towers select targets and fire projectiles
4. Projectiles move and apply damage on arrival
5. Dead enemies grant gold; leaked enemies cost lives
6. Checks for wave completion and game over

The **EventBus** decouples systems — towers don't need to know about the UI, and the score system doesn't need to know about rendering. Subscribe to events like `ENEMY_KILLED` or `WAVE_COMPLETE` to hook in your own logic.

## Getting Started

### Prerequisites

- Python 3.10+ (uses `match` syntax, `X | Y` union types, dataclasses)
- No external dependencies

### Run the Demo

```bash
python main.py
```

This runs a simulated game with 3 waves, 4 towers, and text output showing events. No rendering — just proof that the systems work together.

### Build a Game From This Framework

1. **Add rendering**: Implement a render loop (pygame, pyglet, curses, or even a web frontend). Read `GameState` each frame to draw enemies, towers, and projectiles at their positions.

2. **Add input handling**: Call `GameState.place_tower()`, `sell_tower()`, and `start_wave()` in response to player input.

3. **Add a real game loop**: Replace the simulated `DT` loop in `main.py` with a proper frame-rate-driven loop using your rendering library's clock.

4. **Balance the game**: Adjust stats in the enemy/tower subclasses. The template classes (`Grunt`, `ArrowTower`, etc.) are starting points — tweak `health`, `speed`, `damage`, `cost`, etc.

5. **Extend the systems**:
   - Add new enemy types by subclassing `Enemy`
   - Add new towers by subclassing `Tower`
   - Add new effects by subclassing `StatusEffect`
   - Add new event types to the `EventType` enum
   - Create new targeting strategies in the `TargetingStrategy` enum

6. **Hook into events**: Subscribe to the `EventBus` for sound effects, particle systems, score popups, achievements, etc.

### Key Extension Points (marked with TODO in code)

- **Rendering**: Every entity has a position — add sprite references and draw them
- **Audio**: Events like `ENEMY_KILLED`, `TOWER_PLACED` are natural SFX trigger points
- **AI/Pathfinding**: Enemies currently follow fixed tracks; add A* for dynamic routing
- **Save/Load**: Serialize `GameState` to JSON for save games
- **Modding**: The event bus and class-based design make it straightforward to add plugin support
- **Multiplayer**: GameState is deterministic given the same inputs — suitable for lockstep networking

## Module Reference

| Module | Key Classes | Purpose |
|--------|------------|---------|
| `track.py` | `Waypoint`, `Track`, `TrackManager` | Define and interpolate enemy movement paths |
| `enemies.py` | `Enemy`, `Grunt`, `Runner`, `Tank`, `Boss`, `FlyingEnemy` | Enemy entities with health, armor, speed |
| `towers.py` | `Tower`, `ArrowTower`, `CannonTower`, `FrostTower`, `MageTower`, `AntiAirTower` | Player defenses with targeting and firing |
| `waves.py` | `WaveEntry`, `Wave`, `WaveManager` | Spawn scheduling and wave progression |
| `projectiles.py` | `Projectile`, `ProjectileManager` | In-flight damage delivery |
| `effects.py` | `StatusEffect`, `SlowEffect`, `BurnEffect`, `ArmorReductionEffect`, `EffectManager` | Temporary stat modifiers on enemies |
| `events.py` | `EventType`, `EventBus` | Decoupled publish/subscribe messaging |
| `grid.py` | `TerrainType`, `Grid` | Map representation and buildability checks |
| `game_state.py` | `GameState` | Central state + update loop |
