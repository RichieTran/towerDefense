"""
Event System
============

A lightweight publish/subscribe bus that decouples game systems. Any module
can emit events (e.g., ENEMY_KILLED) and any module can subscribe to them
without direct imports between emitter and listener.

How it fits in the engine:
    - A single EventBus instance is created by GameState and shared with
      all subsystems.
    - Systems emit events at key moments (enemy dies, wave starts, etc.).
    - UI, audio, analytics, or any other layer subscribes to react.

Example::

    bus = EventBus()
    bus.subscribe(EventType.ENEMY_KILLED, lambda data: print(f"Kill! +{data['reward']}g"))
    bus.emit(EventType.ENEMY_KILLED, {"enemy": grunt, "reward": 10})
"""

from __future__ import annotations

from collections import defaultdict
from enum import Enum, auto
from typing import Any, Callable, Dict, List


class EventType(Enum):
    """Predefined game event types.

    Add new entries here as the game grows. Event data schemas are
    documented by convention (see emit calls in each module).

    TODO: Consider making this extensible with string-based custom events
          for mod/plugin support.
    """

    ENEMY_KILLED = auto()       # data: {"enemy": Enemy, "reward": int}
    ENEMY_REACHED_END = auto()  # data: {"enemy": Enemy, "lives_lost": int}
    TOWER_PLACED = auto()       # data: {"tower": Tower, "position": (x, y)}
    TOWER_SOLD = auto()         # data: {"tower": Tower, "refund": int}
    WAVE_START = auto()         # data: {"wave_number": int}
    WAVE_COMPLETE = auto()      # data: {"wave_number": int}
    GAME_OVER = auto()          # data: {"score": int, "waves_survived": int}


class EventBus:
    """Simple publish/subscribe event dispatcher.

    Example::

        bus = EventBus()

        def on_kill(data):
            print(f"Enemy killed! Reward: {data['reward']}")

        bus.subscribe(EventType.ENEMY_KILLED, on_kill)
        bus.emit(EventType.ENEMY_KILLED, {"enemy": e, "reward": 10})
        bus.unsubscribe(EventType.ENEMY_KILLED, on_kill)

    Attributes:
        _subscribers: Mapping from EventType to list of callback functions.
    """

    def __init__(self) -> None:
        self._subscribers: Dict[EventType, List[Callable]] = defaultdict(list)

    def subscribe(self, event_type: EventType, callback: Callable[[Any], None]) -> None:
        """Register a callback for a specific event type.

        Args:
            event_type: The EventType to listen for.
            callback:   A callable that receives the event data dict.

        Side effects:
            Adds the callback to the subscriber list.
        """
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable[[Any], None]) -> None:
        """Remove a previously registered callback.

        Args:
            event_type: The EventType the callback was registered for.
            callback:   The exact callable to remove.

        Side effects:
            Removes the callback if found; silently does nothing otherwise.
        """
        try:
            self._subscribers[event_type].remove(callback)
        except ValueError:
            pass

    def emit(self, event_type: EventType, data: Any = None) -> None:
        """Dispatch an event to all subscribers.

        Args:
            event_type: The EventType being emitted.
            data:       Arbitrary data passed to each callback (typically a dict).

        Side effects:
            Calls every subscribed callback for this event type, in
            registration order.

        TODO: Add error handling so one failing callback doesn't block others.
        TODO: Consider async/queued event dispatch for performance-critical paths.
        """
        for callback in self._subscribers.get(event_type, []):
            callback(data)

    def clear(self) -> None:
        """Remove all subscribers. Useful for test teardown or game reset.

        Side effects:
            Empties all subscriber lists.
        """
        self._subscribers.clear()
