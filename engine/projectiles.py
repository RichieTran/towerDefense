"""
Projectile System
=================

Manages the in-flight objects between a tower firing and damage being applied
to an enemy. Projectiles travel toward their target each frame and apply
damage (single-target or splash) on arrival.

How it fits in the engine:
    - When a Tower fires, it returns projectile data; the ProjectileManager
      creates a Projectile from that data.
    - Each frame, ``ProjectileManager.update(dt)`` moves all projectiles
      and applies damage for any that have reached their target.
    - The GameState owns a ProjectileManager and calls its update.

Example::

    pm = ProjectileManager()
    pm.create(origin=(3, 5), target=enemy, damage=15,
              damage_type=DamageType.PHYSICAL)
    pm.update(dt, all_enemies)
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, List

from engine.enemies import DamageType

if TYPE_CHECKING:
    from engine.enemies import Enemy


class Projectile:
    """A single in-flight projectile.

    Example::

        p = Projectile(position=(3, 5), speed=8.0, target=enemy,
                        damage=15, damage_type=DamageType.PHYSICAL)
        p.move(0.016)
        if p.has_reached_target():
            p.apply_damage(all_enemies)

    Attributes:
        position:       Current (x, y) world position.
        speed:          Movement speed in world units per second.
        target:         The Enemy this projectile is homing toward.
        damage:         Damage to deal on impact.
        damage_type:    The DamageType of the damage.
        splash_radius:  AOE radius. 0 means single-target only.
        alive:          False after damage has been applied.
    """

    def __init__(
        self,
        position: tuple[float, float],
        speed: float,
        target: Enemy,
        damage: float,
        damage_type: DamageType = DamageType.PHYSICAL,
        splash_radius: float = 0.0,
    ) -> None:
        self.position = position
        self.speed = speed
        self.target = target
        self.damage = damage
        self.damage_type = damage_type
        self.splash_radius = splash_radius
        self.alive: bool = True

        # TODO: Add sprite / trail VFX reference
        # TODO: Add impact SFX reference

    def move(self, dt: float) -> None:
        """Move the projectile toward its target.

        If the target has died mid-flight, the projectile continues toward
        the target's last known position.

        Args:
            dt: Delta time in seconds.

        Side effects:
            Updates ``position``.
        """
        if not self.alive:
            return

        tx, ty = self.target.position
        px, py = self.position
        dx, dy = tx - px, ty - py
        dist = math.hypot(dx, dy)

        if dist == 0:
            return

        move_dist = self.speed * dt
        if move_dist >= dist:
            self.position = (tx, ty)
        else:
            ratio = move_dist / dist
            self.position = (px + dx * ratio, py + dy * ratio)

    def has_reached_target(self) -> bool:
        """Check if the projectile has arrived at the target's position.

        Returns:
            True if the projectile is within a small threshold of the target.
        """
        tx, ty = self.target.position
        px, py = self.position
        return math.hypot(tx - px, ty - py) < 0.1

    def apply_damage(self, all_enemies: List[Enemy]) -> None:
        """Deal damage to the target (and nearby enemies if splash > 0).

        Args:
            all_enemies: All active enemies, used for splash calculations.

        Side effects:
            Calls ``take_damage`` on affected enemies. Marks projectile dead.

        TODO: Trigger impact VFX / SFX.
        """
        if not self.alive:
            return

        self.alive = False

        if self.splash_radius > 0:
            # AOE: damage all enemies within splash_radius of impact point
            ix, iy = self.position
            for enemy in all_enemies:
                if not enemy.alive:
                    continue
                ex, ey = enemy.position
                if math.hypot(ex - ix, ey - iy) <= self.splash_radius:
                    enemy.take_damage(self.damage, self.damage_type)
        else:
            # Single target
            if self.target.alive:
                self.target.take_damage(self.damage, self.damage_type)


class ProjectileManager:
    """Tracks and updates all active projectiles.

    Example::

        pm = ProjectileManager()
        pm.create(origin=(3, 5), target=enemy, damage=15,
                  damage_type=DamageType.PHYSICAL)
        pm.update(0.016, all_enemies)

    Attributes:
        projectiles:      List of active Projectile objects.
        projectile_speed: Default speed for new projectiles (world units/sec).
    """

    def __init__(self, projectile_speed: float = 8.0) -> None:
        self.projectiles: List[Projectile] = []
        self.projectile_speed = projectile_speed

    def create(
        self,
        origin: tuple[float, float],
        target: Enemy,
        damage: float,
        damage_type: DamageType = DamageType.PHYSICAL,
        splash_radius: float = 0.0,
        speed: float | None = None,
    ) -> Projectile:
        """Create and register a new projectile.

        Args:
            origin:        Starting (x, y) position (usually the tower).
            target:        The enemy being targeted.
            damage:        Damage on impact.
            damage_type:   DamageType of the damage.
            splash_radius: AOE radius (0 = single target).
            speed:         Override default projectile speed.

        Returns:
            The newly created Projectile.
        """
        proj = Projectile(
            position=origin,
            speed=speed if speed is not None else self.projectile_speed,
            target=target,
            damage=damage,
            damage_type=damage_type,
            splash_radius=splash_radius,
        )
        self.projectiles.append(proj)
        return proj

    def update(self, dt: float, all_enemies: List[Enemy]) -> None:
        """Move all projectiles and apply damage for those that have arrived.

        Args:
            dt:          Delta time in seconds.
            all_enemies: All active enemies (for splash damage calculations).

        Side effects:
            Moves projectiles, applies damage, and removes dead projectiles.
        """
        for proj in self.projectiles:
            proj.move(dt)
            if proj.has_reached_target():
                proj.apply_damage(all_enemies)

        # Remove dead projectiles
        self.projectiles = [p for p in self.projectiles if p.alive]

    def clear(self) -> None:
        """Remove all projectiles. Useful between waves or on game reset.

        Side effects:
            Empties the projectiles list.
        """
        self.projectiles.clear()
