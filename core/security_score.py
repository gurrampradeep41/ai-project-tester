"""
Deterministic security scoring.

Missing scanners are NOT treated as clean.

Security score consists of:
- Finding deductions
- Scanner coverage penalty
- Scanner error penalty
"""

TOTAL_SECURITY_TOOLS = 5


def _safe_count(counts, key):
    try:
        return max(
            0,
            int(
                counts.get(
                    key,
                    0,
                )
            ),
        )
    except (
        TypeError,
        ValueError,
        AttributeError,
    ):
        return 0


def calculate_security_score(
    security_result
):
    """
    Calculate deterministic security score.
    """

    if not isinstance(
        security_result,
        dict,
    ):
        return {
            "score": 0,
            "risk": "UNKNOWN",
            "status": "NOT_ASSESSED",
            "counts": {},
            "coverage": {
                "assessed_tools": [],
                "not_assessed_tools": [],
                "assessed_count": 0,
                "total_tools": TOTAL_SECURITY_TOOLS,
                "coverage_percent": 0,
            },
            "total_findings": 0,
            "deductions": {
                "finding_deduction": 0,
                "coverage_penalty": 0,
                "scanner_error_penalty": 0,
            },
        }

    if not security_result.get(
        "enabled",
        True,
    ):
        return {
            "score": 0,
            "risk": "UNKNOWN",
            "status": "DISABLED",
            "counts": {},
            "coverage": {
                "assessed_tools": [],
                "not_assessed_tools": [],
                "assessed_count": 0,
                "total_tools": TOTAL_SECURITY_TOOLS,
                "coverage_percent": 0,
            },
            "total_findings": 0,
            "deductions": {
                "finding_deduction": 0,
                "coverage_penalty": 0,
                "scanner_error_penalty": 0,
            },
        }

    counts = security_result.get(
        "counts",
        {},
    )

    assessed_tools = security_result.get(
        "assessed_tools",
        [],
    )

    not_assessed_tools = security_result.get(
        "not_assessed_tools",
        [],
    )

    bandit_count = _safe_count(
        counts,
        "bandit",
    )

    semgrep_count = _safe_count(
        counts,
        "semgrep",
    )

    gitleaks_count = _safe_count(
        counts,
        "gitleaks",
    )

    dependency_count = _safe_count(
        counts,
        "dependency_vulnerabilities",
    )

    heuristic_count = _safe_count(
        counts,
        "secret_heuristics",
    )

    # -----------------------------------------------------
    # FINDING DEDUCTIONS
    # -----------------------------------------------------

    gitleaks_deduction = min(
        gitleaks_count * 30,
        60,
    )

    dependency_deduction = min(
        dependency_count * 10,
        40,
    )

    bandit_deduction = min(
        bandit_count * 5,
        25,
    )

    semgrep_deduction = min(
        semgrep_count * 5,
        25,
    )

    heuristic_deduction = min(
        heuristic_count * 2,
        10,
    )

    finding_deduction = (
        gitleaks_deduction
        + dependency_deduction
        + bandit_deduction
        + semgrep_deduction
        + heuristic_deduction
    )

    # -----------------------------------------------------
    # COVERAGE
    # -----------------------------------------------------

    assessed_count = len(
        assessed_tools
    )

    coverage_percent = round(
        (
            assessed_count
            / TOTAL_SECURITY_TOOLS
        )
        * 100
    )

    missing_count = len(
        not_assessed_tools
    )

    coverage_penalty = min(
        missing_count * 10,
        40,
    )

    # -----------------------------------------------------
    # SCANNER ERRORS
    # -----------------------------------------------------

    tools = security_result.get(
        "tools",
        {},
    )

    scanner_error_count = sum(
        1
        for result in tools.values()
        if isinstance(result, dict)
        and result.get("status")
        in {
            "ERROR",
            "TIMEOUT",
        }
    )

    scanner_error_penalty = min(
        scanner_error_count * 10,
        30,
    )

    # -----------------------------------------------------
    # FINAL SCORE
    # -----------------------------------------------------

    score = max(
        0,
        100
        - finding_deduction
        - coverage_penalty
        - scanner_error_penalty,
    )

    # -----------------------------------------------------
    # STATUS
    # -----------------------------------------------------

    if assessed_count == 0:
        status = "NOT_ASSESSED"

    elif (
        coverage_percent < 100
        or scanner_error_count > 0
    ):
        status = "PARTIAL"

    else:
        status = "ASSESSED"

    # -----------------------------------------------------
    # RISK
    # -----------------------------------------------------

    existing_risk = str(
        security_result.get(
            "risk",
            "UNKNOWN",
        )
    ).upper()

    if gitleaks_count > 0:
        risk = "CRITICAL"

    elif dependency_count > 0:
        risk = "HIGH"

    elif (
        bandit_count > 0
        or semgrep_count > 0
    ):
        risk = "MEDIUM"

    elif heuristic_count > 0:
        risk = "LOW"

    elif (
        assessed_count == 0
        or missing_count > 0
        or scanner_error_count > 0
    ):
        risk = "UNKNOWN"

    else:
        risk = existing_risk or "LOW"

    return {
        "score": int(score),
        "risk": risk,
        "status": status,
        "counts": {
            "bandit": bandit_count,
            "semgrep": semgrep_count,
            "gitleaks": gitleaks_count,
            "dependency_vulnerabilities": dependency_count,
            "secret_heuristics": heuristic_count,
        },
        "coverage": {
            "assessed_tools": assessed_tools,
            "not_assessed_tools": not_assessed_tools,
            "assessed_count": assessed_count,
            "total_tools": TOTAL_SECURITY_TOOLS,
            "coverage_percent": coverage_percent,
        },
        "total_findings": (
            bandit_count
            + semgrep_count
            + gitleaks_count
            + dependency_count
            + heuristic_count
        ),
        "deductions": {
            "finding_deduction": finding_deduction,
            "coverage_penalty": coverage_penalty,
            "scanner_error_penalty": scanner_error_penalty,
        },
    }


def security_release_gate(
    security_result
):
    """
    Security-only release gate.
    """

    if not isinstance(
        security_result,
        dict,
    ):
        return "CONDITIONAL"

    risk = str(
        security_result.get(
            "risk",
            "UNKNOWN",
        )
    ).upper()

    if risk in {
        "CRITICAL",
        "HIGH",
    }:
        return "BLOCKED"

    if risk == "UNKNOWN":
        return "CONDITIONAL"

    return "PASS"