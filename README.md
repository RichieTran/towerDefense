# Tower Defense

A tower defense game built in pure Python (standard library only — no pygame, no external deps). Includes a working tkinter GUI where you can place towers, send waves, and defend your base.

## How to Run

```bash
# Play the game (graphical window)
python gui.py

# Run the headless simulation (terminal output only)
python main.py
```

Requires **Python 3.10+** and a working tkinter installation (ships with Python on most systems).

## Gameplay

Enemies spawn at the top-left and follow a fixed path to the exit at the bottom-right. You place towers on buildable cells (green, dashed border) to destroy them before they reach your base.

- **Lives** — you start with 15. Each enemy that reaches the exit costs 1 life. Hit 0 and it's game over.
- **Gold** — earned by killing enemies, spent to build towers. You start with 200g.
- **Waves** — 5 waves of increasing difficulty. Click "Next Wave" when you're ready. Enemies won't spawn until you do.
- **Towers** — click a tower in the shop bar, then click a buildable cell to place it. Hover to preview range. Click "Sell Tower" then click a placed tower to get 70% gold back.

### Tower Types

| Tower | Cost | Damage Type | Notes |
|-------|------|-------------|-------|
| Arrow | 50g | Physical | Balanced all-rounder |
| Cannon | 100g | Physical | Slow, high damage, splash AOE |
| Frost | 75g | Ice | Low damage, slows enemies |
| Mage | 120g | Magic | Long range, ignores armor |
| Anti-Air | 90g | Physical | Only tower that can hit flying enemies |

### Enemy Types

| Enemy | HP | Speed | Armor | Notes |
|-------|-----|-------|-------|-------|
| Grunt | 50 | 1.5 | 0 | Basic fodder, appears in large groups |
| Runner | 30 | 4.0 | 0 | Fast and fragile |
| Tank | 300 | 0.8 | 15 | Slow, heavy armor — needs magic or volume |
| Boss | 1000 | 0.5 | 10 | Massive HP pool, one per wave |
| Flying | 60 | 3.0 | 0 | Only Anti-Air towers can target these |

## Project Structure

```
gui.py                   ← Graphical game (tkinter)
main.py                  ← Headless demo (terminal simulation)
engine/                  ← Core game engine (no rendering)
├── __init__.py
├── game_state.py        ← Central orchestrator: state + update loop
├── track.py             ← Waypoint paths enemies follow
├── enemies.py           ← Enemy base class + 5 templates
├── towers.py            ← Tower base class + 5 templates
├── waves.py             ← Wave definitions and spawn scheduling
├── projectiles.py       ← Projectile movement and damage
├── effects.py           ← Status effects (slow, burn, armor reduction)
├── events.py            ← Pub/sub event bus
└── grid.py              ← 2D grid map with terrain types
levels/                  ← Level definitions
├── __init__.py
└── forest_clearing.py   ← Example level (8x10 map, 5 waves)
```

### How Systems Connect

```
WaveManager  ──spawns──→  Enemies  ──move along──→  Track
                              ↑ targeted by
Towers  ──fires──→  Projectiles  ──applies──→  Damage / Effects
  ↓ placed on
Grid (buildable cells)

All systems  ──emit──→  EventBus  ──notifies──→  GUI / Audio / etc.
```

**GameState** drives the update loop each frame:
1. Spawn enemies from the current wave
2. Move all enemies along their track
3. Towers select targets and fire projectiles
4. Projectiles move and apply damage on arrival
5. Dead enemies grant gold; leaked enemies cost lives
6. Check for wave completion and game over

## Adding a New Level

Levels live in `levels/` as standalone Python modules. Copy `forest_clearing.py` and modify:

1. `LAYOUT` — 2D grid (`0`=empty, `1`=path, `2`=buildable, `3`=blocked)
2. `PATH_COORDS` — ordered `(row, col)` waypoints tracing the enemy route
3. `_build_waves()` — enemy types, counts, and spawn intervals per wave
4. `STARTING_LIVES` / `STARTING_GOLD` — difficulty tuning

Each level exposes a `create()` function that returns a ready-to-play `(GameState, EventBus)`.

## Things That Need to Be Added

### High Priority

- [ ] **Sprites / art** — towers and enemies are placeholder squares right now. Add image assets and load them onto the canvas.
- [ ] **Tower upgrade system** — `Tower.upgrade()` exists but there's no UI for it. Need upgrade button, cost scaling, and visual feedback per tier.
- [ ] **Status effect integration** — `SlowEffect` and `BurnEffect` are defined but Frost/Fire towers don't actually apply them on hit yet. Wire projectile impact → effect creation.
- [ ] **Sound effects** — the EventBus already emits `ENEMY_KILLED`, `TOWER_PLACED`, `WAVE_START`, etc. Subscribe with audio playback callbacks.
- [ ] **More levels** — only one level exists (`forest_clearing`). Add a level select screen and more maps.
- [ ] **Pause / resume** — no way to pause the game mid-wave.

### Medium Priority

- [ ] **Tower sell confirmation** — currently one-click sell with no undo.
- [ ] **Enemy damage type resistances** — armor only reduces PHYSICAL. Add per-type resistance multipliers so enemies can be resistant/weak to fire, ice, magic.
- [ ] **Wave auto-start option** — currently manual "Next Wave" click. Add a timer or auto-send toggle.
- [ ] **Multiple tracks / lanes** — `TrackManager` exists but only one track is used per level.
- [ ] **Targeting strategy UI** — towers default to FIRST. Let the player pick FIRST / LAST / STRONGEST / CLOSEST per tower.
- [ ] **Effect stacking rules** — multiple slows currently stack without limit. Need diminishing returns or refresh-only behavior.
- [ ] **Tower range preview on hover** — works during placement but not for already-placed towers.
- [ ] **Minimap or camera panning** — needed for larger maps that don't fit on screen.

### Nice to Have

- [ ] **Animations** — death effects, projectile trails, tower firing animations.
- [ ] **Score / leaderboard** — persist high scores between sessions.
- [ ] **Save / load** — serialize `GameState` to JSON for mid-game saves.
- [ ] **Fast forward** — speed up the simulation (2x, 3x) during slow waves.
- [ ] **Tooltip system** — hover over towers/enemies to see stats.
- [ ] **Dynamic pathfinding** — enemies use fixed tracks. Add A* so they can reroute if towers block paths (maze TD style).
- [ ] **Mod / plugin support** — the event bus and class-based design support it, but there's no loader yet.
- [ ] **Multiplayer** — GameState is deterministic given the same inputs, suitable for lockstep networking.
