"""Evite les faux declenchements : un geste doit etre tenu plusieurs images de suite."""

from __future__ import annotations

from .gestures import Gesture


class GestureStabilizer:
    def __init__(self, frames_required: int = 8, cooldown_seconds: float = 5.0):
        self.frames_required = frames_required
        self.cooldown_seconds = cooldown_seconds
        self._candidate: tuple[str, Gesture] | None = None
        self._count = 0
        self._last_fired: dict[str, float] = {}

    def update(self, agent: str | None, gesture: Gesture, now: float) -> Gesture | None:
        """Renvoie le geste valide une seule fois quand il est stable, sinon None."""
        if agent is None or gesture is Gesture.NONE:
            self._candidate, self._count = None, 0
            return None

        if self._candidate == (agent, gesture):
            self._count += 1
        else:
            self._candidate, self._count = (agent, gesture), 1

        if self._count < self.frames_required:
            return None
        if now - self._last_fired.get(agent, float("-inf")) < self.cooldown_seconds:
            return None

        self._last_fired[agent] = now
        self._candidate, self._count = None, 0
        return gesture

    def progress(self) -> float:
        """Avancement 0..1 du geste en cours (pour l'affichage)."""
        return min(1.0, self._count / self.frames_required)
