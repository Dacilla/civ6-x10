"""Read-only access to the official runtime database (clean-room source)."""
from __future__ import annotations

import sqlite3
from pathlib import Path


class OfficialDb:
    """Read-only wrapper; refuses to create or modify the database."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        if not self.path.is_file():
            raise FileNotFoundError(f"official DB not found: {self.path}")
        self.con = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        self.con.row_factory = sqlite3.Row

    def close(self):
        self.con.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        return [dict(r) for r in self.con.execute(sql, params)]

    def count(self, table: str) -> int:
        return self.con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
