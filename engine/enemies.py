"""
Enemy System
=============

Defines the entities that traverse tracks and must be destroyed by towers.
Each enemy has health, speed, armor, and tracks its progress along a path.

How it fits in the engine:
    - Enemies are spawned by the Wave system and added to ``GameState.active_enemies``.
    - Each frame, ``GameState.update(dt)`` calls ``enemy.move(dt)`` to advance
      progress, then checks ``enemy.is_at_end()`` to deduct lives.
    - Towers and projectiles call ``enemy.take_damage()`` to reduce HP.
    - The EventBus emits ENEMY_KILLED / ENEMY_REACHED_END as appropriate.

Example::

    grunt = Grunt(track=main_track)
    grunt.move(0.016)          # advance by one frame at ~60fps
    grunt.take_damage(10, DamageType.PHYSICAL)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from engine.track import Track
    from engine.effects import EffectManager


class DamageType(Enum):
    """Categories of damage that interact with armor / resistances.

    TODO: Implement per-type resistance multipliers on enemies for richer
          rock-paper-scissors balancing.
    """

    PHYSICAL = auto()
    FIRE = auto()
    ICE = auto()
    MAGIC = auto()


class Enemy:
    """Base class for all enemies.

    Example::

        enemy = Enemy(track=my_track, health=100, speed=2.0, armor=5, reward=10)
        enemy.move(0.5)
        enemy.take_damage(20, DamageType.PHYSICAL)

    Attributes:
        track:      The Track this enemy follows.
        health:     Current hit points.
        max_health: Maximum hit points (for health-bar rendering).
        speed:      Movement speed in track-progress-units per second.
        armor:      Flat damage reduction applied before HP loss.
        reward:     Gold granted to the player on kill.
        progress:   Current position along the track (0.0 → 1.0).
        alive:      Whether the enemy is still active.
        is_flying:  If True, only anti-air towers can target this enemy.
        effects:    EffectManager handling active status effects.
    """

    def __init__(
        self,
        track: Track,
        health: float = 100,
        speed: float = 1.0,
        armor: float = 0,
        reward: int = 10,
        is_flying: bool = False,
    ) -> None:
        self.track = track
        self.health: float = health
        self.max_health: float = health
        self.speed: float = speed
        self.armor: float = armor
        self.reward: int = reward
        self.progress: float = 0.0
        self.alive: bool = True
        self.is_flying: bool = is_flying

        # Lazily imported to avoid circular deps; assigned after construction
        # by the spawner or GameState if needed.
        self.effects: EffectManager | None = None

        # TODO: Add sprite/animation reference for rendering
        # TODO: Add sound effect hooks for hit/death

    @property
    def position(self) -> tuple[float, float]:
        """Current world-space (x, y) derived from track progress.

        Returns:
            (x, y) tuple.
        """
        return self.track.get_position_at_progress(self.progress)

    def take_damage(self, amount: float, damage_type: DamageType = DamageType.PHYSICAL) -> None:
        """Apply damage to this enemy, reduced by armor.

        Armor provides flat reduction against PHYSICAL damage only (by default).
        Override this method or add resistance tables for richer interactions.

        Args:
            amount:      Raw damage before mitigation.
            damage_type: The DamageType of the incoming damage.

        Side effects:
            Reduces ``health``; calls ``die()`` if health drops to 0 or below.

        TODO: Implement per-damage-type resistance multipliers.
        TODO: Trigger hit VFX / SFX here.
        """
        if not self.alive:
            return

        effective = amount
        if damage_type == DamageType.PHYSICAL:
            effective = max(0.0, amount - self.armor)

        self.health -= effective

        if self.health <= 0:
            self.health = 0
            self.die()

    def move(self, dt: float) -> None:
        """Advance the enemy along its track.

        Args:
            dt: Delta time in seconds since the last frame.

        Side effects:
            Updates ``progress``. Does nothing if the enemy is dead.

        TODO: Factor in slow effects from ``self.effects`` to modify speed.
        """
        if not self.alive:
            return

        # speed is expressed as "fraction of total track per second"
        # so a speed of 0.1 means the enemy crosses the entire track in 10s.
        track_length = self.track.total_length()
        if track_length == 0:
            return

        # Convert speed (world units/sec) to progress/sec
        progress_per_sec = self.speed / track_length
        self.progress += progress_per_sec * dt
        self.progress = min(self.progress, 1.0)

    def is_at_end(self) -> bool:
        """Check whether the enemy has reached the end of its track.

        Returns:
            True if progress >= 1.0 and the enemy is still alive.
        """
        return self.alive and self.progress >= 1.0

    def die(self) -> None:
        """Mark the enemy as dead.

        Side effects:
            Sets ``alive`` to False.

        TODO: Trigger death animation / particle effect.
        TODO: Emit ENEMY_KILLED event via EventBus.
        """
        self.alive = False


# ---------------------------------------------------------------------------
# Template subclasses — override default stats only
# ---------------------------------------------------------------------------


class Grunt(Enemy):
    """Slow, low-HP fodder enemy.  Appears in large numbers early on.

    Example::

        grunt = Grunt(track=main_track)
    """

    def __init__(self, track: Track, **kwargs) -> None:
        defaults = dict(health=50, speed=1.5, armor=0, reward=5)
        defaults.update(kwargs)
        super().__init__(track=track, **defaults)


class Runner(Enemy):
    """Fast but fragile. Dangerous if towers have slow fire rates.

    Example::

        runner = Runner(track=main_track)
    """

    def __init__(self, track: Track, **kwargs) -> None:
        defaults = dict(health=30, speed=4.0, armor=0, reward=7)
        defaults.update(kwargs)
        super().__init__(track=track, **defaults)


class Tank(Enemy):
    """Slow, heavily armored. Requires magic or armor-piercing damage.

    Example::

        tank = Tank(track=main_track)
    """

    def __init__(self, track: Track, **kwargs) -> None:
        defaults = dict(health=300, speed=0.8, armor=15, reward=25)
        defaults.update(kwargs)
        super().__init__(track=track, **defaults)


class Boss(Enemy):
    """Massive HP pool. Usually one per wave. High reward.

    Example::

        boss = Boss(track=main_track)
    """

    def __init__(self, track: Track, **kwargs) -> None:
        defaults = dict(health=1000, speed=0.5, armor=10, reward=100)
        defaults.update(kwargs)
        super().__init__(track=track, **defaults)


class FlyingEnemy(Enemy):
    """Airborne enemy that bypasses ground-only towers.

    Only towers with ``can_target_air=True`` (e.g., AntiAirTower) can hit these.

    Example::

        flyer = FlyingEnemy(track=main_track)
    """

    def __init__(self, track: Track, **kwargs) -> None:
        defaults = dict(health=60, speed=3.0, armor=0, reward=15, is_flying=True)
        defaults.update(kwargs)
        super().__init__(track=track, **defaults)
