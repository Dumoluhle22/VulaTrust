"""Holds an uploaded file between the preview and the confirm step (issue 11).

The file is kept in memory under a random one-time token. Entries expire, the
number kept is capped, and a token works only once. If the server restarts the
preview is simply lost and the file has to be uploaded again.
"""
import secrets
import threading
import time


class PendingImports:
    def __init__(self, ttl_seconds: int = 1800, max_items: int = 10, clock=time.monotonic):
        self._ttl = ttl_seconds
        self._max_items = max_items
        self._clock = clock
        self._items: dict[str, tuple[float, str, bytes]] = {}
        self._lock = threading.Lock()

    def _prune(self) -> None:
        now = self._clock()
        for token in [t for t, (stored, _n, _d) in self._items.items() if now - stored > self._ttl]:
            del self._items[token]

    def put(self, filename: str, data: bytes) -> str:
        with self._lock:
            self._prune()
            token = secrets.token_urlsafe(24)
            self._items[token] = (self._clock(), filename, data)
            while len(self._items) > self._max_items:
                del self._items[next(iter(self._items))]  # drop the oldest
            return token

    def take(self, token: str) -> tuple[str, bytes] | None:
        """Return (filename, data) once, then forget it."""
        with self._lock:
            self._prune()
            item = self._items.pop(token, None)
        return None if item is None else (item[1], item[2])


pending_imports = PendingImports()
