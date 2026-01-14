from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Any

API_DIR = Path(__file__).resolve().parents[1]  # api/
DB_PATH = API_DIR / "storage" / "app.db"

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id TEXT NOT NULL,           -- request의 image_id(파일명 등)
            path TEXT NOT NULL,               -- 로컬 저장 경로
            sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL,
            image_ref_id INTEGER NOT NULL,    -- images.id FK
            risk_level TEXT NOT NULL,         -- "high" | "normal"
            objects_json TEXT NOT NULL,       -- DetectedObject list
            caption TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(image_ref_id) REFERENCES images(id)
        );
        """)
        conn.commit()

def insert_image(image_id: str, path: str, sha256: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO images(image_id, path, sha256) VALUES (?, ?, ?)",
            (image_id, path, sha256),
        )
        conn.commit()
        return int(cur.lastrowid)

def insert_analysis(
    request_id: str,
    image_ref_id: int,
    risk_level: str,
    objects: list[dict[str, Any]],
    caption: str
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO analyses(request_id, image_ref_id, risk_level, objects_json, caption)
            VALUES (?, ?, ?, ?, ?)
            """,
            (request_id, image_ref_id, risk_level, json.dumps(objects, ensure_ascii=False), caption),
        )
        conn.commit()
        return int(cur.lastrowid)

def get_analysis(analysis_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("""
            SELECT
              a.id AS analysis_id,
              a.request_id AS request_id,
              a.risk_level AS risk_level,
              a.objects_json AS objects_json,
              a.caption AS caption,
              a.created_at AS created_at,
              i.image_id AS image_id,
              i.path AS image_path,
              i.sha256 AS image_sha256
            FROM analyses a
            JOIN images i ON i.id = a.image_ref_id
            WHERE a.id = ?
        """, (analysis_id,)).fetchone()

        if row is None:
            return None

        return {
            "analysis_id": row["analysis_id"],
            "request_id": row["request_id"],
            "risk_level": row["risk_level"],
            "objects": json.loads(row["objects_json"]),
            "caption": row["caption"],
            "created_at": row["created_at"],
            "image_id": row["image_id"],
            "image_path": row["image_path"],
            "image_sha256": row["image_sha256"],
        }
