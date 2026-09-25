"""SQLite disk cache so repeated calls never re-hit rate-limited sources."""

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class DiskCache:
    def __init__(self, path: Path, ttl_days: float) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute("CREATE TABLE IF NOT EXISTS cache (k TEXT PRIMARY KEY, v TEXT, t REAL)")
        self._ttl = ttl_days * 86400

    @staticmethod
    def key(namespace: str, **params: Any) -> str:
        raw = json.dumps(params, sort_keys=True, ensure_ascii=False)
        return f"{namespace}:{hashlib.sha256(raw.encode()).hexdigest()}"

    def get(self, key: str) -> Any | None:
        row = self._db.execute("SELECT v, t FROM cache WHERE k = ?", (key,)).fetchone()
        if row is None or (self._ttl > 0 and time.time() - row[1] > self._ttl):
            return None
        return json.loads(row[0])

    def set(self, key: str, value: Any) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO cache (k, v, t) VALUES (?, ?, ?)",
            (key, json.dumps(value, ensure_ascii=False), time.time()),
        )
        self._db.commit()

    def close(self) -> None:
        self._db.close()
