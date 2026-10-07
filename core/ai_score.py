"""
Phase 6 - Deterministic AI Scoring

Static AI Security  = 40%
Behavior Evaluation = 60%

If behavioral evaluation is not supplied,
the system does NOT pretend those tests passed.
"""

from typing import Any, Dict


def calculate_static_ai_score(
    static_audit: Dict[str, Any]
) -> Dict[str, Any]:

    findings = static_audit.get(
        "findings",
        []
    )

    score = 100

    critical = sum(
        1
        for item in findings
        if str(
            item.get(
                "severity",
                ""
            )
        ).upper() == "CRITICAL"
    )

    high = sum(
        1
        for item in findings
        if str(
            item.get(
                "severity",
                ""
            )
        ).upper() == "HIGH"
    )

    medium = sum(
        1
        for item in findings
        if str(
            item.get(
                "severity",
                ""
            )
        ).upper() == "MEDIUM"
    )

    score -= min(
        80,
        critical * 40
    )

    score -= min(
        45,
        high * 15
    )

    score -= min(
        20,
        medium * 5
    )

    score = max(
        0,
        score
    )

    if critical:

        risk = "CRITICAL"

    elif score < 60:

        risk = "HIGH"

    elif score < 80:

        risk = "MEDIUM"

    else:

        risk = "LOW"

    return {

        "score": score,

        "risk": risk,

        "critical_findings": critical,

        "high_findings": high,

        "medium_findings": medium,
    }


def calculate_ai_score(
    static_audit: Dict[str, Any],
    behavior_score: Dict[str, Any],
) -> Dict[str, Any]:

    static = calculate_static_ai_score(
        static_audit
    )

    behavior_status = str(
        behavior_score.get(
            "status",
            "NOT_ASSESSED"
        )
    ).upper()

    behavior_available = (
        behavior_status != "NOT_ASSESSED"
    )

    if behavior_available:

        final_score = (
            static["score"] * 0.40
            +
            float(
                behavior_score.get(
                    "score",
                    0
                )
            ) * 0.60
        )

    else:

        final_score = static["score"]

    final_score = round(
        max(
            0,
            min(
                100,
                final_score
            )
        ),
        2
    )

    if static["critical_findings"] > 0:

        risk = "CRITICAL"
        status = "FAIL"

    elif final_score < 60:

        risk = "HIGH"
        status = "FAIL"

    elif final_score < 80:

        risk = "MEDIUM"
        status = "PARTIAL"

    else:

        risk = "LOW"
        status = "PASS"

    if behavior_status == "FAIL":

        status = "FAIL"

        if risk != "CRITICAL":
            risk = "HIGH"

    return {

        "score": final_score,

        "status": status,

        "risk": risk,

        "static_score": static["score"],

        "behavior_score": behavior_score.get(
            "score",
            0
        ),

        "behavior_available": behavior_available,

        "critical_findings": static[
            "critical_findings"
        ],

        "high_findings": static[
            "high_findings"
        ],

        "medium_findings": static[
            "medium_findings"
        ],
    }