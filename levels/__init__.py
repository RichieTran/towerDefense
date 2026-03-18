"""
Levels Package
==============

Each module in this package defines a single playable level. A level is a
plain Python module that exposes a ``create()`` function returning a fully
configured ``GameState`` ready to play.

This convention keeps level data separate from engine code and makes it easy
to add new levels — just drop in a new file that follows the pattern.

Usage::

    from levels import forest_clearing
    state, event_bus = forest_clearing.create()
    while not state.game_over:
        state.update(dt)

To create your own level, copy ``forest_clearing.py`` and modify:
    1. The grid layout  — shape the terrain
    2. The track path   — route the enemies
    3. The wave list    — choose enemy types, counts, pacing
    4. The starting resources — lives, gold
"""
