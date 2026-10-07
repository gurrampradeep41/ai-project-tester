"""
Test execution scoring and release-gate helpers.

Important:
- Passing tests do not prove the application is bug-free.
- NOT_ASSESSED is not PASS.
- Missing test execution is explicitly represented.
"""

STATUS_SCORES = {
    "PASSED": 100,
    "FAILED": 30,
    "TIMEOUT": 20,
    "BUILD_FAILED": 10,
    "ERROR": 0,
    "NOT_ASSESSED": 0,
    "DISABLED": 0,
    "NOT_INSTALLED": 0,
}


def _normalize_status(test_result):
    """
    Extract and normalize the test execution status.
    """

    if not isinstance(test_result, dict):
        return "NOT_ASSESSED"

    status = test_result.get(
        "status",
        "NOT_ASSESSED",
    )

    if status is None:
        return "NOT_ASSESSED"

    return str(status).strip().upper()


def calculate_test_score(test_result):
    """
    Convert test execution evidence into a deterministic score.
    """

    status = _normalize_status(test_result)

    score = STATUS_SCORES.get(
        status,
        0,
    )

    if status == "PASSED":

        risk = "LOW"

        summary = (
            "Automated tests completed successfully. "
            "Passing tests do not prove the project is bug-free."
        )

    elif status == "FAILED":

        risk = "HIGH"

        summary = (
            "Automated tests executed but one or more tests failed."
        )

    elif status == "TIMEOUT":

        risk = "HIGH"

        summary = (
            "Automated test execution exceeded the configured timeout."
        )

    elif status == "BUILD_FAILED":

        risk = "CRITICAL"

        summary = (
            "The project could not be built successfully "
            "inside the test environment."
        )

    elif status == "ERROR":

        risk = "CRITICAL"

        summary = (
            "Test execution encountered an execution error."
        )

    elif status in {
        "NOT_ASSESSED",
        "DISABLED",
        "NOT_INSTALLED",
    }:

        risk = "UNKNOWN"

        summary = (
            "Automated testing was not assessed. "
            "This must not be interpreted as a passing result."
        )

    else:

        risk = "UNKNOWN"

        summary = (
            f"Unknown test execution status: {status}."
        )

    return {
        "score": score,
        "status": status,
        "risk": risk,
        "summary": summary,
    }


def calculate_testing_release_gate(test_result):
    """
    Determine the release gate for automated testing.

    This function intentionally does NOT start with
    'test_' or 'testing_' so pytest does not mistake
    it for a test function.
    """

    status = _normalize_status(test_result)

    if status == "PASSED":
        return "PASS"

    if status in {
        "FAILED",
        "TIMEOUT",
        "BUILD_FAILED",
        "ERROR",
    }:
        return "BLOCKED"

    return "CONDITIONAL"


# ---------------------------------------------------------
# Backward-compatible helper
# ---------------------------------------------------------

def get_testing_release_gate(test_result):
    """
    Backward-compatible alias.

    Do not name this function test_* because pytest would
    attempt to execute it as a test.
    """

    return calculate_testing_release_gate(
        test_result
    )


__all__ = [
    "calculate_test_score",
    "calculate_testing_release_gate",
    "get_testing_release_gate",
]