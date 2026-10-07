# core/phase8/audit_history.py

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .database import (
    initialize_database,
    insert_audit,
    insert_remediation_items,
    get_audit_history,
    get_audit,
)


def generate_audit_id() -> str:

    timestamp = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%d%H%M%S"
    )

    random_part = uuid.uuid4().hex[:8].upper()

    return f"AUD-{timestamp}-{random_part}"


def calculate_project_hash(
    project_dir: str | Path,
) -> str:

    project_dir = Path(
        project_dir
    )

    hasher = hashlib.sha256()

    files = sorted(
        [
            path
            for path in project_dir.rglob("*")
            if path.is_file()
        ],
        key=lambda p: str(p),
    )

    for path in files:

        try:

            relative = str(
                path.relative_to(
                    project_dir
                )
            )

            hasher.update(
                relative.encode(
                    "utf-8"
                )
            )

            hasher.update(
                path.read_bytes()
            )

        except Exception:

            continue

    return hasher.hexdigest()


def save_audit(
    project_name: str,
    project_dir: str | Path,
    result: dict[str, Any],
) -> str:

    initialize_database()

    audit_id = generate_audit_id()

    project_hash = calculate_project_hash(
        project_dir
    )

    created_at = datetime.now(
        timezone.utc
    ).isoformat()

    insert_audit(
        audit_id=audit_id,
        project_name=project_name,
        project_hash=project_hash,
        created_at=created_at,
        result=result,
    )

    remediation_items = result.get(
        "remediation_plan",
        [],
    )

    insert_remediation_items(
        audit_id=audit_id,
        items=remediation_items,
        created_at=created_at,
    )

    return audit_id