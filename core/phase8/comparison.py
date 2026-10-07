# core/phase8/comparison.py

from __future__ import annotations

from typing import Any


def compare_audits(
    old_audit: dict[str, Any],
    new_audit: dict[str, Any],
) -> dict[str, Any]:

    old = old_audit.get(
        "result",
        {}
    )

    new = new_audit.get(
        "result",
        {}
    )

    old_final = old.get(
        "final_score",
        {}
    )

    new_final = new.get(
        "final_score",
        {}
    )

    old_security = old.get(
        "security",
        {}
    )

    new_security = new.get(
        "security",
        {}
    )

    old_testing = old.get(
        "testing",
        {}
    )

    new_testing = new.get(
        "testing",
        {}
    )

    old_requirements = old.get(
        "requirement_score",
        {}
    )

    new_requirements = new.get(
        "requirement_score",
        {}
    )

    old_ai = old.get(
        "ai",
        {}
    )

    new_ai = new.get(
        "ai",
        {}
    )

    old_production = old.get(
        "production_readiness",
        {}
    )

    new_production = new.get(
        "production_readiness",
        {}
    )

    def score(obj):

        return float(
            obj.get(
                "score",
                0,
            )
            or 0
        )

    return {
        "old_audit_id": old_audit.get(
            "audit_id"
        ),

        "new_audit_id": new_audit.get(
            "audit_id"
        ),

        "changes": {

            "final_score": (
                score(new_final)
                - score(old_final)
            ),

            "security": (
                score(new_security)
                - score(old_security)
            ),

            "testing": (
                score(new_testing)
                - score(old_testing)
            ),

            "requirements": (
                score(new_requirements)
                - score(old_requirements)
            ),

            "ai": (
                score(new_ai)
                - score(old_ai)
            ),

            "production": (
                score(new_production)
                - score(old_production)
            ),
        },

        "release_status": {
            "old": old.get(
                "release_gate",
                {}
            ).get(
                "status",
                "UNKNOWN",
            ),

            "new": new.get(
                "release_gate",
                {}
            ).get(
                "status",
                "UNKNOWN",
            ),
        },
    }