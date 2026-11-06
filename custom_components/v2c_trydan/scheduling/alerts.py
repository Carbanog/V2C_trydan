"""Debounce one actionable alert per unresolved command incident."""

from dataclasses import dataclass

UNCONFIRMED_ALERT_DELAY = 60


@dataclass
class CommandAlert:
    """Use a monotonic clock; wall-clock edits must not create alert storms."""

    started: float | None = None
    active: bool = False

    def update(self, unresolved: bool, now: float) -> bool | None:
        """Return True to create, False to clear, or None for no UI operation."""
        if unresolved:
            if self.started is None:
                self.started = now
            if not self.active and now - self.started >= UNCONFIRMED_ALERT_DELAY:
                self.active = True
                return True
        else:
            self.started = None
            if self.active:
                self.active = False
                return False
        return None
