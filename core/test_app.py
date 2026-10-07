"""
Unit tests for AI Project Tester core logic.
"""

from core.requirements import (
    analyze_requirements,
    extract_requirements,
)

from core.security_score import (
    calculate_security_score,
)

from core.test_score import (
    calculate_test_score,
)

from core.scoring import (
    calculate_final_score,
    calculate_release_gate,
)


def test_extract_requirements():
    text = """
    # Requirements

    1. User login
    2. User dashboard
    - Search functionality
    * Export reports
    """

    requirements = extract_requirements(
        text
    )

    assert len(requirements) == 5

    assert "User login" in requirements
    assert "User dashboard" in requirements


def test_requirement_analysis():
    project = {
        "files": [
            "login.py",
            "dashboard.py",
            "reports.py",
        ],
        "languages": [
            "Python",
        ],
        "frameworks": [],
    }

    result = analyze_requirements(
        """
        User login
        User dashboard
        Export reports
        """,
        project,
    )

    assert result["total_requirements"] == 3
    assert result["score"] >= 0
    assert result["coverage_score"] >= 0


def test_empty_requirements():
    result = analyze_requirements(
        "",
        {},
    )

    assert result["total_requirements"] == 0
    assert result["score"] == 0


def _clean_security():
    tools = {
        "bandit": {
            "status": "COMPLETED",
            "findings": [],
        },
        "semgrep": {
            "status": "COMPLETED",
            "findings": [],
        },
        "gitleaks": {
            "status": "COMPLETED",
            "findings": [],
        },
        "osv": {
            "status": "COMPLETED",
            "findings": [],
        },
        "secret_heuristics": {
            "status": "COMPLETED",
            "findings": [],
        },
    }

    return {
        "enabled": True,
        "status": "COMPLETED",
        "risk": "LOW",
        "tools": tools,
        "findings": [],
        "counts": {
            "bandit": 0,
            "semgrep": 0,
            "gitleaks": 0,
            "dependency_vulnerabilities": 0,
            "secret_heuristics": 0,
        },
        "assessed_tools": [
            "bandit",
            "semgrep",
            "gitleaks",
            "osv",
            "secret_heuristics",
        ],
        "not_assessed_tools": [],
    }


def test_clean_security_score():
    result = calculate_security_score(
        _clean_security()
    )

    assert result["score"] == 100
    assert result["risk"] == "LOW"
    assert result["status"] == "ASSESSED"


def test_gitleaks_critical():
    security = _clean_security()

    security["counts"]["gitleaks"] = 1
    security["findings"] = [
        {
            "scanner": "gitleaks",
            "severity": "CRITICAL",
            "message": (
                "Potential secret detected."
            ),
        }
    ]

    result = calculate_security_score(
        security
    )

    assert result["risk"] == "CRITICAL"
    assert result["score"] < 100


def test_missing_scanner():
    security = _clean_security()

    security["tools"]["semgrep"][
        "status"
    ] = "NOT_INSTALLED"

    security["assessed_tools"].remove(
        "semgrep"
    )

    security["not_assessed_tools"].append(
        "semgrep"
    )

    result = calculate_security_score(
        security
    )

    assert result["score"] < 100
    assert result["risk"] == "UNKNOWN"
    assert result["status"] == "PARTIAL"


def test_test_score_passed():
    result = calculate_test_score(
        {
            "status": "PASSED"
        }
    )

    assert result["score"] == 100
    assert result["status"] == "PASSED"
    assert result["risk"] == "LOW"


def test_test_score_failed():
    result = calculate_test_score(
        {
            "status": "FAILED"
        }
    )

    assert result["score"] == 30
    assert result["status"] == "FAILED"
    assert result["risk"] == "HIGH"


def test_test_score_not_assessed():
    result = calculate_test_score(
        {
            "status": "NOT_ASSESSED"
        }
    )

    assert result["score"] == 0
    assert result["status"] == "NOT_ASSESSED"
    assert result["risk"] == "UNKNOWN"


def test_final_score():
    requirements = {
        "score": 90
    }

    security = {
        "score": 80
    }

    testing = {
        "score": 100,
        "status": "PASSED",
    }

    ai = {
        "score": 70
    }

    result = calculate_final_score(
        {},
        requirements,
        security,
        testing,
        ai,
    )

    expected = (
        90 * 0.30
        + 80 * 0.30
        + 100 * 0.25
        + 70 * 0.15
    )

    assert result["score"] == round(
        expected
    )

    assert (
        result["component_scores"][
            "requirements"
        ]
        == 90
    )


def test_release_gate_ready():
    final_result = {
        "score": 90
    }

    requirements = {
        "score": 90
    }

    security = {
        "score": 90,
        "risk": "LOW",
        "status": "ASSESSED",
    }

    testing = {
        "score": 100,
        "status": "PASSED",
    }

    ai = {
        "score": 90,
        "findings": [],
    }

    result = calculate_release_gate(
        final_result,
        requirements,
        security,
        testing,
        ai,
    )

    assert result["status"] == "READY"


def test_release_gate_failed_tests():
    final_result = {
        "score": 80
    }

    requirements = {
        "score": 90
    }

    security = {
        "score": 90,
        "risk": "LOW",
        "status": "ASSESSED",
    }

    testing = {
        "score": 30,
        "status": "FAILED",
    }

    ai = {
        "score": 90,
        "findings": [],
    }

    result = calculate_release_gate(
        final_result,
        requirements,
        security,
        testing,
        ai,
    )

    assert result["status"] == "BLOCKED"


def test_release_gate_critical_ai():
    final_result = {
        "score": 80
    }

    requirements = {
        "score": 90
    }

    security = {
        "score": 90,
        "risk": "LOW",
        "status": "ASSESSED",
    }

    testing = {
        "score": 100,
        "status": "PASSED",
    }

    ai = {
        "score": 90,
        "findings": [
            {
                "severity": "CRITICAL",
                "title": "Critical issue",
            }
        ],
    }

    result = calculate_release_gate(
        final_result,
        requirements,
        security,
        testing,
        ai,
    )

    assert result["status"] == "BLOCKED"