"""Count failed password attempts per client and pause clients that fail too often."""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable


class FailureThrottle:
    """Allow ``limit`` failures per client within ``window`` seconds.

    A client that reaches the limit is refused until its oldest failure is
    ``window`` seconds old. State lives in memory, like the job store, so it
    covers one API process and resets on restart.
    """

    def __init__(
        self,
        *,
        limit: int,
        window: float,
        clock: Callable[[], float] = time.monotonic,
        max_clients: int = 10_000,
    ) -> None:
        """Track at most ``max_clients`` clients, forgetting idle ones and then the oldest."""
        self.limit = limit
        self.window = window
        self._clock = clock
        self._max_clients = max_clients
        self._failures: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def retry_after(self, client: str) -> int:
        """Whole seconds until ``client`` may try again, or 0 when it may try now."""
        with self._lock:
            now = self._clock()
            recent = self._recent(client, now)
            if len(recent) < self.limit:
                return 0
            return max(1, math.ceil(recent[0] + self.window - now))

    def record_failure(self, client: str) -> None:
        """Remember one failed attempt from ``client``."""
        with self._lock:
            now = self._clock()
            times = [*self._recent(client, now), now]
            # Re-inserting moves the client to the end, so the dict stays
            # ordered from least to most recently failed.
            self._failures.pop(client, None)
            self._failures[client] = times
            if len(self._failures) > self._max_clients:
                self._forget_idle(now)
                self._forget_oldest()

    def clear(self, client: str) -> None:
        """Forget ``client``'s failures after it proves it knows the password."""
        with self._lock:
            self._failures.pop(client, None)

    def _recent(self, client: str, now: float) -> list[float]:
        cutoff = now - self.window
        recent = [at for at in self._failures.get(client, []) if at > cutoff]
        if recent:
            self._failures[client] = recent
        else:
            self._failures.pop(client, None)
        return recent

    def _forget_idle(self, now: float) -> None:
        cutoff = now - self.window
        idle = [c for c, times in self._failures.items() if times[-1] <= cutoff]
        for client in idle:
            del self._failures[client]

    def _forget_oldest(self) -> None:
        # Many clients failing inside one window (rotating IPv6 addresses, say)
        # are not idle, so drop the least recently failed to keep a hard cap.
        while len(self._failures) > self._max_clients:
            del self._failures[next(iter(self._failures))]
