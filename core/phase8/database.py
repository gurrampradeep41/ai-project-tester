# core/phase8/database.py

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"

DB_PATH = DATA_DIR / "audits.db"


def get_connection() -> sqlite3.Connection:

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        DB_PATH,
        check_same_thread=False,
    )

    connection.row_factory = sqlite3.Row

    return connection


def initialize_database() -> None:

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS audits (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            audit_id TEXT UNIQUE NOT NULL,

            project_name TEXT,

            project_hash TEXT,

            created_at TEXT NOT NULL,

            final_score REAL,

            release_status TEXT,

            security_score REAL,

            testing_score REAL,

            requirement_score REAL,

            ai_score REAL,

            production_score REAL,

            risk TEXT,

            critical_findings INTEGER DEFAULT 0,

            high_findings INTEGER DEFAULT 0,

            warning_count INTEGER DEFAULT 0,

            result_json TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS remediation_items (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            audit_id TEXT NOT NULL,

            finding_id TEXT,

            source TEXT,

            priority TEXT,

            title TEXT,

            problem TEXT,

            action TEXT,

            status TEXT DEFAULT 'OPEN',

            created_at TEXT NOT NULL,

            FOREIGN KEY(audit_id)
                REFERENCES audits(audit_id)
        )
        """
    )

    connection.commit()

    connection.close()


def insert_audit(
    audit_id: str,
    project_name: str,
    project_hash: str,
    created_at: str,
    result: dict[str, Any],
) -> None:

    connection = get_connection()

    cursor = connection.cursor()

    final_score = result.get(
        "final_score",
        {},
    )

    security = result.get(
        "security",
        {},
    )

    testing = result.get(
        "testing",
        {},
    )

    requirement_score = result.get(
        "requirement_score",
        {},
    )

    ai = result.get(
        "ai",
        {},
    )

    production = result.get(
        "production_readiness",
        {},
    )

    release_gate = result.get(
        "release_gate",
        {},
    )

    cursor.execute(
        """
        INSERT OR REPLACE INTO audits (

            audit_id,
            project_name,
            project_hash,
            created_at,
            final_score,
            release_status,
            security_score,
            testing_score,
            requirement_score,
            ai_score,
            production_score,
            risk,
            critical_findings,
            high_findings,
            warning_count,
            result_json

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            audit_id,
            project_name,
            project_hash,
            created_at,

            float(
                final_score.get(
                    "score",
                    0,
                )
                or 0
            ),

            release_gate.get(
                "status",
                "UNKNOWN",
            ),

            float(
                security.get(
                    "score",
                    0,
                )
                or 0
            ),

            float(
                testing.get(
                    "score",
                    0,
                )
                or 0
            ),

            float(
                requirement_score.get(
                    "score",
                    0,
                )
                or 0
            ),

            float(
                ai.get(
                    "score",
                    0,
                )
                or 0
            ),

            float(
                production.get(
                    "score",
                    0,
                )
                or 0
            ),

            release_gate.get(
                "risk",
                production.get(
                    "risk",
                    "UNKNOWN",
                ),
            ),

            int(
                production.get(
                    "critical_failures",
                    0,
                )
                or 0
            ),

            int(
                production.get(
                    "high_failures",
                    0,
                )
                or 0
            ),

            int(
                production.get(
                    "warning_count",
                    0,
                )
                or 0
            ),

            json.dumps(
                result,
                ensure_ascii=False,
                default=str,
            ),
        ),
    )

    connection.commit()

    connection.close()


def insert_remediation_items(
    audit_id: str,
    items: list[dict[str, Any]],
    created_at: str,
) -> None:

    connection = get_connection()

    cursor = connection.cursor()

    for item in items:

        cursor.execute(
            """
            INSERT INTO remediation_items (

                audit_id,
                finding_id,
                source,
                priority,
                title,
                problem,
                action,
                status,
                created_at

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audit_id,
                item.get(
                    "id",
                    "",
                ),
                item.get(
                    "source",
                    "",
                ),
                item.get(
                    "priority",
                    "MEDIUM",
                ),
                item.get(
                    "title",
                    "",
                ),
                item.get(
                    "problem",
                    "",
                ),
                item.get(
                    "action",
                    "",
                ),
                item.get(
                    "status",
                    "OPEN",
                ),
                created_at,
            ),
        )

    connection.commit()

    connection.close()


def get_audit_history(
    limit: int = 50,
) -> list[dict[str, Any]]:

    connection = get_connection()

    cursor = connection.cursor()

    rows = cursor.execute(
        """
        SELECT
            audit_id,
            project_name,
            created_at,
            final_score,
            release_status,
            security_score,
            testing_score,
            requirement_score,
            ai_score,
            production_score,
            risk,
            critical_findings,
            high_findings,
            warning_count
        FROM audits
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (
            limit,
        ),
    ).fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


def get_audit(
    audit_id: str,
) -> dict[str, Any] | None:

    connection = get_connection()

    cursor = connection.cursor()

    row = cursor.execute(
        """
        SELECT *
        FROM audits
        WHERE audit_id = ?
        """,
        (
            audit_id,
        ),
    ).fetchone()

    connection.close()

    if row is None:
        return None

    result = dict(row)

    try:

        result["result"] = json.loads(
            result.pop(
                "result_json"
            )
        )

    except Exception:

        result["result"] = {}

    return result