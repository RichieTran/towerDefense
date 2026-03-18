"""
Game State
==========

Central orchestrator that owns all game data and drives the per-frame
update loop. GameState ties together the grid, tracks, towers, enemies,
waves, projectiles, and event bus into a cohesive whole.

How it fits in the engine:
    - The top-level game loop (``main.py``) creates a GameState and calls
      ``update(dt)`` every frame.
    - GameState delegates to subsystems: WaveManager spawns enemies,
      towers find targets and fire, ProjectileManager moves projectiles,
      enemies move and take damage.

Example::

    state = GameState(grid=grid, track=main_track, wave_manager=wm, event_bus=bus)
    state.place_tower(ArrowTower(), (3, 5))
    state.start_wave()
    state.update(0.016)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from engine.effects import EffectManager
from engine.events import EventBus, EventType
from engine.grid import Grid
from engine.projectiles import ProjectileManager
from engine.towers import TargetingStrategy, Tower
from engine.track import Track
from engine.waves import WaveManager

if TYPE_CHECKING:
    from engine.enemies import Enemy


class GameState:
    """Central game state and update loop.

    Example::

        gs = GameState(grid=grid, track=track, wave_manager=wm)
        gs.place_tower(ArrowTower(), (3, 5))
        gs.start_wave()
        while not gs.game_over:
            gs.update(1/60)

    Attributes:
        lives:            Player's remaining lives.
        gold:             Current gold for buying/upgrading towers.
        score:            Accumulated score.
        towers:           List of placed Tower objects.
        active_enemies:   List of currently alive enemies on the field.
        track:            The primary Track enemies follow.
        grid:             The Grid representing the map.
        wave_manager:     WaveManager controlling enemy spawns.
        projectile_mgr:   ProjectileManager for in-flight projectiles.
        event_bus:        EventBus for decoupled communication.
        game_over:        True when the player has lost (or won).
    """

    def __init__(
        self,
        grid: Grid,
        track: Track,
        wave_manager: WaveManager,
        event_bus: EventBus | None = None,
        lives: int = 20,
        gold: int = 200,
    ) -> None:
        self.lives = lives
        self.gold = gold
        self.score: int = 0
        self.towers: List[Tower] = []
        self.active_enemies: List[Enemy] = []
        self.track = track
        self.grid = grid
        self.wave_manager = wave_manager
        self.projectile_mgr = ProjectileManager()
        self.event_bus = event_bus or EventBus()
        self.game_over: bool = False

        # TODO: Add support for multiple tracks
        # TODO: Add pause/resume state

    @property
    def current_wave(self) -> int:
        """Human-readable current wave number (1-indexed)."""
        return self.wave_manager.wave_number

    def place_tower(self, tower: Tower, position: tuple[int, int]) -> bool:
        """Place a tower on the grid if the cell is buildable and gold is sufficient.

        Args:
            tower:    The Tower instance to place.
            position: (row, col) grid coordinates.

        Returns:
            True if the tower was successfully placed.

        Side effects:
            Deducts gold, marks grid cell, adds tower to list,
            emits TOWER_PLACED event.
        """
        if self.gold < tower.cost:
            return False

        row, col = position
        if not self.grid.place_tower(row, col):
            return False

        tower.position = (float(col), float(row))  # (x, y) from (row, col)
        self.gold -= tower.cost
        self.towers.append(tower)

        self.event_bus.emit(EventType.TOWER_PLACED, {
            "tower": tower,
            "position": position,
        })
        return True

    def sell_tower(self, tower: Tower) -> bool:
        """Sell a tower, refunding a portion of its cost.

        Args:
            tower: The Tower instance to sell.

        Returns:
            True if the tower was found and sold.

        Side effects:
            Refunds gold, frees grid cell, removes tower from list,
            emits TOWER_SOLD event.
        """
        if tower not in self.towers:
            return False

        refund = tower.sell_value()
        self.gold += refund
        self.towers.remove(tower)

        # Free the grid cell
        tx, ty = tower.position
        self.grid.remove_tower(int(ty), int(tx))

        self.event_bus.emit(EventType.TOWER_SOLD, {
            "tower": tower,
            "refund": refund,
        })
        return True

    def start_wave(self) -> bool:
        """Begin the next wave of enemies.

        Returns:
            True if a new wave was started, False if no more waves.

        Side effects:
            Starts the wave via WaveManager, emits WAVE_START event.
        """
        started = self.wave_manager.start_next_wave()
        if started:
            self.event_bus.emit(EventType.WAVE_START, {
                "wave_number": self.current_wave,
            })
        return started

    def update(self, dt: float) -> None:
        """Main per-frame update. Advances all game systems.

        Call this once per frame from the game loop.

        Args:
            dt: Delta time in seconds since the last frame.

        Side effects:
            Spawns enemies, moves enemies, fires towers, moves projectiles,
            checks for enemy deaths and leak-throughs, checks wave completion
            and game-over.

        TODO: Update enemy effect managers (status effects).
        TODO: Add rendering hooks / callback.
        TODO: Add audio trigger points.
        """
        if self.game_over:
            return

        # 1. Spawn enemies from current wave
        new_enemies = self.wave_manager.update(dt, self.track)
        for enemy in new_enemies:
            enemy.effects = EffectManager(enemy)
            self.active_enemies.append(enemy)

        # 2. Move enemies
        for enemy in self.active_enemies:
            if enemy.alive:
                enemy.move(dt)
                # Update status effects
                if enemy.effects:
                    enemy.effects.update(dt)

        # 3. Check for enemies reaching the end
        for enemy in self.active_enemies:
            if enemy.is_at_end():
                self.lose_life(1)
                enemy.alive = False
                self.event_bus.emit(EventType.ENEMY_REACHED_END, {
                    "enemy": enemy,
                    "lives_lost": 1,
                })

        # 4. Towers find targets and fire
        for tower in self.towers:
            tower.update_cooldown(dt)
            if tower.can_fire():
                target = tower.find_target(
                    self.active_enemies, TargetingStrategy.FIRST
                )
                if target:
                    shot_data = tower.fire(target)
                    self.projectile_mgr.create(
                        origin=shot_data["origin"],
                        target=shot_data["target"],
                        damage=shot_data["damage"],
                        damage_type=shot_data["damage_type"],
                        splash_radius=shot_data["splash_radius"],
                    )

        # 5. Move projectiles and apply damage
        self.projectile_mgr.update(dt, self.active_enemies)

        # 6. Process enemy deaths
        for enemy in self.active_enemies:
            if not enemy.alive and enemy.reward > 0:
                self.gold += enemy.reward
                self.score += enemy.reward
                self.event_bus.emit(EventType.ENEMY_KILLED, {
                    "enemy": enemy,
                    "reward": enemy.reward,
                })
                enemy.reward = 0  # prevent double-counting

        # 7. Clean up dead enemies
        self.active_enemies = [e for e in self.active_enemies if e.alive]

        # 8. Check wave completion
        if self.wave_manager.check_wave_complete(self.active_enemies):
            self.event_bus.emit(EventType.WAVE_COMPLETE, {
                "wave_number": self.current_wave,
            })
            # TODO: Auto-start next wave after a delay, or wait for player input

        # 9. Check game over
        if self.lives <= 0:
            self.game_over = True
            self.event_bus.emit(EventType.GAME_OVER, {
                "score": self.score,
                "waves_survived": self.current_wave,
            })

    def is_wave_complete(self) -> bool:
        """Check if the current wave is fully cleared.

        Returns:
            True if all enemies from the current wave are dead.
        """
        return self.wave_manager.check_wave_complete(self.active_enemies)

    def lose_life(self, amount: int = 1) -> None:
        """Reduce player lives.

        Args:
            amount: Number of lives to lose.

        Side effects:
            Decreases ``lives`` (floored at 0).
        """
        self.lives = max(0, self.lives - amount)
