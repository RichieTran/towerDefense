"""
Status Effects System
=====================

Provides time-based modifiers that alter enemy stats (speed, armor, HP over
time). Effects are applied by towers/projectiles and managed per-enemy by
an EffectManager.

How it fits in the engine:
    - When a FrostTower's projectile hits, it creates a SlowEffect and
      adds it to the target's EffectManager.
    - Each frame, ``EffectManager.update(dt)`` ticks all active effects,
      applying periodic damage or stat changes and removing expired ones.
    - Effects reference the enemy they are attached to and mutate its stats.

Example::

    em = EffectManager(enemy=some_enemy)
    em.add(SlowEffect(factor=0.5, duration=3.0))
    em.add(BurnEffect(damage_per_tick=5, duration=4.0, tick_interval=1.0))
    em.update(dt)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from engine.enemies import Enemy


class StatusEffect:
    """Base class for all status effects.

    Example::

        effect = StatusEffect(duration=5.0, tick_interval=1.0)

    Attributes:
        duration:       Total time the effect lasts (seconds).
        remaining:      Time left before the effect expires.
        tick_interval:  How often ``tick`` fires (seconds). 0 = every frame.
        _tick_timer:    Internal countdown to next tick.
        source:         Optional label for what created this effect.
    """

    def __init__(
        self,
        duration: float = 5.0,
        tick_interval: float = 0.0,
        source: str = "",
    ) -> None:
        self.duration = duration
        self.remaining: float = duration
        self.tick_interval = tick_interval
        self._tick_timer: float = 0.0
        self.source = source

    def apply(self, enemy: Enemy) -> None:
        """Called once when the effect is first attached to an enemy.

        Override in subclasses to apply initial stat changes.

        Args:
            enemy: The enemy receiving this effect.

        TODO: Trigger VFX indicator (e.g., frost overlay) on the enemy.
        """
        pass

    def tick(self, dt: float, enemy: Enemy) -> None:
        """Called periodically (every ``tick_interval`` seconds).

        Override in subclasses to apply recurring damage or stat changes.

        Args:
            dt:    Delta time since last frame (for continuous effects).
            enemy: The enemy this effect is attached to.
        """
        pass

    def remove(self, enemy: Enemy) -> None:
        """Called when the effect expires or is manually removed.

        Override in subclasses to revert stat changes.

        Args:
            enemy: The enemy this effect is being removed from.
        """
        pass

    def is_expired(self) -> bool:
        """Check whether the effect's duration has elapsed.

        Returns:
            True if the effect should be removed.
        """
        return self.remaining <= 0

    def update(self, dt: float, enemy: Enemy) -> None:
        """Advance timers and call tick if appropriate.

        Args:
            dt:    Delta time in seconds.
            enemy: The enemy this effect is attached to.

        Side effects:
            Decrements ``remaining``; calls ``tick()`` at the right interval.
        """
        self.remaining -= dt

        if self.tick_interval <= 0:
            # Continuous: tick every frame
            self.tick(dt, enemy)
        else:
            self._tick_timer -= dt
            if self._tick_timer <= 0:
                self.tick(dt, enemy)
                self._tick_timer = self.tick_interval


# ---------------------------------------------------------------------------
# Template effects
# ---------------------------------------------------------------------------


class SlowEffect(StatusEffect):
    """Reduces enemy movement speed for a duration.

    Example::

        slow = SlowEffect(factor=0.5, duration=3.0)
        # Enemy moves at 50% speed for 3 seconds.

    Attributes:
        factor: Multiplier applied to enemy speed (0.5 = half speed).
    """

    def __init__(self, factor: float = 0.5, duration: float = 3.0, **kwargs) -> None:
        super().__init__(duration=duration, source="frost", **kwargs)
        self.factor = factor
        self._original_speed: float = 0.0

    def apply(self, enemy: Enemy) -> None:
        """Store original speed and reduce it.

        Args:
            enemy: The affected enemy.
        """
        self._original_speed = enemy.speed
        enemy.speed *= self.factor

    def remove(self, enemy: Enemy) -> None:
        """Restore the enemy's original speed.

        Args:
            enemy: The affected enemy.
        """
        enemy.speed = self._original_speed


class BurnEffect(StatusEffect):
    """Deals fire damage over time.

    Example::

        burn = BurnEffect(damage_per_tick=5, duration=4.0, tick_interval=1.0)
        # 5 fire damage every 1s for 4s = 20 total.

    Attributes:
        damage_per_tick: Fire damage applied each tick.
    """

    def __init__(
        self,
        damage_per_tick: float = 5.0,
        duration: float = 4.0,
        tick_interval: float = 1.0,
        **kwargs,
    ) -> None:
        super().__init__(duration=duration, tick_interval=tick_interval, source="fire", **kwargs)
        self.damage_per_tick = damage_per_tick

    def tick(self, dt: float, enemy: Enemy) -> None:
        """Deal fire damage.

        Args:
            dt:    Unused for tick-based effects.
            enemy: The burning enemy.
        """
        from engine.enemies import DamageType

        enemy.take_damage(self.damage_per_tick, DamageType.FIRE)


class ArmorReductionEffect(StatusEffect):
    """Temporarily reduces an enemy's armor.

    Example::

        shred = ArmorReductionEffect(reduction=10, duration=5.0)
        # Enemy loses 10 armor for 5 seconds.

    Attributes:
        reduction: Flat armor points removed.
    """

    def __init__(self, reduction: float = 10.0, duration: float = 5.0, **kwargs) -> None:
        super().__init__(duration=duration, source="armor_shred", **kwargs)
        self.reduction = reduction

    def apply(self, enemy: Enemy) -> None:
        """Reduce armor (floored at 0).

        Args:
            enemy: The affected enemy.
        """
        enemy.armor = max(0, enemy.armor - self.reduction)

    def remove(self, enemy: Enemy) -> None:
        """Restore armor.

        Args:
            enemy: The affected enemy.
        """
        enemy.armor += self.reduction


# ---------------------------------------------------------------------------
# Effect Manager
# ---------------------------------------------------------------------------


class EffectManager:
    """Manages all active status effects on a single enemy.

    Example::

        em = EffectManager(enemy=grunt)
        em.add(SlowEffect(factor=0.5, duration=3.0))
        em.update(0.016)

    Attributes:
        enemy:   The enemy these effects are attached to.
        effects: List of active StatusEffect instances.
    """

    def __init__(self, enemy: Enemy) -> None:
        self.enemy = enemy
        self.effects: List[StatusEffect] = []

    def add(self, effect: StatusEffect) -> None:
        """Attach a new effect to the enemy.

        Args:
            effect: The StatusEffect to add.

        Side effects:
            Calls ``effect.apply(enemy)`` immediately.

        TODO: Implement stacking rules (refresh duration, stack intensity, etc.)
        """
        effect.apply(self.enemy)
        self.effects.append(effect)

    def update(self, dt: float) -> None:
        """Tick all effects and remove expired ones.

        Args:
            dt: Delta time in seconds.

        Side effects:
            Updates each effect; calls ``remove()`` on expired effects.
        """
        expired: List[StatusEffect] = []

        for effect in self.effects:
            effect.update(dt, self.enemy)
            if effect.is_expired():
                expired.append(effect)

        for effect in expired:
            effect.remove(self.enemy)
            self.effects.remove(effect)

    def clear(self) -> None:
        """Remove all effects immediately.

        Side effects:
            Calls ``remove()`` on every active effect.
        """
        for effect in self.effects:
            effect.remove(self.enemy)
        self.effects.clear()

    def has_effect(self, effect_type: type) -> bool:
        """Check if the enemy currently has an effect of the given type.

        Args:
            effect_type: The class to check for (e.g., SlowEffect).

        Returns:
            True if at least one matching effect is active.
        """
        return any(isinstance(e, effect_type) for e in self.effects)
