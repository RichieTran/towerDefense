"""
Tower / Defense System
======================

Defines the stationary defenses that the player places on the grid to
destroy enemies. Each tower has range, damage, fire rate, and a targeting
strategy that determines which enemy it prioritizes.

How it fits in the engine:
    - Towers are placed via ``GameState.place_tower()`` which validates
      gold and grid buildability.
    - Each frame, ``GameState.update(dt)`` iterates towers, calls
      ``find_target()`` and ``fire()`` to create projectiles.
    - The EventBus emits TOWER_PLACED / TOWER_SOLD events.

Example::

    tower = ArrowTower(position=(3, 5))
    if tower.can_fire():
        target = tower.find_target(active_enemies, TargetingStrategy.FIRST)
        if target:
            tower.fire(target)
"""

from __future__ import annotations

import math
from enum import Enum, auto
from typing import TYPE_CHECKING, List, Optional

from engine.enemies import DamageType

if TYPE_CHECKING:
    from engine.enemies import Enemy


class TargetingStrategy(Enum):
    """How a tower selects which enemy to shoot.

    FIRST:     The enemy closest to the end of the track (highest progress).
    LAST:      The enemy furthest from the end (lowest progress).
    STRONGEST: The enemy with the most current health.
    CLOSEST:   The enemy nearest to the tower in Euclidean distance.
    """

    FIRST = auto()
    LAST = auto()
    STRONGEST = auto()
    CLOSEST = auto()


class Tower:
    """Base class for all player-placeable towers.

    Example::

        tower = Tower(name="Basic", position=(5, 3), range_=4.0,
                      damage=10, fire_rate=1.0, cost=50)
        if tower.can_fire():
            target = tower.find_target(enemies, TargetingStrategy.FIRST)

    Attributes:
        name:              Display name.
        position:          (x, y) grid or world position.
        range_:            Attack radius in world units.
        damage:            Damage per shot.
        fire_rate:         Shots per second.
        cooldown_timer:    Seconds remaining before the tower can fire again.
        cost:              Gold cost to build.
        upgrade_level:     Current upgrade tier (starts at 1).
        damage_type:       The DamageType dealt by this tower.
        can_target_air:    Whether this tower can hit flying enemies.
        splash_radius:     AOE radius (0 = single target).
    """

    def __init__(
        self,
        name: str = "Tower",
        position: tuple[float, float] = (0, 0),
        range_: float = 3.0,
        damage: float = 10,
        fire_rate: float = 1.0,
        cost: int = 50,
        damage_type: DamageType = DamageType.PHYSICAL,
        can_target_air: bool = False,
        splash_radius: float = 0.0,
    ) -> None:
        self.name = name
        self.position = position
        self.range_ = range_
        self.damage = damage
        self.fire_rate = fire_rate
        self.cooldown_timer: float = 0.0
        self.cost = cost
        self.upgrade_level: int = 1
        self.damage_type = damage_type
        self.can_target_air = can_target_air
        self.splash_radius = splash_radius

        # TODO: Add sprite / animation reference
        # TODO: Add upgrade path definitions (cost, stat changes per level)

    def can_fire(self) -> bool:
        """Check whether the cooldown has elapsed.

        Returns:
            True if the tower is ready to fire.
        """
        return self.cooldown_timer <= 0.0

    def find_target(
        self,
        enemies: List[Enemy],
        strategy: TargetingStrategy = TargetingStrategy.FIRST,
    ) -> Optional[Enemy]:
        """Select the best target from a list of enemies based on strategy.

        Only considers enemies that are alive, within range, and targetable
        (respects ``can_target_air`` vs ``enemy.is_flying``).

        Args:
            enemies:  All currently active enemies.
            strategy: The TargetingStrategy to use.

        Returns:
            The chosen Enemy, or None if no valid target exists.
        """
        candidates = [e for e in enemies if self._can_target(e)]

        if not candidates:
            return None

        if strategy == TargetingStrategy.FIRST:
            return max(candidates, key=lambda e: e.progress)
        elif strategy == TargetingStrategy.LAST:
            return min(candidates, key=lambda e: e.progress)
        elif strategy == TargetingStrategy.STRONGEST:
            return max(candidates, key=lambda e: e.health)
        elif strategy == TargetingStrategy.CLOSEST:
            return min(candidates, key=lambda e: self._distance_to(e))

        return candidates[0]

    def fire(self, target: Enemy) -> dict:
        """Fire at a target and reset the cooldown.

        Does NOT directly deal damage — instead returns the data needed
        for the ProjectileManager to create a projectile.

        Args:
            target: The enemy to shoot at.

        Returns:
            A dict with keys: origin, target, damage, damage_type,
            splash_radius — enough for ProjectileManager.create().

        Side effects:
            Resets ``cooldown_timer`` to ``1 / fire_rate``.

        TODO: Trigger firing animation / SFX.
        """
        self.cooldown_timer = 1.0 / self.fire_rate if self.fire_rate > 0 else 0.0

        return {
            "origin": self.position,
            "target": target,
            "damage": self.damage,
            "damage_type": self.damage_type,
            "splash_radius": self.splash_radius,
        }

    def update_cooldown(self, dt: float) -> None:
        """Tick the cooldown timer down.

        Args:
            dt: Delta time in seconds.
        """
        if self.cooldown_timer > 0:
            self.cooldown_timer -= dt

    def upgrade(self) -> int:
        """Upgrade the tower to the next level.

        Returns:
            The new upgrade level.

        Side effects:
            Increments ``upgrade_level`` and applies stat boosts.

        TODO: Define upgrade paths with specific costs and stat deltas
              per tower type. Currently applies a flat 20% boost.
        """
        self.upgrade_level += 1
        self.damage *= 1.2
        self.range_ *= 1.05
        return self.upgrade_level

    def sell_value(self) -> int:
        """Calculate gold returned when selling this tower.

        Returns:
            70% of the original cost (rounded down).

        TODO: Factor in upgrade costs for accurate refund.
        """
        return int(self.cost * 0.7)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _can_target(self, enemy: Enemy) -> bool:
        """Check if an enemy is a valid target (alive, in range, targetable).

        Args:
            enemy: The enemy to evaluate.

        Returns:
            True if the tower can attack this enemy.
        """
        if not enemy.alive:
            return False
        if enemy.is_flying and not self.can_target_air:
            return False
        return self._distance_to(enemy) <= self.range_

    def _distance_to(self, enemy: Enemy) -> float:
        """Euclidean distance from the tower to an enemy.

        Args:
            enemy: The enemy to measure distance to.

        Returns:
            Distance as a float.
        """
        ex, ey = enemy.position
        tx, ty = self.position
        return math.hypot(ex - tx, ey - ty)


# ---------------------------------------------------------------------------
# Template subclasses — override default stats only
# ---------------------------------------------------------------------------


class ArrowTower(Tower):
    """Balanced physical-damage tower. Good all-rounder.

    Example::

        arrow = ArrowTower(position=(3, 4))
    """

    def __init__(self, position: tuple[float, float] = (0, 0), **kwargs) -> None:
        defaults = dict(
            name="Arrow Tower",
            position=position,
            range_=4.0,
            damage=15,
            fire_rate=1.5,
            cost=50,
            damage_type=DamageType.PHYSICAL,
        )
        defaults.update(kwargs)
        super().__init__(**defaults)


class CannonTower(Tower):
    """Slow-firing AOE tower with high damage per shot.

    Example::

        cannon = CannonTower(position=(5, 2))
    """

    def __init__(self, position: tuple[float, float] = (0, 0), **kwargs) -> None:
        defaults = dict(
            name="Cannon Tower",
            position=position,
            range_=3.5,
            damage=40,
            fire_rate=0.5,
            cost=100,
            damage_type=DamageType.PHYSICAL,
            splash_radius=1.5,
        )
        defaults.update(kwargs)
        super().__init__(**defaults)


class FrostTower(Tower):
    """Slows enemies with ice damage. Low direct damage.

    Example::

        frost = FrostTower(position=(2, 6))

    TODO: Apply SlowEffect on hit via the effects system.
    """

    def __init__(self, position: tuple[float, float] = (0, 0), **kwargs) -> None:
        defaults = dict(
            name="Frost Tower",
            position=position,
            range_=3.0,
            damage=5,
            fire_rate=1.0,
            cost=75,
            damage_type=DamageType.ICE,
        )
        defaults.update(kwargs)
        super().__init__(**defaults)


class MageTower(Tower):
    """Long-range magic damage. Ignores armor.

    Example::

        mage = MageTower(position=(7, 3))
    """

    def __init__(self, position: tuple[float, float] = (0, 0), **kwargs) -> None:
        defaults = dict(
            name="Mage Tower",
            position=position,
            range_=5.5,
            damage=25,
            fire_rate=0.8,
            cost=120,
            damage_type=DamageType.MAGIC,
        )
        defaults.update(kwargs)
        super().__init__(**defaults)


class AntiAirTower(Tower):
    """Specialized tower that can target flying enemies.

    Example::

        aa = AntiAirTower(position=(4, 4))
    """

    def __init__(self, position: tuple[float, float] = (0, 0), **kwargs) -> None:
        defaults = dict(
            name="Anti-Air Tower",
            position=position,
            range_=5.0,
            damage=20,
            fire_rate=1.2,
            cost=90,
            damage_type=DamageType.PHYSICAL,
            can_target_air=True,
        )
        defaults.update(kwargs)
        super().__init__(**defaults)
