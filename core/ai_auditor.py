"""
Groq-powered AI audit interpretation.

Architecture rule:
    Deterministic scanners/tests produce evidence.
    Requirement traceability produces structured evidence.
    Groq interprets that evidence.

Groq must never:
    - claim the project is bug-free
    - claim the project is completely secure
    - invent vulnerabilities
    - invent test results
    - invent implemented requirements
    - reproduce secret values
"""

import json
import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()


DEFAULT_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b",
)


# ============================================================
# HELPERS
# ============================================================

def _bounded_text(value, max_chars=12000):
    """Convert a value to bounded text."""

    if value is None:
        return ""

    text = str(value)

    if len(text) > max_chars:
        return (
            text[:max_chars]
            + "\n...[TRUNCATED]"
        )

    return text


def _bounded_list(value, max_items=100):
    """Return a bounded list."""

    if not isinstance(value, list):
        return []

    return value[:max_items]


# ============================================================
# PROJECT NORMALIZATION
# ============================================================

def _normalize_project(project):
    if not isinstance(project, dict):
        return {}

    return {
        "file_count": project.get(
            "file_count",
            0,
        ),

        "languages": _bounded_list(
            project.get(
                "languages",
                [],
            )
        ),

        "frameworks": _bounded_list(
            project.get(
                "frameworks",
                [],
            )
        ),

        "dependencies": _bounded_list(
            project.get(
                "dependencies",
                [],
            )
        ),

        "databases": _bounded_list(
            project.get(
                "databases",
                [],
            )
        ),

        "apis": _bounded_list(
            project.get(
                "apis",
                [],
            )
        ),

        "ai_tools": _bounded_list(
            project.get(
                "ai_tools",
                [],
            )
        ),

        "configuration": _bounded_list(
            project.get(
                "configuration",
                [],
            )
        ),

        "tests": _bounded_list(
            project.get(
                "tests",
                [],
            )
        ),

        "documentation": _bounded_list(
            project.get(
                "documentation",
                [],
            )
        ),

        "entry_points": _bounded_list(
            project.get(
                "entry_points",
                [],
            )
        ),
    }


# ============================================================
# SECURITY NORMALIZATION
# ============================================================

def _normalize_security(security):
    if not isinstance(
        security,
        dict,
    ):
        return {}

    findings = []

    for finding in security.get(
        "findings",
        [],
    ):

        if not isinstance(
            finding,
            dict,
        ):
            continue

        # IMPORTANT:
        # Never send actual secret values to Groq.
        findings.append(
            {
                "scanner": finding.get(
                    "scanner"
                ),

                "severity": finding.get(
                    "severity"
                ),

                "message": _bounded_text(
                    finding.get(
                        "message"
                    ),
                    1000,
                ),

                "file": finding.get(
                    "file"
                ),

                "line": finding.get(
                    "line"
                ),

                "rule": finding.get(
                    "rule"
                ),
            }
        )

    return {
        "status": security.get(
            "status",
            "UNKNOWN",
        ),

        "risk": security.get(
            "risk",
            "UNKNOWN",
        ),

        "counts": security.get(
            "counts",
            {},
        ),

        "assessed_tools": security.get(
            "assessed_tools",
            [],
        ),

        "not_assessed_tools": security.get(
            "not_assessed_tools",
            [],
        ),

        "findings": findings[:100],
    }


# ============================================================
# TESTING NORMALIZATION
# ============================================================

def _normalize_testing(testing):
    if not isinstance(
        testing,
        dict,
    ):
        return {}

    return {
        "status": testing.get(
            "status",
            "NOT_ASSESSED",
        ),

        "framework": testing.get(
            "framework"
        ),

        "exit_code": testing.get(
            "exit_code"
        ),

        "stdout": _bounded_text(
            testing.get(
                "stdout",
                "",
            ),
            5000,
        ),

        "stderr": _bounded_text(
            testing.get(
                "stderr",
                "",
            ),
            5000,
        ),
    }


# ============================================================
# REQUIREMENT NORMALIZATION
# ============================================================

def _normalize_requirements(requirements):
    if not isinstance(
        requirements,
        dict,
    ):
        return {}

    items = []

    for item in requirements.get(
        "requirements",
        [],
    ):

        if not isinstance(
            item,
            dict,
        ):
            continue

        items.append(
            {
                "requirement": _bounded_text(
                    item.get(
                        "requirement",
                        "",
                    ),
                    1000,
                ),

                "status": item.get(
                    "status"
                ),

                "confidence": item.get(
                    "confidence"
                ),

                "evidence": _bounded_list(
                    item.get(
                        "evidence",
                        [],
                    ),
                    10,
                ),

                "category": item.get(
                    "category"
                ),
            }
        )

    return {
        "total_requirements": requirements.get(
            "total_requirements",
            0,
        ),

        "implemented": requirements.get(
            "implemented",
            0,
        ),

        "missing": requirements.get(
            "missing",
            0,
        ),

        "score": requirements.get(
            "score",
            requirements.get(
                "coverage_score",
                0,
            ),
        ),

        "requirements": items,
    }


# ============================================================
# TRACEABILITY NORMALIZATION
# ============================================================

def _normalize_traceability(traceability):
    """
    Normalize the deterministic Requirement Traceability Matrix.

    Important:
        This function does not invent evidence.
        It only forwards evidence already produced by the
        deterministic traceability engine.
    """

    if not isinstance(
        traceability,
        dict,
    ):
        return {}

    matrix = []

    for item in traceability.get(
        "matrix",
        traceability.get(
            "requirements",
            [],
        ),
    ):

        if not isinstance(
            item,
            dict,
        ):
            continue

        implementation_evidence = item.get(
            "implementation_evidence",
            item.get(
                "implementation",
                [],
            ),
        )

        test_evidence = item.get(
            "test_evidence",
            item.get(
                "tests",
                [],
            ),
        )

        if not isinstance(
            implementation_evidence,
            list,
        ):
            implementation_evidence = []

        if not isinstance(
            test_evidence,
            list,
        ):
            test_evidence = []

        matrix.append(
            {
                "id": item.get(
                    "id"
                ),

                "requirement": _bounded_text(
                    item.get(
                        "requirement",
                        item.get(
                            "description",
                            "",
                        ),
                    ),
                    1000,
                ),

                "priority": str(
                    item.get(
                        "priority",
                        "MEDIUM",
                    )
                ).upper(),

                "type": str(
                    item.get(
                        "type",
                        "FUNCTIONAL",
                    )
                ).upper(),

                "status": str(
                    item.get(
                        "status",
                        "NOT_VERIFIED",
                    )
                ).upper(),

                "implementation_score": item.get(
                    "implementation_score",
                    0,
                ),

                "test_status": item.get(
                    "test_status",
                    item.get(
                        "test_result",
                        "NOT_ASSESSED",
                    ),
                ),

                "implementation_evidence": [
                    _bounded_text(
                        evidence,
                        1000,
                    )
                    for evidence
                    in implementation_evidence[:10]
                ],

                "test_evidence": [
                    _bounded_text(
                        evidence,
                        1000,
                    )
                    for evidence
                    in test_evidence[:10]
                ],
            }
        )

    return {
        "total": traceability.get(
            "total",
            len(matrix),
        ),

        "pass": traceability.get(
            "pass",
            traceability.get(
                "passed",
                0,
            ),
        ),

        "partial": traceability.get(
            "partial",
            0,
        ),

        "fail": traceability.get(
            "fail",
            traceability.get(
                "failed",
                0,
            ),
        ),

        "not_verified": traceability.get(
            "not_verified",
            0,
        ),

        "coverage_score": traceability.get(
            "coverage_score",
            traceability.get(
                "score",
                0,
            ),
        ),

        "matrix": matrix[:200],
    }


# ============================================================
# DEFAULT RESULT
# ============================================================

def _default_result(
    reason="AI audit unavailable.",
):

    return {
        "score": 0,

        "status": "NOT_ASSESSED",

        "summary": reason,

        "findings": [],

        "recommendations": [],

        "strengths": [],

        "limitations": [
            "AI audit is not a substitute for deterministic testing.",
            "Passing tests do not prove the project is bug-free.",
            "Security scanner coverage may be incomplete.",
            "Requirement traceability depends on available implementation and test evidence.",
        ],
    }


# ============================================================
# AI RESULT NORMALIZATION
# ============================================================

def _normalize_ai_result(data):

    if not isinstance(
        data,
        dict,
    ):
        return _default_result(
            "Groq returned an invalid response."
        )

    try:

        score = int(
            float(
                data.get(
                    "score",
                    0,
                )
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        score = 0

    score = max(
        0,
        min(
            100,
            score,
        ),
    )

    findings = data.get(
        "findings",
        [],
    )

    if not isinstance(
        findings,
        list,
    ):
        findings = []

    normalized_findings = []

    for finding in findings[:50]:

        if not isinstance(
            finding,
            dict,
        ):
            continue

        normalized_findings.append(
            {
                "severity": str(
                    finding.get(
                        "severity",
                        "INFO",
                    )
                ).upper(),

                "category": finding.get(
                    "category",
                    "general",
                ),

                "title": _bounded_text(
                    finding.get(
                        "title",
                        "",
                    ),
                    300,
                ),

                "description": _bounded_text(
                    finding.get(
                        "description",
                        "",
                    ),
                    1500,
                ),

                "evidence": _bounded_text(
                    finding.get(
                        "evidence",
                        "",
                    ),
                    1500,
                ),

                "recommendation": _bounded_text(
                    finding.get(
                        "recommendation",
                        "",
                    ),
                    1500,
                ),
            }
        )

    recommendations = data.get(
        "recommendations",
        [],
    )

    strengths = data.get(
        "strengths",
        [],
    )

    if not isinstance(
        recommendations,
        list,
    ):
        recommendations = []

    if not isinstance(
        strengths,
        list,
    ):
        strengths = []

    return {
        "score": score,

        "status": data.get(
            "status",
            "ASSESSED",
        ),

        "summary": _bounded_text(
            data.get(
                "summary",
                "",
            ),
            3000,
        ),

        "findings": normalized_findings,

        "recommendations": [
            _bounded_text(
                item,
                1000,
            )
            for item in recommendations[:30]
        ],

        "strengths": [
            _bounded_text(
                item,
                1000,
            )
            for item in strengths[:30]
        ],

        "limitations": [
            "AI interpretation is evidence-based but not proof of correctness.",
            "Passing tests do not prove the project is bug-free.",
            "Zero scanner findings do not prove complete security.",
            "Requirement traceability is based on available deterministic evidence.",
        ],
    }


# ============================================================
# GROQ AUDITOR
# ============================================================

def groq_audit(
    project,
    requirements,
    security,
    model="openai/gpt-oss-120b",
    testing=None,
    traceability=None,
):
    """
    Send bounded evidence to Groq and return structured AI analysis.

    Groq is an interpretation layer only.

    Deterministic evidence has priority.
    """

    api_key = os.getenv(
        "GROQ_API_KEY"
    )

    if not api_key:

        return _default_result(
            "GROQ_API_KEY is not configured."
        )

    testing = testing or {}
    traceability = traceability or {}

    normalized_project = _normalize_project(
        project
    )

    normalized_requirements = _normalize_requirements(
        requirements
    )

    normalized_security = _normalize_security(
        security
    )

    normalized_testing = _normalize_testing(
        testing
    )

    normalized_traceability = _normalize_traceability(
        traceability
    )

    # ========================================================
    # EVIDENCE SENT TO GROQ
    # ========================================================

    prompt_data = {

        "project": normalized_project,

        "requirements": normalized_requirements,

        "traceability": normalized_traceability,

        "security": normalized_security,

        "testing": normalized_testing,
    }

    # ========================================================
    # SYSTEM PROMPT
    # ========================================================

    system_prompt = """
You are an expert software quality, security,
requirements and release-readiness auditor.

You are an INTERPRETATION layer.

Deterministic scanner, test and requirement-traceability
evidence has priority over assumptions.

STRICT RULES:

1. Never claim software is bug-free.

2. Never claim software is completely secure.

3. Never invent files, functionality, vulnerabilities,
   requirements, test results or scanner results.

4. Never treat filename matching as proof of implementation.

5. Never treat implementation evidence alone as proof
   that a requirement is fully satisfied.

6. Passing tests are strong evidence but do not prove
   complete functionality.

7. Failed tests must be treated as actual evidence of
   a problem.

8. Timeout or build failure must not be treated as PASS.

9. NOT_VERIFIED means evidence is insufficient.

10. Never convert NOT_VERIFIED into PASS.

11. Never reproduce API keys, passwords, tokens,
    private keys or secret values.

12. Missing scanners mean NOT_ASSESSED.

13. Zero scanner findings do not prove complete security.

14. Deterministic security findings are stronger than
    speculative AI concerns.

15. Deterministic requirement status is stronger than
    assumptions.

16. High-priority or security requirement failures must
    be highlighted.

17. Requirement coverage must not be artificially increased.

18. Do not invent test evidence.

19. Clearly distinguish:
    - VERIFIED evidence
    - PARTIAL evidence
    - NOT_VERIFIED evidence
    - AI inference

20. Give actionable recommendations.

21. The AI score must NOT override deterministic release gates.

22. Use only the supplied evidence.

REQUIREMENT STATUS MEANINGS:

PASS:
Strong implementation evidence + supporting test evidence.

PARTIAL:
Some implementation evidence exists but verification
is incomplete.

FAIL:
Evidence indicates the requirement is not satisfied,
or an important test/security condition failed.

NOT_VERIFIED:
There is not enough evidence to determine whether the
requirement is implemented correctly.

RELEASE SAFETY:

Do not independently declare the project READY.

The deterministic release gate outside the AI model
controls the final release decision.

Return ONLY valid JSON.

Required JSON structure:

{
    "score": 0,
    "status": "ASSESSED",
    "summary": "...",
    "strengths": [],
    "findings": [
        {
            "severity": "CRITICAL|HIGH|MEDIUM|LOW|INFO",
            "category": "...",
            "title": "...",
            "description": "...",
            "evidence": "...",
            "recommendation": "..."
        }
    ],
    "recommendations": []
}

The score is an AI interpretation score only.
It must not override deterministic security,
testing or requirement release gates.
"""

    # ========================================================
    # USER PROMPT
    # ========================================================

    user_prompt = (
        "Audit the following software project evidence.\n\n"
        "IMPORTANT:\n"
        "- Use only supplied evidence.\n"
        "- Do not invent missing evidence.\n"
        "- Do not treat filenames as proof.\n"
        "- Do not claim the application is bug-free.\n"
        "- Do not claim complete security.\n"
        "- Pay special attention to requirement traceability.\n"
        "- Highlight FAIL and NOT_VERIFIED requirements.\n"
        "- Highlight HIGH/CRITICAL requirements.\n\n"
        + json.dumps(
            prompt_data,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )

    # ========================================================
    # GROQ REQUEST
    # ========================================================

    try:

        client = Groq(
            api_key=api_key
        )

        response = client.chat.completions.create(
            model=model,

            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },

                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],

            temperature=0.1,

            max_completion_tokens=7000,

            response_format={
                "type": "json_object"
            },
        )

        content = response.choices[
            0
        ].message.content

        if not content:

            return _default_result(
                "Groq returned an empty response."
            )

        data = json.loads(
            content
        )

        return _normalize_ai_result(
            data
        )

    except Exception as exc:

        return _default_result(
            f"Groq audit failed: {exc}"
        )