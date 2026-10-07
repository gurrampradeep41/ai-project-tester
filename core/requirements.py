import re
from typing import Any, Dict, List


def clean_requirement_text(text: str) -> str:
    """
    Clean markdown and unnecessary formatting.
    """

    text = re.sub(
        r"```.*?```",
        " ",
        text,
        flags=re.DOTALL
    )

    text = re.sub(
        r"`([^`]*)`",
        r"\1",
        text
    )

    text = re.sub(
        r"[*_#>]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def is_requirement_candidate(line: str) -> bool:
    """
    Determine whether a line looks like a requirement.
    """

    line = line.strip()

    if not line:
        return False

    patterns = [
        r"^\d+[\.\)]\s+",
        r"^[-*]\s+",
        r"^REQ[-_ ]?\d+",
        r"^FR[-_ ]?\d+",
        r"^NFR[-_ ]?\d+",
        r"^UC[-_ ]?\d+",
        r"^the system shall",
        r"^the application shall",
        r"^the user shall",
        r"^users shall",
        r"^admin shall",
        r"^must ",
        r"^should ",
        r"^shall "
    ]

    lower = line.lower()

    return any(
        re.search(
            pattern,
            lower,
            re.IGNORECASE
        )
        for pattern in patterns
    )


def remove_requirement_prefix(
    text: str
) -> str:

    text = re.sub(
        r"^\s*[-*]\s*",
        "",
        text
    )

    text = re.sub(
        r"^\s*\d+[\.\)]\s*",
        "",
        text
    )

    text = re.sub(
        r"^\s*(REQ|FR|NFR|UC)[-_ ]?\d+[:\.\-]?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    return text.strip()


def infer_requirement_type(
    text: str
) -> str:

    lower = text.lower()

    security_words = [
        "security",
        "password",
        "authentication",
        "authorization",
        "credential",
        "encrypt",
        "secure"
    ]

    testing_words = [
        "test",
        "testing",
        "unit test",
        "integration test"
    ]

    performance_words = [
        "performance",
        "latency",
        "response time",
        "scalable",
        "load"
    ]

    documentation_words = [
        "documentation",
        "readme",
        "document"
    ]

    configuration_words = [
        "production",
        "environment variable",
        "configuration",
        "deployment"
    ]

    if any(
        word in lower
        for word in security_words
    ):
        return "SECURITY"

    if any(
        word in lower
        for word in testing_words
    ):
        return "TESTING"

    if any(
        word in lower
        for word in performance_words
    ):
        return "PERFORMANCE"

    if any(
        word in lower
        for word in documentation_words
    ):
        return "DOCUMENTATION"

    if any(
        word in lower
        for word in configuration_words
    ):
        return "CONFIGURATION"

    return "FUNCTIONAL"


def parse_requirements(
    text: str
) -> List[Dict[str, Any]]:

    requirements = []

    lines = text.splitlines()

    counter = 1

    for raw_line in lines:

        line = raw_line.strip()

        if not line:
            continue

        if not is_requirement_candidate(line):
            continue

        cleaned = remove_requirement_prefix(
            clean_requirement_text(line)
        )

        if len(cleaned) < 5:
            continue

        requirements.append({
            "id": f"REQ-{counter:03d}",
            "text": cleaned,
            "type": infer_requirement_type(
                cleaned
            ),
            "priority": (
                "HIGH"
                if any(
                    word in cleaned.lower()
                    for word in [
                        "must",
                        "security",
                        "critical",
                        "shall"
                    ]
                )
                else "MEDIUM"
            )
        })

        counter += 1

    return requirements


def parse_requirement_document(
    content: str,
    filename: str = ""
) -> Dict[str, Any]:

    requirements = parse_requirements(
        content
    )

    return {
        "source": filename,
        "count": len(requirements),
        "requirements": requirements
    }


def analyze_requirements(
    content: str,
    filename: str = ""
) -> Dict[str, Any]:
    """
    Analyze a client requirement document.

    This function is kept as a compatibility wrapper for the
    application layer.
    """

    result = parse_requirement_document(
        content,
        filename
    )

    return result