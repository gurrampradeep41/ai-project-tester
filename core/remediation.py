# core/remediation.py

from __future__ import annotations

from typing import Any


PRIORITY_ORDER = {
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
    "INFO": 4,
}


def build_remediation_plan(
    production: dict[str, Any],
    security: dict[str, Any] | None = None,
    testing: dict[str, Any] | None = None,
    requirement_score: dict[str, Any] | None = None,
    ai: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:

    items = []

    # ---------------------------------------------------------
    # PRODUCTION
    # ---------------------------------------------------------

    for finding in production.get(
        "findings",
        [],
    ):

        status = str(
            finding.get(
                "status",
                "",
            )
        ).upper()

        if status not in {
            "FAIL",
            "WARNING",
        }:
            continue

        severity = str(
            finding.get(
                "severity",
                "MEDIUM",
            )
        ).upper()

        items.append(
            {
                "source": "Production Readiness",
                "id": finding.get("id"),
                "priority": severity,
                "title": finding.get("title"),
                "problem": finding.get("message"),
                "evidence": finding.get(
                    "evidence",
                    [],
                ),
                "action": finding.get(
                    "recommendation",
                    "Review and remediate this finding.",
                ),
                "status": "OPEN",
            }
        )

    # ---------------------------------------------------------
    # SECURITY
    # ---------------------------------------------------------

    if security:

        for finding in security.get(
            "findings",
            [],
        ):

            severity = str(
                finding.get(
                    "severity",
                    "MEDIUM",
                )
            ).upper()

            if severity not in {
                "CRITICAL",
                "HIGH",
                "MEDIUM",
            }:
                continue

            items.append(
                {
                    "source": "Security",
                    "id": finding.get(
                        "rule",
                        "SECURITY",
                    ),
                    "priority": severity,
                    "title": finding.get(
                        "message",
                        "Security finding",
                    ),
                    "problem": finding.get(
                        "message",
                        "",
                    ),
                    "evidence": [
                        finding.get(
                            "file",
                            ""
                        )
                    ],
                    "action": (
                        "Remediate the security finding "
                        "and rerun the security audit."
                    ),
                    "status": "OPEN",
                }
            )

    # ---------------------------------------------------------
    # TESTING
    # ---------------------------------------------------------

    if testing:

        test_status = str(
            testing.get(
                "status",
                "",
            )
        ).upper()

        if test_status in {
            "FAIL",
            "ERROR",
        }:

            items.append(
                {
                    "source": "Automated Testing",
                    "id": "TEST-RELEASE",
                    "priority": "HIGH",
                    "title": "Automated tests are failing",
                    "problem": testing.get(
                        "summary",
                        "Automated tests did not pass.",
                    ),
                    "evidence": [
                        testing.get(
                            "stderr",
                            "",
                        )
                    ],
                    "action": (
                        "Fix failing tests and rerun "
                        "the sandbox test suite."
                    ),
                    "status": "OPEN",
                }
            )

    # ---------------------------------------------------------
    # REQUIREMENTS
    # ---------------------------------------------------------

    if requirement_score:

        critical_failures = requirement_score.get(
            "critical_failures",
            [],
        )

        for requirement in critical_failures:

            items.append(
                {
                    "source": "Requirements",
                    "id": requirement.get(
                        "id",
                        "REQ",
                    ),
                    "priority": "HIGH",
                    "title": requirement.get(
                        "requirement",
                        "Critical requirement failure",
                    ),
                    "problem": (
                        "A critical client requirement "
                        "is not satisfied."
                    ),
                    "evidence": requirement.get(
                        "implementation_evidence",
                        [],
                    ),
                    "action": (
                        "Implement and verify the client "
                        "requirement before release."
                    ),
                    "status": "OPEN",
                }
            )

    # ---------------------------------------------------------
    # AI
    # ---------------------------------------------------------

    if ai:

        ai_findings = ai.get(
            "findings",
            [],
        )

        for finding in ai_findings:

            severity = str(
                finding.get(
                    "severity",
                    "MEDIUM",
                )
            ).upper()

            if severity not in {
                "CRITICAL",
                "HIGH",
                "MEDIUM",
            }:
                continue

            items.append(
                {
                    "source": "AI Audit",
                    "id": finding.get(
                        "id",
                        "AI",
                    ),
                    "priority": severity,
                    "title": finding.get(
                        "title",
                        "AI finding",
                    ),
                    "problem": finding.get(
                        "description",
                        "",
                    ),
                    "evidence": [
                        finding.get(
                            "evidence",
                            "",
                        )
                    ],
                    "action": finding.get(
                        "recommendation",
                        "Review and remediate the AI finding.",
                    ),
                    "status": "OPEN",
                }
            )

    items.sort(
        key=lambda item: PRIORITY_ORDER.get(
            item.get(
                "priority",
                "MEDIUM",
            ),
            2,
        )
    )

    return items