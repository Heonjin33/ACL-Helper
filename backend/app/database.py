from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any


def database_path() -> Path:
    default_path = Path(__file__).resolve().parents[1] / "data" / "acl_helper.sqlite3"
    return Path(os.getenv("DATABASE_PATH", str(default_path)))


def connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
      conn.execute(
          """
          CREATE TABLE IF NOT EXISTS reports (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              action_type TEXT NOT NULL,
              mode TEXT NOT NULL,
              overall_score INTEGER NOT NULL,
              summary_json TEXT NOT NULL,
              report_json TEXT NOT NULL,
              created_at TEXT NOT NULL
          )
          """
      )
      conn.commit()


def insert_report(
    *,
    action_type: str,
    mode: str,
    overall_score: int,
    summary: dict[str, Any],
    report: dict[str, Any],
    created_at: str,
) -> int:
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO reports (action_type, mode, overall_score, summary_json, report_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                action_type,
                mode,
                overall_score,
                json.dumps(summary, ensure_ascii=False),
                json.dumps(report, ensure_ascii=False),
                created_at,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def fetch_report(report_id: int) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
