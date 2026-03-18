"""
Tower Defense Game Engine
=========================

A modular, extensible framework for building tower defense games using only
the Python standard library. This package provides core systems that can be
composed to create a complete tower defense game.

Modules:
    track       — Path/waypoint system for enemy movement routes
    enemies     — Enemy types, health, and movement along tracks
    towers      — Tower placement, targeting, and firing logic
    waves       — Wave definitions and spawn scheduling
    game_state  — Central game state management and update loop
    projectiles — Projectile movement and damage application
    effects     — Status effects (slow, burn, armor reduction)
    events      — Pub/sub event bus for decoupled communication
    grid        — Grid-based map with terrain types and buildability
"""

from engine.events import EventBus
from engine.grid import Grid
from engine.track import Track, Waypoint
from engine.game_state import GameState

__all__ = [
    "EventBus",
    "Grid",
    "Track",
    "Waypoint",
    "GameState",
]
