"""
Path / Track System
===================

Defines the routes that enemies follow from spawn to the player's base.
A Track is an ordered sequence of Waypoints; enemies interpolate their
position along this polyline based on a progress value (0.0 → 1.0).

Multiple tracks can coexist to support alternate lanes or branching paths.

How it fits in the engine:
    - Enemies hold a reference to a Track and a ``progress`` float.
    - Each frame, ``Enemy.move(dt)`` advances progress and queries the
      track for the world-space position via ``get_position_at_progress``.
    - The Grid module can auto-generate tracks from PATH cells, or tracks
      can be hand-authored as a list of Waypoints.

Example::

    track = Track(name="main")
    track.add_waypoint(Waypoint(0, 5))
    track.add_waypoint(Waypoint(10, 5))
    track.add_waypoint(Waypoint(10, 0))

    pos = track.get_position_at_progress(0.5)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class Waypoint:
    """A single point on a track.

    Example::

        wp = Waypoint(3.0, 7.5)

    Attributes:
        x: Horizontal coordinate.
        y: Vertical coordinate.
    """

    x: float
    y: float


class Track:
    """An ordered polyline path that enemies follow.

    Example::

        track = Track(name="left_lane")
        track.add_waypoint(Waypoint(0, 0))
        track.add_waypoint(Waypoint(5, 0))
        track.add_waypoint(Waypoint(5, 5))
        length = track.total_length()
        mid = track.get_position_at_progress(0.5)

    Attributes:
        name:      Human-readable identifier for this track.
        waypoints: Ordered list of Waypoint objects.
    """

    def __init__(self, name: str = "default") -> None:
        self.name: str = name
        self.waypoints: List[Waypoint] = []
        self._segment_lengths: List[float] = []
        self._total_length: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_waypoint(self, wp: Waypoint) -> None:
        """Append a waypoint to the end of the track and recompute lengths.

        Args:
            wp: The Waypoint to append.

        Side effects:
            Recalculates cached segment lengths and total length.
        """
        self.waypoints.append(wp)
        self._recompute_lengths()

    def get_path(self) -> List[Waypoint]:
        """Return the full ordered list of waypoints.

        Returns:
            A shallow copy of the waypoints list.
        """
        return list(self.waypoints)

    def total_length(self) -> float:
        """Return the total Euclidean length of the polyline.

        Returns:
            Sum of all segment lengths (float).
        """
        return self._total_length

    def get_position_at_progress(self, progress: float) -> Tuple[float, float]:
        """Interpolate a world-space (x, y) position along the track.

        Args:
            progress: A value in [0.0, 1.0] where 0.0 is the first waypoint
                      and 1.0 is the last.

        Returns:
            A (x, y) tuple of the interpolated position.

        Raises:
            ValueError: If there are fewer than 2 waypoints.
        """
        if len(self.waypoints) < 2:
            raise ValueError("Track needs at least 2 waypoints to interpolate.")

        progress = max(0.0, min(1.0, progress))

        if progress == 0.0:
            wp = self.waypoints[0]
            return (wp.x, wp.y)
        if progress == 1.0:
            wp = self.waypoints[-1]
            return (wp.x, wp.y)

        target_dist = progress * self._total_length
        accumulated = 0.0

        for i, seg_len in enumerate(self._segment_lengths):
            if accumulated + seg_len >= target_dist:
                # Interpolate within this segment
                remainder = target_dist - accumulated
                t = remainder / seg_len if seg_len > 0 else 0.0
                a = self.waypoints[i]
                b = self.waypoints[i + 1]
                return (
                    a.x + (b.x - a.x) * t,
                    a.y + (b.y - a.y) * t,
                )
            accumulated += seg_len

        # Fallback: return last waypoint
        wp = self.waypoints[-1]
        return (wp.x, wp.y)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _recompute_lengths(self) -> None:
        """Recalculate segment lengths after waypoints change."""
        self._segment_lengths = []
        self._total_length = 0.0
        for i in range(len(self.waypoints) - 1):
            a = self.waypoints[i]
            b = self.waypoints[i + 1]
            length = math.hypot(b.x - a.x, b.y - a.y)
            self._segment_lengths.append(length)
            self._total_length += length


class TrackManager:
    """Container for multiple tracks / lanes.

    Example::

        tm = TrackManager()
        tm.add_track(main_track)
        tm.add_track(flank_track)
        t = tm.get_track("main")

    Attributes:
        tracks: Dict mapping track names to Track objects.
    """

    def __init__(self) -> None:
        self.tracks: dict[str, Track] = {}

    def add_track(self, track: Track) -> None:
        """Register a track by name.

        Args:
            track: The Track instance to register.
        """
        self.tracks[track.name] = track

    def get_track(self, name: str) -> Track | None:
        """Retrieve a track by name.

        Args:
            name: The track name.

        Returns:
            The Track, or None if not found.
        """
        return self.tracks.get(name)

    def all_tracks(self) -> list[Track]:
        """Return all registered tracks.

        Returns:
            List of Track objects.
        """
        return list(self.tracks.values())
