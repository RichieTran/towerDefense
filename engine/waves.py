"""
Wave / Spawner System
=====================

Controls when and what enemies appear. A Wave is a sequence of WaveEntries,
each specifying an enemy type, count, and spawn interval. The WaveManager
orchestrates progression through all waves.

How it fits in the engine:
    - ``GameState.start_wave()`` tells WaveManager to begin the next wave.
    - Each frame, ``WaveManager.update(dt)`` spawns enemies at the correct
      intervals and appends them to ``GameState.active_enemies``.
    - When all enemies in a wave are dead and no more spawns remain,
      the EventBus emits WAVE_COMPLETE.

Example::

    wave = Wave(entries=[
        WaveEntry(enemy_type=Grunt, count=10, spawn_interval=0.5),
        WaveEntry(enemy_type=Runner, count=5, spawn_interval=0.3),
    ])
    manager = WaveManager(waves=[wave])
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, List, Optional, Type

if TYPE_CHECKING:
    from engine.enemies import Enemy
    from engine.track import Track


@dataclass
class WaveEntry:
    """A single group of enemies within a wave.

    Example::

        entry = WaveEntry(enemy_type=Grunt, count=10, spawn_interval=0.5)

    Attributes:
        enemy_type:     The Enemy subclass to instantiate.
        count:          How many of this enemy to spawn.
        spawn_interval: Seconds between each spawn.
    """

    enemy_type: Type[Enemy]
    count: int = 1
    spawn_interval: float = 1.0


class Wave:
    """A single wave composed of one or more WaveEntries executed sequentially.

    Example::

        wave = Wave(entries=[
            WaveEntry(enemy_type=Grunt, count=5, spawn_interval=0.8),
            WaveEntry(enemy_type=Tank, count=1, spawn_interval=0.0),
        ])

    Attributes:
        entries:        Ordered list of WaveEntry groups.
        _entry_index:   Index of the current WaveEntry being spawned.
        _spawned:       How many enemies have been spawned from the current entry.
        _timer:         Countdown to the next spawn.
        _started:       Whether the wave has begun.
        _finished:      Whether all entries have been fully spawned.
    """

    def __init__(self, entries: List[WaveEntry] | None = None) -> None:
        self.entries: List[WaveEntry] = entries or []
        self._entry_index: int = 0
        self._spawned: int = 0
        self._timer: float = 0.0
        self._started: bool = False
        self._finished: bool = False

    @property
    def is_finished(self) -> bool:
        """True when every entry has been fully spawned."""
        return self._finished

    def start(self) -> None:
        """Begin spawning enemies for this wave.

        Side effects:
            Resets internal counters and marks the wave as started.
        """
        self._entry_index = 0
        self._spawned = 0
        self._timer = 0.0
        self._started = True
        self._finished = False

    def update(self, dt: float, track: Track) -> List[Enemy]:
        """Advance spawn timers and return any newly spawned enemies.

        Args:
            dt:    Delta time in seconds.
            track: The Track to assign to spawned enemies.

        Returns:
            A list of newly created Enemy instances (may be empty).
        """
        if not self._started or self._finished:
            return []

        spawned: List[Enemy] = []
        self._timer -= dt

        while self._timer <= 0 and not self._finished:
            entry = self.entries[self._entry_index]
            enemy = entry.enemy_type(track=track)
            spawned.append(enemy)
            self._spawned += 1

            if self._spawned >= entry.count:
                # Move to next entry
                self._entry_index += 1
                self._spawned = 0
                if self._entry_index >= len(self.entries):
                    self._finished = True
                    break
                self._timer += self.entries[self._entry_index].spawn_interval
            else:
                self._timer += entry.spawn_interval

        return spawned


class WaveManager:
    """Manages progression through all waves in the level.

    Example::

        wm = WaveManager(waves=[wave1, wave2, wave3])
        wm.start_next_wave()
        new_enemies = wm.update(dt, track)

    Attributes:
        waves:            Ordered list of Wave objects for the level.
        current_wave_idx: Index of the active wave (-1 if none started).
        all_complete:     True when every wave has been spawned and cleared.
    """

    def __init__(self, waves: List[Wave] | None = None) -> None:
        self.waves: List[Wave] = waves or []
        self.current_wave_idx: int = -1
        self.all_complete: bool = False

    @property
    def current_wave(self) -> Optional[Wave]:
        """The currently active Wave, or None."""
        if 0 <= self.current_wave_idx < len(self.waves):
            return self.waves[self.current_wave_idx]
        return None

    @property
    def wave_number(self) -> int:
        """Human-readable wave number (1-indexed)."""
        return self.current_wave_idx + 1

    def start_next_wave(self) -> bool:
        """Advance to and start the next wave.

        Returns:
            True if a new wave was started, False if no more waves remain.

        Side effects:
            Increments ``current_wave_idx`` and calls ``wave.start()``.

        TODO: Emit WAVE_START event via EventBus.
        """
        next_idx = self.current_wave_idx + 1
        if next_idx >= len(self.waves):
            self.all_complete = True
            return False

        self.current_wave_idx = next_idx
        self.waves[next_idx].start()
        return True

    def update(self, dt: float, track: Track) -> List[Enemy]:
        """Tick the current wave's spawner.

        Args:
            dt:    Delta time in seconds.
            track: Track to assign to spawned enemies.

        Returns:
            List of newly spawned enemies (may be empty).
        """
        wave = self.current_wave
        if wave is None:
            return []
        return wave.update(dt, track)

    def is_wave_spawning_done(self) -> bool:
        """Check if the current wave has finished spawning all enemies.

        Returns:
            True if all spawns are complete for the current wave.
        """
        wave = self.current_wave
        return wave is not None and wave.is_finished

    def check_wave_complete(self, active_enemies: List[Enemy]) -> bool:
        """Check if the current wave is fully complete (spawned + all dead).

        Args:
            active_enemies: The list of currently living enemies.

        Returns:
            True if spawning is done and no enemies remain alive.

        TODO: Emit WAVE_COMPLETE event via EventBus when True.
        """
        if not self.is_wave_spawning_done():
            return False
        return all(not e.alive for e in active_enemies)
