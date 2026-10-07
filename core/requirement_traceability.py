"""
Requirement Traceability Matrix.

Purpose:
    Match client requirements against:
        1. implementation evidence
        2. test evidence
        3. deterministic security evidence

Important:
    Filename matching is NOT treated as proof of implementation.
"""

from pathlib import Path
import re


IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
    "dist",
    "build",
    "coverage",
}


STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "for",
    "with",
    "on",
    "in",
    "user",
    "users",
    "system",
    "application",
    "feature",
    "functionality",
    "must",
    "should",
    "shall",
    "provide",
    "allow",
    "support",
}


SYNONYMS = {
    "login": {
        "login",
        "signin",
        "sign-in",
        "authenticate",
        "authentication",
    },

    "registration": {
        "register",
        "registration",
        "signup",
        "sign-up",
        "create-account",
    },

    "search": {
        "search",
        "find",
        "lookup",
        "query",
    },

    "email": {
        "email",
        "mail",
        "notification",
    },

    "admin": {
        "admin",
        "administrator",
        "dashboard",
        "management",
    },

    "security": {
        "security",
        "secure",
        "authentication",
        "authorization",
        "password",
        "credential",
        "secret",
    },

    "testing": {
        "test",
        "tests",
        "testing",
        "pytest",
        "unittest",
        "jest",
    },

    "documentation": {
        "documentation",
        "docs",
        "readme",
        "guide",
    },

    "ai": {
        "ai",
        "llm",
        "chatbot",
        "assistant",
        "generative",
    },
}


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize_text(value):
    if value is None:
        return ""

    return re.sub(
        r"[^a-z0-9_\-\s]",
        " ",
        str(value).lower(),
    )


def tokenize(value):
    text = normalize_text(value)

    tokens = re.findall(
        r"[a-z0-9_]+",
        text,
    )

    return {
        token
        for token in tokens
        if token not in STOPWORDS
        and len(token) > 1
    }


def expand_tokens(tokens):
    expanded = set(tokens)

    for token in list(tokens):

        for canonical, synonyms in SYNONYMS.items():

            if token in synonyms:
                expanded.add(canonical)
                expanded.update(synonyms)

    return expanded


def keyword_similarity(
    requirement_tokens,
    evidence_tokens,
):
    if not requirement_tokens:
        return 0.0

    requirement_tokens = expand_tokens(
        requirement_tokens
    )

    evidence_tokens = expand_tokens(
        evidence_tokens
    )

    intersection = (
        requirement_tokens
        & evidence_tokens
    )

    return len(intersection) / len(
        requirement_tokens
    )


# ============================================================
# FILE COLLECTION
# ============================================================

def collect_project_files(project_dir):
    project_dir = Path(project_dir)

    files = []

    for path in project_dir.rglob("*"):

        if not path.is_file():
            continue

        relative_parts = path.relative_to(
            project_dir
        ).parts

        if any(
            part in IGNORED_DIRS
            for part in relative_parts
        ):
            continue

        files.append(path)

    return files


# ============================================================
# FILE EVIDENCE
# ============================================================

def extract_file_evidence(
    path,
    max_chars=30000,
):
    try:

        if path.stat().st_size > max_chars:
            return ""

        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

    except Exception:
        return ""


# ============================================================
# IMPLEMENTATION MATCHING
# ============================================================

def find_implementation_evidence(
    requirement,
    project_dir,
):
    project_dir = Path(project_dir)

    requirement_tokens = expand_tokens(
        tokenize(requirement)
    )

    results = []

    for path in collect_project_files(
        project_dir
    ):

        filename_tokens = expand_tokens(
            tokenize(path.stem)
        )

        filename_score = keyword_similarity(
            requirement_tokens,
            filename_tokens,
        )

        content = extract_file_evidence(
            path
        )

        content_tokens = expand_tokens(
            tokenize(content[:20000])
        )

        content_score = keyword_similarity(
            requirement_tokens,
            content_tokens,
        )

        # Content is stronger evidence than filename.
        score = (
            content_score * 0.80
            + filename_score * 0.20
        )

        if score >= 0.25:

            results.append(
                {
                    "file": str(
                        path.relative_to(
                            project_dir
                        )
                    ),

                    "score": round(
                        score,
                        3,
                    ),

                    "filename_score": round(
                        filename_score,
                        3,
                    ),

                    "content_score": round(
                        content_score,
                        3,
                    ),
                }
            )

    results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return results[:10]


# ============================================================
# TEST EVIDENCE
# ============================================================

def find_test_evidence(
    requirement,
    project_dir,
):
    project_dir = Path(project_dir)

    requirement_tokens = expand_tokens(
        tokenize(requirement)
    )

    results = []

    for path in collect_project_files(
        project_dir
    ):

        filename = path.name.lower()

        is_test_file = (
            "test" in filename
            or filename.startswith("spec")
            or "tests" in path.parts
        )

        if not is_test_file:
            continue

        content = extract_file_evidence(
            path,
            max_chars=20000,
        )

        tokens = expand_tokens(
            tokenize(content)
        )

        score = keyword_similarity(
            requirement_tokens,
            tokens,
        )

        if score >= 0.20:

            results.append(
                {
                    "file": str(
                        path.relative_to(
                            project_dir
                        )
                    ),

                    "score": round(
                        score,
                        3,
                    ),
                }
            )

    results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return results[:10]


# ============================================================
# REQUIREMENT CLASSIFICATION
# ============================================================

def classify_requirement(
    requirement,
    implementation_evidence,
    test_evidence,
    test_result,
    priority="MEDIUM",
    requirement_type="FUNCTIONAL",
    security_result=None,
):
    security_result = (
        security_result
        or {}
    )

    implementation_score = 0.0

    if implementation_evidence:

        implementation_score = max(
            item.get(
                "score",
                0,
            )
            for item in implementation_evidence
        )

    test_status = str(
        test_result.get(
            "status",
            "NOT_ASSESSED",
        )
    ).upper()

    # --------------------------------------------------------
    # SECURITY FAILURE
    # --------------------------------------------------------

    security_findings = security_result.get(
        "findings",
        [],
    )

    critical_security_failure = False

    for finding in security_findings:

        if not isinstance(
            finding,
            dict,
        ):
            continue

        scanner = str(
            finding.get(
                "scanner",
                "",
            )
        ).lower()

        severity = str(
            finding.get(
                "severity",
                "",
            )
        ).upper()

        if (
            scanner in {
                "gitleaks",
                "dependency_vulnerabilities",
            }
            and severity in {
                "CRITICAL",
                "HIGH",
            }
        ):
            critical_security_failure = True

    if (
        requirement_type.upper() == "SECURITY"
        and critical_security_failure
    ):
        status = "FAIL"

    # --------------------------------------------------------
    # STRONG IMPLEMENTATION + TEST
    # --------------------------------------------------------

    elif (
        implementation_score >= 0.60
        and test_evidence
        and test_status == "PASSED"
    ):
        status = "PASS"

    # --------------------------------------------------------
    # IMPLEMENTED BUT NOT TESTED
    # --------------------------------------------------------

    elif (
        implementation_score >= 0.60
        and not test_evidence
    ):
        status = "PARTIAL"

    # --------------------------------------------------------
    # TEST FAILURE
    # --------------------------------------------------------

    elif (
        implementation_score >= 0.60
        and test_status in {
            "FAILED",
            "TIMEOUT",
            "BUILD_FAILED",
        }
    ):
        status = "FAIL"

    # --------------------------------------------------------
    # PARTIAL IMPLEMENTATION
    # --------------------------------------------------------

    elif (
        0.30
        <= implementation_score
        < 0.60
    ):
        status = "PARTIAL"

    # --------------------------------------------------------
    # INSUFFICIENT EVIDENCE
    # --------------------------------------------------------

    else:
        status = "NOT_VERIFIED"

    return {
        "status": status,

        "priority": str(
            priority
        ).upper(),

        "type": str(
            requirement_type
        ).upper(),

        "implementation_score": round(
            implementation_score,
            3,
        ),

        "implementation_evidence": implementation_evidence,

        "test_evidence": test_evidence,

        "test_status": test_status,
    }


# ============================================================
# TRACEABILITY MATRIX
# ============================================================

def build_traceability_matrix(
    requirements,
    project_dir,
    security_result=None,
    test_result=None,
):
    security_result = (
        security_result
        or {}
    )

    test_result = (
        test_result
        or {}
    )

    matrix = []

    for index, requirement in enumerate(
        requirements,
        start=1,
    ):

        if isinstance(
            requirement,
            dict,
        ):

            text = requirement.get(
                "requirement",
                requirement.get(
                    "description",
                    "",
                ),
            )

            priority = requirement.get(
                "priority",
                "MEDIUM",
            )

            requirement_type = requirement.get(
                "type",
                requirement.get(
                    "category",
                    "FUNCTIONAL",
                ),
            )

        else:

            text = str(
                requirement
            )

            priority = "MEDIUM"
            requirement_type = "FUNCTIONAL"

        implementation_evidence = (
            find_implementation_evidence(
                text,
                project_dir,
            )
        )

        test_evidence = (
            find_test_evidence(
                text,
                project_dir,
            )
        )

        classification = classify_requirement(
            requirement=text,
            implementation_evidence=implementation_evidence,
            test_evidence=test_evidence,
            test_result=test_result,
            priority=priority,
            requirement_type=requirement_type,
            security_result=security_result,
        )

        matrix.append(
            {
                "id": f"REQ-{index:03d}",

                "requirement": text,

                **classification,
            }
        )

    total = len(matrix)

    passed = sum(
        1
        for item in matrix
        if item["status"] == "PASS"
    )

    partial = sum(
        1
        for item in matrix
        if item["status"] == "PARTIAL"
    )

    failed = sum(
        1
        for item in matrix
        if item["status"] == "FAIL"
    )

    not_verified = sum(
        1
        for item in matrix
        if item["status"] == "NOT_VERIFIED"
    )

    if total:

        coverage_score = (
            (
                passed
                + partial * 0.5
            )
            / total
        ) * 100

    else:

        coverage_score = 0

    return {
        "total": total,

        "pass": passed,

        "partial": partial,

        "fail": failed,

        "not_verified": not_verified,

        "coverage_score": round(
            coverage_score,
            2,
        ),

        "matrix": matrix,
    }