# core/production_audit.py

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
    "dist",
    "build",
}


TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".php",
    ".rb",
    ".cs",
    ".cpp",
    ".c",
    ".h",
    ".html",
    ".css",
    ".scss",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".md",
    ".txt",
    ".env",
    ".sh",
    ".bat",
}


def collect_files(project_dir: Path) -> list[Path]:
    """
    Collect relevant project files while ignoring generated/vendor directories.
    """

    files = []

    for path in project_dir.rglob("*"):
        if not path.is_file():
            continue

        if any(part in IGNORED_DIRS for part in path.parts):
            continue

        files.append(path)

    return files


def read_text(path: Path, max_chars: int = 100_000) -> str:
    """
    Safely read a text file.
    """

    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return ""

    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )[:max_chars]
    except Exception:
        return ""


def relative_name(path: Path, project_dir: Path) -> str:
    try:
        return str(path.relative_to(project_dir))
    except Exception:
        return path.name


def finding(
    check_id: str,
    title: str,
    severity: str,
    status: str,
    message: str,
    evidence: list[str] | None = None,
    recommendation: str = "",
) -> dict[str, Any]:

    return {
        "id": check_id,
        "title": title,
        "severity": severity,
        "status": status,
        "message": message,
        "evidence": evidence or [],
        "recommendation": recommendation,
    }


def check_debug_configuration(
    files: list[Path],
    project_dir: Path,
) -> dict[str, Any]:

    findings = []

    patterns = [
        r"\bDEBUG\s*=\s*True\b",
        r"\bDEBUG\s*=\s*true\b",
        r"\bdebug\s*=\s*True\b",
        r"\bdebug\s*=\s*true\b",
        r"app\.run\s*\([^)]*debug\s*=\s*True",
        r"debug\s*:\s*true",
    ]

    for path in files:
        text = read_text(path)

        if not text:
            continue

        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                findings.append(
                    finding(
                        "PROD-001",
                        "Debug mode appears enabled",
                        "HIGH",
                        "FAIL",
                        "Development/debug configuration was detected.",
                        [
                            relative_name(path, project_dir)
                        ],
                        "Disable debug/development mode in production.",
                    )
                )
                return {
                    "status": "FAIL",
                    "findings": findings,
                }

    return {
        "status": "PASS",
        "findings": [
            finding(
                "PROD-001",
                "Debug mode",
                "INFO",
                "PASS",
                "No obvious production debug configuration was detected.",
            )
        ],
    }


def check_secret_files(
    files: list[Path],
    project_dir: Path,
) -> dict[str, Any]:

    findings = []

    dangerous_names = {
        ".env",
        ".env.local",
        ".env.production",
        ".env.development",
        "credentials.json",
        "service-account.json",
        "secrets.json",
    }

    for path in files:

        if path.name.lower() not in dangerous_names:
            continue

        if path.name == ".env.example":
            continue

        findings.append(
            finding(
                "PROD-002",
                "Potential secret/configuration file included",
                "HIGH",
                "WARNING",
                "A sensitive configuration filename exists inside the project.",
                [
                    relative_name(path, project_dir)
                ],
                "Keep secrets outside the source package and provide an example configuration file.",
            )
        )

    if findings:
        return {
            "status": "WARNING",
            "findings": findings,
        }

    return {
        "status": "PASS",
        "findings": [
            finding(
                "PROD-002",
                "Secret file packaging",
                "INFO",
                "PASS",
                "No obvious secret configuration files were detected.",
            )
        ],
    }


def check_environment_configuration(
    files: list[Path],
    project_dir: Path,
) -> dict[str, Any]:

    names = {path.name.lower() for path in files}

    has_env_example = (
        ".env.example" in names
        or ".env.template" in names
        or "env.example" in names
    )

    has_config_file = any(
        name in names
        for name in {
            "config.py",
            "settings.py",
            "config.js",
            "config.ts",
            "application.yml",
            "application.yaml",
            "application.properties",
        }
    )

    if has_env_example or has_config_file:
        return {
            "status": "PASS",
            "findings": [
                finding(
                    "PROD-003",
                    "Environment configuration",
                    "INFO",
                    "PASS",
                    "A configuration/environment mechanism was detected.",
                )
            ],
        }

    return {
        "status": "WARNING",
        "findings": [
            finding(
                "PROD-003",
                "Environment configuration",
                "MEDIUM",
                "WARNING",
                "No obvious environment configuration template was detected.",
                [],
                "Provide .env.example or equivalent production configuration documentation.",
            )
        ],
    }


def check_cors(
    files: list[Path],
    project_dir: Path,
) -> dict[str, Any]:

    risky_patterns = [
        r"allow_origins\s*=\s*\[\s*[\"']\*[\"']",
        r"origins\s*=\s*[\"']\*[\"']",
        r"Access-Control-Allow-Origin[\"']?\s*[:=]\s*[\"']\*[\"']",
        r"cors.*allow.*origin.*\*",
    ]

    for path in files:

        text = read_text(path)

        if not text:
            continue

        for pattern in risky_patterns:

            if re.search(pattern, text, re.IGNORECASE):

                return {
                    "status": "WARNING",
                    "findings": [
                        finding(
                            "PROD-004",
                            "Wildcard CORS configuration",
                            "MEDIUM",
                            "WARNING",
                            "Wildcard CORS configuration was detected.",
                            [
                                relative_name(path, project_dir)
                            ],
                            "Restrict allowed origins to trusted production domains.",
                        )
                    ],
                }

    return {
        "status": "PASS",
        "findings": [
            finding(
                "PROD-004",
                "CORS configuration",
                "INFO",
                "PASS",
                "No obvious wildcard CORS configuration was detected.",
            )
        ],
    }


def check_docker(
    files: list[Path],
    project_dir: Path,
) -> dict[str, Any]:

    names = {path.name.lower() for path in files}

    dockerfile = any(
        name in names
        for name in {
            "dockerfile",
            "dockerfile.prod",
            "dockerfile.production",
        }
    )

    compose = any(
        name in names
        for name in {
            "docker-compose.yml",
            "docker-compose.yaml",
            "compose.yml",
            "compose.yaml",
        }
    )

    if dockerfile:
        evidence = ["Dockerfile detected"]

        if compose:
            evidence.append("Docker Compose configuration detected")

        return {
            "status": "PASS",
            "findings": [
                finding(
                    "PROD-005",
                    "Containerization",
                    "INFO",
                    "PASS",
                    "Container configuration was detected.",
                    evidence,
                )
            ],
        }

    return {
        "status": "WARNING",
        "findings": [
            finding(
                "PROD-005",
                "Production container configuration",
                "MEDIUM",
                "WARNING",
                "No Dockerfile was detected.",
                [],
                "Provide reproducible production deployment configuration where appropriate.",
            )
        ],
    }


def check_dependencies(
    files: list[Path],
    project_dir: Path,
) -> dict[str, Any]:

    names = {path.name.lower() for path in files}

    dependency_files = {
        "requirements.txt",
        "pyproject.toml",
        "poetry.lock",
        "pipfile",
        "pipfile.lock",
        "package.json",
        "package-lock.json",
        "npm-shrinkwrap.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "pom.xml",
        "build.gradle",
        "go.mod",
        "go.sum",
        "cargo.toml",
        "cargo.lock",
    }

    detected = sorted(
        name for name in dependency_files
        if name in names
    )

    if not detected:

        return {
            "status": "FAIL",
            "findings": [
                finding(
                    "PROD-006",
                    "Dependency manifest",
                    "HIGH",
                    "FAIL",
                    "No recognizable dependency manifest was detected.",
                    [],
                    "Add a reproducible dependency manifest and lock/pin dependencies where supported.",
                )
            ],
        }

    lock_files = {
        "poetry.lock",
        "pipfile.lock",
        "package-lock.json",
        "npm-shrinkwrap.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "go.sum",
        "cargo.lock",
    }

    has_lock = any(
        item in names
        for item in lock_files
    )

    status = "PASS" if has_lock else "WARNING"

    return {
        "status": status,
        "findings": [
            finding(
                "PROD-006",
                "Dependency reproducibility",
                "INFO" if has_lock else "MEDIUM",
                status,
                "Dependency files detected."
                + (
                    " A lock file was also detected."
                    if has_lock
                    else " No lock file was detected."
                ),
                detected,
                ""
                if has_lock
                else "Use lock files or explicit dependency versions for reproducible deployments.",
            )
        ],
    }


def check_documentation(
    files: list[Path],
    project_dir: Path,
) -> dict[str, Any]:

    names = {path.name.lower() for path in files}

    readme = any(
        name.startswith("readme")
        for name in names
    )

    deployment_keywords = [
        "deploy",
        "deployment",
        "production",
        "docker",
        "environment",
        "installation",
        "setup",
    ]

    deployment_docs = False

    for path in files:

        if path.suffix.lower() not in {
            ".md",
            ".txt",
        }:
            continue

        text = read_text(path, max_chars=50_000).lower()

        if sum(
            keyword in text
            for keyword in deployment_keywords
        ) >= 2:
            deployment_docs = True
            break

    if readme and deployment_docs:

        return {
            "status": "PASS",
            "findings": [
                finding(
                    "PROD-007",
                    "Production documentation",
                    "INFO",
                    "PASS",
                    "README and deployment-related documentation were detected.",
                )
            ],
        }

    if readme:

        return {
            "status": "WARNING",
            "findings": [
                finding(
                    "PROD-007",
                    "Production documentation",
                    "MEDIUM",
                    "WARNING",
                    "README exists but production deployment documentation is incomplete or unclear.",
                    [],
                    "Document installation, environment variables, deployment, health checks, and rollback procedures.",
                )
            ],
        }

    return {
        "status": "FAIL",
        "findings": [
            finding(
                "PROD-007",
                "Project documentation",
                "HIGH",
                "FAIL",
                "No README documentation was detected.",
                [],
                "Add project setup and production deployment documentation.",
            )
        ],
    }


def check_health_endpoint(
    files: list[Path],
    project_dir: Path,
) -> dict[str, Any]:

    patterns = [
        r"@app\.get\([\"']/health",
        r"@app\.get\([\"']/healthz",
        r"@app\.get\([\"']/ready",
        r"@app\.get\([\"']/readiness",
        r"route.*health",
        r"healthcheck",
        r"health_check",
    ]

    for path in files:

        text = read_text(path)

        if not text:
            continue

        for pattern in patterns:

            if re.search(pattern, text, re.IGNORECASE):

                return {
                    "status": "PASS",
                    "findings": [
                        finding(
                            "PROD-008",
                            "Health/readiness endpoint",
                            "INFO",
                            "PASS",
                            "A health or readiness mechanism was detected.",
                            [
                                relative_name(path, project_dir)
                            ],
                        )
                    ],
                }

    return {
        "status": "WARNING",
        "findings": [
            finding(
                "PROD-008",
                "Health/readiness endpoint",
                "MEDIUM",
                "WARNING",
                "No obvious health/readiness endpoint was detected.",
                [],
                "Provide a lightweight health/readiness mechanism for deployment monitoring.",
            )
        ],
    }


def check_logging(
    files: list[Path],
    project_dir: Path,
) -> dict[str, Any]:

    patterns = [
        r"\blogging\.",
        r"\bimport logging\b",
        r"\bconsole\.log\b",
        r"\blogger\.",
        r"\bstructlog\b",
        r"\bloguru\b",
    ]

    for path in files:

        text = read_text(path)

        if not text:
            continue

        if any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in patterns
        ):

            return {
                "status": "PASS",
                "findings": [
                    finding(
                        "PROD-009",
                        "Application logging",
                        "INFO",
                        "PASS",
                        "Application logging indicators were detected.",
                        [
                            relative_name(path, project_dir)
                        ],
                    )
                ],
            }

    return {
        "status": "WARNING",
        "findings": [
            finding(
                "PROD-009",
                "Application logging",
                "MEDIUM",
                "WARNING",
                "No obvious structured/application logging mechanism was detected.",
                [],
                "Add production logging with appropriate levels and avoid logging secrets or sensitive data.",
            )
        ],
    }


def check_api_documentation(
    files: list[Path],
    project_dir: Path,
) -> dict[str, Any]:

    patterns = [
        r"FastAPI",
        r"swagger",
        r"openapi",
        r"@app\.get",
        r"@app\.post",
        r"express\(",
        r"Router\(",
    ]

    for path in files:

        text = read_text(path)

        if not text:
            continue

        if any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in patterns
        ):

            return {
                "status": "PASS",
                "findings": [
                    finding(
                        "PROD-010",
                        "API interface/documentation",
                        "INFO",
                        "PASS",
                        "API or OpenAPI-related indicators were detected.",
                        [
                            relative_name(path, project_dir)
                        ],
                    )
                ],
            }

    return {
        "status": "NOT_APPLICABLE",
        "findings": [
            finding(
                "PROD-010",
                "API documentation",
                "INFO",
                "NOT_APPLICABLE",
                "No obvious API implementation was detected.",
            )
        ],
    }


def check_startup(
    files: list[Path],
    project_dir: Path,
) -> dict[str, Any]:

    startup_files = {
        "main.py",
        "app.py",
        "server.py",
        "manage.py",
        "index.js",
        "server.js",
        "main.js",
        "main.ts",
        "server.ts",
        "package.json",
        "dockerfile",
    }

    detected = [
        relative_name(path, project_dir)
        for path in files
        if path.name.lower() in startup_files
    ]

    if detected:

        return {
            "status": "PASS",
            "findings": [
                finding(
                    "PROD-011",
                    "Application startup configuration",
                    "INFO",
                    "PASS",
                    "A recognizable application entry point was detected.",
                    detected[:10],
                )
            ],
        }

    return {
        "status": "WARNING",
        "findings": [
            finding(
                "PROD-011",
                "Application startup configuration",
                "MEDIUM",
                "WARNING",
                "No conventional application entry point was detected.",
                [],
                "Document the exact production startup command.",
            )
        ],
    }


def check_error_handling(
    files: list[Path],
    project_dir: Path,
) -> dict[str, Any]:

    patterns = [
        r"\btry\s*:",
        r"\bexcept\s+Exception",
        r"\btry\s*\{",
        r"\bcatch\s*\(",
        r"HTTPException",
        r"errorHandler",
    ]

    matches = []

    for path in files:

        text = read_text(path)

        if not text:
            continue

        if any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in patterns
        ):
            matches.append(
                relative_name(path, project_dir)
            )

    if matches:

        return {
            "status": "PASS",
            "findings": [
                finding(
                    "PROD-012",
                    "Error handling",
                    "INFO",
                    "PASS",
                    "Error-handling patterns were detected.",
                    matches[:10],
                )
            ],
        }

    return {
        "status": "WARNING",
        "findings": [
            finding(
                "PROD-012",
                "Error handling",
                "MEDIUM",
                "WARNING",
                "No obvious error-handling patterns were detected.",
                [],
                "Implement controlled exception handling and safe production error responses.",
            )
        ],
    }


def calculate_production_score(
    checks: dict[str, dict[str, Any]],
) -> dict[str, Any]:

    weights = {
        "PROD-001": 10,
        "PROD-002": 15,
        "PROD-003": 8,
        "PROD-004": 7,
        "PROD-005": 8,
        "PROD-006": 12,
        "PROD-007": 10,
        "PROD-008": 7,
        "PROD-009": 7,
        "PROD-010": 4,
        "PROD-011": 6,
        "PROD-012": 6,
    }

    status_scores = {
        "PASS": 1.0,
        "WARNING": 0.5,
        "FAIL": 0.0,
        "NOT_APPLICABLE": 1.0,
    }

    weighted_total = 0.0
    total_weight = 0.0

    findings = []

    for check in checks.values():

        for item in check.get("findings", []):
            findings.append(item)

            check_id = item.get("id")

            weight = weights.get(
                check_id,
                1,
            )

            status = item.get(
                "status",
                "WARNING",
            )

            weighted_total += (
                weight *
                status_scores.get(status, 0.0)
            )

            total_weight += weight

    score = (
        weighted_total / total_weight * 100
        if total_weight
        else 0
    )

    critical = sum(
        1
        for item in findings
        if item.get("severity") == "CRITICAL"
        and item.get("status") == "FAIL"
    )

    high = sum(
        1
        for item in findings
        if item.get("severity") == "HIGH"
        and item.get("status") == "FAIL"
    )

    failures = [
        item
        for item in findings
        if item.get("status") == "FAIL"
    ]

    warnings = [
        item
        for item in findings
        if item.get("status") == "WARNING"
    ]

    if critical > 0:
        risk = "CRITICAL"
    elif high > 0:
        risk = "HIGH"
    elif score < 70:
        risk = "HIGH"
    elif score < 85:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    if critical > 0 or high > 0:
        status = "FAIL"
    elif score >= 85:
        status = "PASS"
    elif score >= 70:
        status = "CONDITIONAL"
    else:
        status = "FAIL"

    return {
        "score": round(score, 2),
        "status": status,
        "risk": risk,
        "critical_failures": critical,
        "high_failures": high,
        "failure_count": len(failures),
        "warning_count": len(warnings),
        "findings": findings,
    }


def run_production_audit(
    project_dir: str | Path,
) -> dict[str, Any]:

    project_dir = Path(project_dir)

    files = collect_files(project_dir)

    checks = {
        "debug": check_debug_configuration(
            files,
            project_dir,
        ),
        "secrets": check_secret_files(
            files,
            project_dir,
        ),
        "environment": check_environment_configuration(
            files,
            project_dir,
        ),
        "cors": check_cors(
            files,
            project_dir,
        ),
        "docker": check_docker(
            files,
            project_dir,
        ),
        "dependencies": check_dependencies(
            files,
            project_dir,
        ),
        "documentation": check_documentation(
            files,
            project_dir,
        ),
        "health": check_health_endpoint(
            files,
            project_dir,
        ),
        "logging": check_logging(
            files,
            project_dir,
        ),
        "api": check_api_documentation(
            files,
            project_dir,
        ),
        "startup": check_startup(
            files,
            project_dir,
        ),
        "error_handling": check_error_handling(
            files,
            project_dir,
        ),
    }

    score = calculate_production_score(
        checks
    )

    return {
        "enabled": True,
        "status": score["status"],
        "risk": score["risk"],
        "score": score["score"],
        "checks": checks,
        "findings": score["findings"],
        "critical_failures": score["critical_failures"],
        "high_failures": score["high_failures"],
        "failure_count": score["failure_count"],
        "warning_count": score["warning_count"],
    }