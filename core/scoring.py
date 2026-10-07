"""
Deterministic final scoring and release-gate logic.

Architecture:
    Evidence
        ↓
    Component Scores
        ↓
    Final Score
        ↓
    Release Gate

Important:
    - LLM does NOT determine whether the application is secure.
    - LLM does NOT determine whether tests passed.
    - Requirement Traceability Matrix is the authoritative
      requirement verification layer.
    - Critical/high-priority requirement failures can block release.
"""


# ============================================================
# WEIGHTS
# ============================================================

REQUIREMENT_WEIGHT = 0.30
SECURITY_WEIGHT = 0.30
TESTING_WEIGHT = 0.25
AI_WEIGHT = 0.15


# ============================================================
# GENERIC SCORE HELPER
# ============================================================

def _score(data, default=0):
    """
    Safely extract a score from a dictionary.

    Priority:
        score
        coverage_score

    Result is always between 0 and 100.
    """

    if not isinstance(data, dict):
        return float(default)

    value = data.get("score")

    if value is None:
        value = data.get("coverage_score")

    try:
        return max(
            0.0,
            min(
                100.0,
                float(value),
            ),
        )

    except (
        TypeError,
        ValueError,
    ):
        return float(default)


# ============================================================
# REQUIREMENT SCORE
# ============================================================

def _requirement_component_score(
    requirements,
    requirement_score=None,
):
    """
    Determine the authoritative requirement score.

    Phase 5:
        requirement_score is preferred because it comes from
        the deterministic Requirement Traceability Matrix.

    Backward compatibility:
        If requirement_score is unavailable, fall back to
        the previous requirements object.
    """

    if isinstance(
        requirement_score,
        dict,
    ):
        return _score(
            requirement_score
        )

    return _score(
        requirements
    )


# ============================================================
# FINAL SCORE
# ============================================================

def calculate_final_score(
    project,
    requirements,
    security,
    testing,
    ai,
    requirement_score=None,
):
    """
    Calculate deterministic weighted final score.

    Weights:

        Requirements = 30%
        Security     = 30%
        Testing      = 25%
        AI Audit     = 15%

    Phase 5:
        Requirements score comes from the deterministic
        Requirement Traceability Matrix whenever available.

    The AI score contributes only 15%.
    It cannot override deterministic release gates.
    """

    # --------------------------------------------------------
    # REQUIREMENTS
    # --------------------------------------------------------

    requirement_component = (
        _requirement_component_score(
            requirements,
            requirement_score,
        )
    )

    # --------------------------------------------------------
    # SECURITY
    # --------------------------------------------------------

    security_component = _score(
        security
    )

    # --------------------------------------------------------
    # TESTING
    # --------------------------------------------------------

    testing_component = _score(
        testing
    )

    # --------------------------------------------------------
    # AI
    # --------------------------------------------------------

    ai_component = _score(
        ai
    )

    # --------------------------------------------------------
    # WEIGHTED SCORE
    # --------------------------------------------------------

    final_score = (
        requirement_component
        * REQUIREMENT_WEIGHT

        + security_component
        * SECURITY_WEIGHT

        + testing_component
        * TESTING_WEIGHT

        + ai_component
        * AI_WEIGHT
    )

    return {
        "score": round(
            final_score
        ),

        "weights": {
            "requirements": 30,
            "security": 30,
            "testing": 25,
            "ai": 15,
        },

        "component_scores": {
            "requirements": round(
                requirement_component
            ),

            "security": round(
                security_component
            ),

            "testing": round(
                testing_component
            ),

            "ai": round(
                ai_component
            ),
        },
    }


# ============================================================
# SECURITY CRITICAL CHECK
# ============================================================

def _security_is_critical(
    security
):
    """
    Return True when deterministic security evidence
    contains a CRITICAL finding.
    """

    if not isinstance(
        security,
        dict,
    ):
        return False

    # --------------------------------------------------------
    # SECURITY RISK
    # --------------------------------------------------------

    if str(
        security.get(
            "risk",
            "",
        )
    ).upper() == "CRITICAL":

        return True

    # --------------------------------------------------------
    # SECURITY FINDINGS
    # --------------------------------------------------------

    findings = security.get(
        "findings",
        [],
    )

    if not isinstance(
        findings,
        list,
    ):
        return False

    for finding in findings:

        if not isinstance(
            finding,
            dict,
        ):
            continue

        severity = str(
            finding.get(
                "severity",
                "",
            )
        ).upper()

        if severity == "CRITICAL":
            return True

    return False


# ============================================================
# AI CRITICAL FINDING CHECK
# ============================================================

def _ai_has_critical_finding(
    ai
):
    """
    Detect CRITICAL findings reported by AI.

    Note:
        AI findings are not treated as proof of a vulnerability.
        They are still surfaced as a release concern.
    """

    if not isinstance(
        ai,
        dict,
    ):
        return False

    findings = ai.get(
        "findings",
        [],
    )

    if not isinstance(
        findings,
        list,
    ):
        return False

    for finding in findings:

        if not isinstance(
            finding,
            dict,
        ):
            continue

        severity = str(
            finding.get(
                "severity",
                "",
            )
        ).upper()

        if severity == "CRITICAL":
            return True

    return False


# ============================================================
# REQUIREMENT CRITICAL FAILURE CHECK
# ============================================================

def requirement_gate_blocks_release(
    requirement_score
):
    """
    Determine whether requirement verification
    must block release.

    BLOCK if:

        1. A critical/high-priority requirement failed.

        OR

        2. A SECURITY requirement failed.

        OR

        3. Overall requirement status is FAIL.

    Important:
        PARTIAL and NOT_VERIFIED do not automatically mean
        BLOCKED unless the overall requirement score becomes FAIL
        or a critical/high-priority requirement has failed.
    """

    if not isinstance(
        requirement_score,
        dict,
    ):
        return True

    # --------------------------------------------------------
    # CRITICAL REQUIREMENT FAILURES
    # --------------------------------------------------------

    critical_failures = (
        requirement_score.get(
            "critical_failures",
            [],
        )
    )

    if critical_failures:
        return True

    # --------------------------------------------------------
    # OVERALL REQUIREMENT STATUS
    # --------------------------------------------------------

    status = str(
        requirement_score.get(
            "status",
            "",
        )
    ).upper()

    if status == "FAIL":
        return True

    return False


# ============================================================
# REQUIREMENT STATUS HELPERS
# ============================================================

def _requirement_has_not_verified(
    requirement_score
):
    """
    Check whether some requirements still lack verification.
    """

    if not isinstance(
        requirement_score,
        dict,
    ):
        return True

    return (
        int(
            requirement_score.get(
                "not_verified",
                0,
            )
        )
        > 0
    )


def _requirement_has_partial(
    requirement_score
):
    """
    Check whether some requirements are only partially verified.
    """

    if not isinstance(
        requirement_score,
        dict,
    ):
        return True

    return (
        int(
            requirement_score.get(
                "partial",
                0,
            )
        )
        > 0
    )


# ============================================================
# FINAL RELEASE GATE
# ============================================================

def calculate_release_gate(
    final_result,
    requirements,
    security,
    testing,
    ai,
    requirement_score=None,
):
    """
    Determine overall release readiness.

    ============================================================
    BLOCKED
    ============================================================

    Release is BLOCKED when:

        - Critical security issue
        - Critical AI finding
        - Failed/errored automated tests
        - Critical/high-priority requirement failure
        - Requirement score is FAIL

    ============================================================
    READY
    ============================================================

    READY requires:

        - Final score >= 80
        - Requirement score >= 80
        - Security score >= 80
        - Automated tests PASSED
        - Security risk is not UNKNOWN/HIGH/CRITICAL
        - AI audit available
        - No critical requirement failure

    ============================================================
    CONDITIONAL
    ============================================================

    Everything else that does not meet BLOCKED criteria.
    """

    # ========================================================
    # SCORES
    # ========================================================

    final_score = _score(
        final_result
    )

    requirement_component = (
        _requirement_component_score(
            requirements,
            requirement_score,
        )
    )

    security_score = _score(
        security
    )

    testing_score = _score(
        testing
    )

    # ========================================================
    # STATUS VALUES
    # ========================================================

    testing_status = str(
        testing.get(
            "status",
            "",
        )
        if isinstance(
            testing,
            dict,
        )
        else ""
    ).upper()

    security_risk = str(
        security.get(
            "risk",
            "",
        )
        if isinstance(
            security,
            dict,
        )
        else ""
    ).upper()

    security_status = str(
        security.get(
            "status",
            "",
        )
        if isinstance(
            security,
            dict,
        )
        else ""
    ).upper()

    requirement_status = str(
        requirement_score.get(
            "status",
            "",
        )
        if isinstance(
            requirement_score,
            dict,
        )
        else ""
    ).upper()

    ai_available = (
        isinstance(
            ai,
            dict,
        )
        and bool(ai)
        and ai.get(
            "status",
            "NOT_ASSESSED",
        )
        != "NOT_ASSESSED"
    )

    reasons = []

    # ========================================================
    # HARD BLOCK 1
    # CRITICAL SECURITY
    # ========================================================

    if _security_is_critical(
        security
    ):

        reasons.append(
            "Critical security finding detected."
        )

    # ========================================================
    # HARD BLOCK 2
    # CRITICAL AI FINDING
    # ========================================================

    if _ai_has_critical_finding(
        ai
    ):

        reasons.append(
            "Critical AI audit finding detected."
        )

    # ========================================================
    # HARD BLOCK 3
    # AUTOMATED TEST FAILURE
    # ========================================================

    if testing_status in {
        "FAILED",
        "BUILD_FAILED",
        "TIMEOUT",
        "ERROR",
    }:

        reasons.append(
            "Automated testing status is "
            f"{testing_status}."
        )

    # ========================================================
    # HARD BLOCK 4
    # REQUIREMENT FAILURE
    # ========================================================

    if requirement_gate_blocks_release(
        requirement_score
    ):

        if requirement_status == "FAIL":

            reasons.append(
                "Requirement coverage is below "
                "the minimum release threshold."
            )

        critical_failures = (
            requirement_score.get(
                "critical_failures",
                []
            )
            if isinstance(
                requirement_score,
                dict,
            )
            else []
        )

        if critical_failures:

            reasons.append(
                "One or more high-priority or "
                "security requirements failed."
            )

    # ========================================================
    # RETURN BLOCKED
    # ========================================================

    if reasons:

        return {
            "status": "BLOCKED",

            "score": round(
                final_score
            ),

            "reasons": reasons,

            "component_scores": {
                "requirements": round(
                    requirement_component
                ),

                "security": round(
                    security_score
                ),

                "testing": round(
                    testing_score
                ),

                "ai": _score(ai),
            },
        }

    # ========================================================
    # SECURITY ASSESSMENT
    # ========================================================

    if security_risk == "UNKNOWN":

        reasons.append(
            "Security assessment is incomplete."
        )

    if security_status in {
        "NOT_ASSESSED",
        "ERROR",
        "DISABLED",
    }:

        reasons.append(
            "Security scanning was not fully assessed."
        )

    # ========================================================
    # REQUIREMENT ASSESSMENT
    # ========================================================

    if _requirement_has_not_verified(
        requirement_score
    ):

        reasons.append(
            "One or more client requirements "
            "could not be fully verified."
        )

    if _requirement_has_partial(
        requirement_score
    ):

        reasons.append(
            "One or more client requirements "
            "are only partially verified."
        )

    if requirement_component < 80:

        reasons.append(
            "Requirement coverage is below "
            "the READY threshold."
        )

    # ========================================================
    # READY
    # ========================================================

    if (
        final_score >= 80

        and requirement_component >= 80

        and security_score >= 80

        and testing_status == "PASSED"

        and security_risk not in {
            "UNKNOWN",
            "CRITICAL",
            "HIGH",
        }

        and security_status not in {
            "NOT_ASSESSED",
            "ERROR",
            "DISABLED",
        }

        and requirement_status != "FAIL"

        and not _requirement_has_not_verified(
            requirement_score
        )

        and not _requirement_has_partial(
            requirement_score
        )

        and ai_available
    ):

        return {
            "status": "READY",

            "score": round(
                final_score
            ),

            "reasons": [
                "Release-readiness criteria satisfied."
            ],

            "component_scores": {
                "requirements": round(
                    requirement_component
                ),

                "security": round(
                    security_score
                ),

                "testing": round(
                    testing_score
                ),

                "ai": _score(ai),
            },
        }

    # ========================================================
    # CONDITIONAL
    # ========================================================

    if testing_status != "PASSED":

        reasons.append(
            "Automated testing has not passed."
        )

    if security_score < 80:

        reasons.append(
            "Security score is below "
            "the READY threshold."
        )

    if final_score < 80:

        reasons.append(
            "Overall score is below "
            "the READY threshold."
        )

    if not ai_available:

        reasons.append(
            "AI audit is unavailable or disabled."
        )

    if not reasons:

        reasons.append(
            "Additional validation is required "
            "before release."
        )

    # Remove duplicate reasons while preserving order.
    unique_reasons = list(
        dict.fromkeys(
            reasons
        )
    )

    return {
        "status": "CONDITIONAL",

        "score": round(
            final_score
        ),

        "reasons": unique_reasons,

        "component_scores": {
            "requirements": round(
                requirement_component
            ),

            "security": round(
                security_score
            ),

            "testing": round(
                testing_score
            ),

            "ai": _score(ai),
        },
    }


# ============================================================
# SECURITY-ONLY RELEASE GATE
# ============================================================

def security_release_gate(
    security
):
    """
    Backward-compatible security-only release gate.
    """

    if not isinstance(
        security,
        dict,
    ):
        return "CONDITIONAL"

    risk = str(
        security.get(
            "risk",
            "UNKNOWN",
        )
    ).upper()

    if risk == "CRITICAL":
        return "BLOCKED"

    if risk == "HIGH":
        return "BLOCKED"

    if risk == "UNKNOWN":
        return "CONDITIONAL"

    if risk in {
        "NOT_ASSESSED",
        "DISABLED",
    }:
        return "CONDITIONAL"

    return "PASS"


def calculate_ai_release_gate(
    ai_evaluation
):

    ai_score = ai_evaluation.get(
        "score",
        {}
    )

    score = ai_score.get(
        "score",
        0
    )

    risk = ai_score.get(
        "risk",
        "UNKNOWN"
    )

    critical_findings = ai_score.get(
        "critical_findings",
        0
    )

    behavior = ai_evaluation.get(
        "behavior_score",
        {}
    )

    behavior_status = behavior.get(
        "status",
        "NOT_ASSESSED"
    )

    if critical_findings > 0:

        return "BLOCKED"

    if risk == "CRITICAL":

        return "BLOCKED"

    if behavior_status == "FAIL":

        return "BLOCKED"

    if score < 60:

        return "BLOCKED"

    if (
        score < 80
        or behavior_status == "NOT_ASSESSED"
    ):

        return "CONDITIONAL"

    return "PASS"