# core/release_gate.py

from __future__ import annotations

from typing import Any


def _status(result: dict[str, Any], default: str = "UNKNOWN") -> str:
    return str(
        result.get("status", default)
    ).upper()


def calculate_phase7_release_gate(
    production: dict[str, Any],
) -> dict[str, Any]:

    score = float(
        production.get("score", 0)
    )

    risk = str(
        production.get("risk", "UNKNOWN")
    ).upper()

    critical_failures = production.get(
        "critical_failures",
        0,
    )

    high_failures = production.get(
        "high_failures",
        0,
    )

    reasons = []

    # ---------------------------------------------------------
    # HARD BLOCKS
    # ---------------------------------------------------------

    if critical_failures > 0:

        reasons.append(
            "Critical production-readiness failure detected."
        )

        return {
            "status": "BLOCKED",
            "score": score,
            "risk": risk,
            "reasons": reasons,
        }

    if risk == "CRITICAL":

        reasons.append(
            "Production readiness risk is CRITICAL."
        )

        return {
            "status": "BLOCKED",
            "score": score,
            "risk": risk,
            "reasons": reasons,
        }

    # ---------------------------------------------------------
    # HIGH-RISK CONDITIONS
    # ---------------------------------------------------------

    if high_failures > 0:

        reasons.append(
            "High-severity production-readiness failures require remediation."
        )

        return {
            "status": "BLOCKED",
            "score": score,
            "risk": risk,
            "reasons": reasons,
        }

    # ---------------------------------------------------------
    # SCORE GATE
    # ---------------------------------------------------------

    if score < 60:

        reasons.append(
            f"Production readiness score is {score:.1f}/100, below the minimum release threshold."
        )

        return {
            "status": "BLOCKED",
            "score": score,
            "risk": risk,
            "reasons": reasons,
        }

    if score < 85:

        reasons.append(
            f"Production readiness score is {score:.1f}/100."
        )

        reasons.append(
            "Production deployment requires remediation or explicit approval."
        )

        return {
            "status": "CONDITIONAL",
            "score": score,
            "risk": risk,
            "reasons": reasons,
        }

    return {
        "status": "PASS",
        "score": score,
        "risk": risk,
        "reasons": [
            "Production-readiness checks passed the release threshold."
        ],
    }


def combine_release_gates(
    existing_gate: dict[str, Any],
    requirement_gate: dict[str, Any],
    ai_gate: dict[str, Any] | None,
    production_gate: dict[str, Any],
) -> dict[str, Any]:

    gates = {
        "overall": existing_gate,
        "requirements": requirement_gate,
        "ai": ai_gate or {
            "status": "NOT_ASSESSED"
        },
        "production": production_gate,
    }

    reasons = []

    statuses = []

    for name, gate in gates.items():

        status = _status(gate)

        statuses.append(status)

        if status in {
            "BLOCKED",
            "FAIL",
        }:

            reasons.extend(
                [
                    f"{name.title()} gate: {reason}"
                    for reason in gate.get(
                        "reasons",
                        [],
                    )
                ]
            )

    # ---------------------------------------------------------
    # HARD BLOCK
    # ---------------------------------------------------------

    if any(
        status in {
            "BLOCKED",
            "FAIL",
        }
        for status in statuses
    ):

        return {
            "status": "BLOCKED",
            "reasons": reasons,
            "gates": gates,
        }

    # ---------------------------------------------------------
    # CONDITIONAL
    # ---------------------------------------------------------

    if any(
        status in {
            "CONDITIONAL",
            "WARNING",
            "NOT_ASSESSED",
        }
        for status in statuses
    ):

        reasons.extend(
            [
                f"{name.title()} gate requires attention."
                for name, gate in gates.items()
                if _status(gate) in {
                    "CONDITIONAL",
                    "WARNING",
                    "NOT_ASSESSED",
                }
            ]
        )

        return {
            "status": "CONDITIONAL",
            "reasons": reasons,
            "gates": gates,
        }

    # ---------------------------------------------------------
    # READY
    # ---------------------------------------------------------

    return {
        "status": "READY",
        "reasons": [
            "All assessed release gates passed."
        ],
        "gates": gates,
    }