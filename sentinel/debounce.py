"""Anti faux positifs commun a la vision et aux capteurs."""

from __future__ import annotations


class Debouncer:
    """Une condition doit etre vraie N fois de suite avant de declencher, puis delai entre deux alertes."""

    def __init__(self, required: int = 5, cooldown_seconds: float = 10.0):
        self.required = required
        self.cooldown_seconds = cooldown_seconds
        self._count = 0
        self._last_fired = float("-inf")

    def update(self, condition: bool, now: float) -> bool:
        if not condition:
            self._count = 0
            return False
        self._count += 1
        if self._count < self.required or now - self._last_fired < self.cooldown_seconds:
            return False
        self._last_fired = now
        return True

    @property
    def active(self) -> bool:
        return self._count >= self.required
