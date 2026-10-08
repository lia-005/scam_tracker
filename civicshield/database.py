import json
import sqlite3
from datetime import datetime

from . import config


class Database:
    def __init__(self, path: str | None = None):
        self.path = path or config.DB_PATH
        with self._conn() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS analyses(
                id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, kind TEXT,
                input_preview TEXT, risk_score INTEGER, verdict TEXT, result_json TEXT)""")

    def _conn(self):
        return sqlite3.connect(self.path)

    def save(self, kind: str, preview: str, result: dict, risk_score=None, verdict=None):
        with self._conn() as c:
            c.execute("INSERT INTO analyses(created_at,kind,input_preview,risk_score,verdict,result_json) VALUES (?,?,?,?,?,?)",
                      (datetime.now().isoformat(timespec="seconds"), kind, preview[:200], risk_score, verdict,
                       json.dumps(result, ensure_ascii=False)))

    def recent(self, limit: int = 25) -> list[dict]:
        with self._conn() as c:
            rows = c.execute("SELECT id,created_at,kind,input_preview,risk_score,verdict FROM analyses ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(zip(("id", "time", "type", "input", "risk", "verdict"), r)) for r in rows]

    def clear(self):
        with self._conn() as c:
            c.execute("DELETE FROM analyses")
