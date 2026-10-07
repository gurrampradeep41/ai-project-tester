"""
Deterministic requirement scoring and release gate.
"""


def calculate_requirement_score(
    traceability
):
    if not isinstance(
        traceability,
        dict,
    ):
        return {
            "score": 0,
            "status": "FAIL",
            "total": 0,
            "pass": 0,
            "partial": 0,
            "fail": 0,
            "not_verified": 0,
            "critical_failures": [],
        }

    matrix = traceability.get(
        "matrix",
        [],
    )

    total = len(matrix)

    passed = sum(
        1
        for item in matrix
        if item.get("status") == "PASS"
    )

    partial = sum(
        1
        for item in matrix
        if item.get("status") == "PARTIAL"
    )

    failed = sum(
        1
        for item in matrix
        if item.get("status") == "FAIL"
    )

    not_verified = sum(
        1
        for item in matrix
        if item.get("status")
        == "NOT_VERIFIED"
    )

    if total:

        score = (
            (
                passed
                + partial * 0.5
            )
            / total
        ) * 100

    else:

        score = 0

    # --------------------------------------------------------
    # CRITICAL FAILURES
    # --------------------------------------------------------

    critical_failures = []

    for item in matrix:

        status = str(
            item.get(
                "status",
                "",
            )
        ).upper()

        priority = str(
            item.get(
                "priority",
                "",
            )
        ).upper()

        requirement_type = str(
            item.get(
                "type",
                "",
            )
        ).upper()

        if (
            status == "FAIL"
            and (
                priority == "HIGH"
                or requirement_type == "SECURITY"
            )
        ):

            critical_failures.append(
                {
                    "id": item.get(
                        "id"
                    ),

                    "requirement": item.get(
                        "requirement"
                    ),

                    "priority": priority,

                    "type": requirement_type,

                    "status": status,
                }
            )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    if score >= 90:
        status = "PASS"

    elif score >= 70:
        status = "PARTIAL"

    else:
        status = "FAIL"

    return {
        "score": round(
            score,
            2,
        ),

        "status": status,

        "total": total,

        "pass": passed,

        "partial": partial,

        "fail": failed,

        "not_verified": not_verified,

        "critical_failures": critical_failures,
    }


def requirement_release_gate(
    requirement_score
):
    """
    Requirement-specific release gate.

    PASS:
        >= 90% coverage and no critical failures.

    CONDITIONAL:
        >= 70% coverage and no critical failures.

    BLOCKED:
        Critical/high-priority failure
        OR coverage below 70%.
    """

    if not isinstance(
        requirement_score,
        dict,
    ):
        return {
            "status": "BLOCKED",
            "reason": "Requirement score unavailable.",
        }

    critical_failures = (
        requirement_score.get(
            "critical_failures",
            [],
        )
    )

    score = float(
        requirement_score.get(
            "score",
            0,
        )
    )

    if critical_failures:

        return {
            "status": "BLOCKED",

            "reason": (
                "One or more high-priority "
                "or security requirements failed."
            ),
        }

    if score < 70:

        return {
            "status": "BLOCKED",

            "reason": (
                "Requirement coverage is below "
                "the minimum release threshold."
            ),
        }

    if score < 90:

        return {
            "status": "CONDITIONAL",

            "reason": (
                "Requirement coverage is acceptable "
                "but additional verification is required."
            ),
        }

    return {
        "status": "PASS",

        "reason": (
            "Requirement coverage meets the "
            "release threshold."
        ),
    }