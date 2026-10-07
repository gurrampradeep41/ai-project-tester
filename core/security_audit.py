"""
Security audit layer.

Runs:
- Bandit
- Semgrep
- Gitleaks
- OSV-Scanner
- Local secret heuristics

Important:
- Missing scanners are NOT treated as clean.
- Secret values are never returned.
- Subprocess output is decoded safely as UTF-8.
"""

from pathlib import Path
import json
import os
import re
import shutil
import subprocess


DEFAULT_TIMEOUT = 120

SCANNERS = [
    "bandit",
    "semgrep",
    "gitleaks",
    "osv",
    "secret_heuristics",
]


def _run_command(
    command,
    cwd=None,
    timeout=DEFAULT_TIMEOUT,
):
    """
    Execute a scanner command safely without shell=True.

    Windows-safe:
    subprocess output is explicitly decoded as UTF-8.
    Invalid bytes are replaced instead of crashing the application.
    """

    try:
        process = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
        )

        return {
            "returncode": process.returncode,
            "stdout": process.stdout or "",
            "stderr": process.stderr or "",
            "status": "COMPLETED",
        }

    except FileNotFoundError:
        return {
            "returncode": None,
            "stdout": "",
            "stderr": "Tool not installed.",
            "status": "NOT_INSTALLED",
        }

    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""

        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")

        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")

        return {
            "returncode": None,
            "stdout": stdout,
            "stderr": "Scanner timed out.",
            "status": "TIMEOUT",
        }

    except Exception as exc:
        return {
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "status": "ERROR",
        }


def _safe_json(text):
    if not text:
        return {}

    try:
        return json.loads(text)
    except Exception:
        return {}


def _finding(
    scanner,
    severity="MEDIUM",
    message="",
    file_path=None,
    line=None,
    rule=None,
):
    return {
        "scanner": scanner,
        "severity": str(
            severity or "MEDIUM"
        ).upper(),
        "message": str(message)[:1000],
        "file": file_path,
        "line": line,
        "rule": rule,
    }


def _severity_from_bandit(value):
    value = str(value or "").upper()

    if value == "HIGH":
        return "HIGH"

    if value == "MEDIUM":
        return "MEDIUM"

    if value == "LOW":
        return "LOW"

    return "MEDIUM"


def run_bandit(project_dir):
    """
    Run Bandit against Python source files.
    """

    if not shutil.which("bandit"):
        return {
            "status": "NOT_INSTALLED",
            "findings": [],
            "error": "Bandit is not installed.",
        }

    result = _run_command(
        [
            "bandit",
            "-r",
            str(project_dir),
            "-f",
            "json",
        ],
        cwd=project_dir,
    )

    if result["status"] != "COMPLETED":
        return {
            "status": result["status"],
            "findings": [],
            "error": result["stderr"],
        }

    data = _safe_json(result["stdout"])

    findings = []

    for item in data.get("results", []):
        findings.append(
            _finding(
                scanner="bandit",
                severity=_severity_from_bandit(
                    item.get("issue_severity")
                ),
                message=item.get(
                    "issue_text",
                    "Bandit security finding.",
                ),
                file_path=item.get("filename"),
                line=item.get("line_number"),
                rule=item.get("test_id"),
            )
        )

    return {
        "status": "COMPLETED",
        "findings": findings,
        "error": None,
    }


def run_semgrep(project_dir):
    """
    Run Semgrep using automatic configuration.
    """

    if not shutil.which("semgrep"):
        return {
            "status": "NOT_INSTALLED",
            "findings": [],
            "error": "Semgrep is not installed.",
        }

    result = _run_command(
        [
            "semgrep",
            "--config",
            "auto",
            "--json",
            str(project_dir),
        ],
        cwd=project_dir,
    )

    if result["status"] != "COMPLETED":
        return {
            "status": result["status"],
            "findings": [],
            "error": result["stderr"],
        }

    data = _safe_json(result["stdout"])

    findings = []

    for item in data.get("results", []):
        extra = item.get("extra", {})
        metadata = extra.get("metadata", {})

        severity = metadata.get(
            "severity",
            "MEDIUM",
        )

        findings.append(
            _finding(
                scanner="semgrep",
                severity=str(
                    severity
                ).upper(),
                message=extra.get(
                    "message",
                    "Semgrep finding.",
                ),
                file_path=item.get("path"),
                line=item.get(
                    "start",
                    {},
                ).get("line"),
                rule=item.get("check_id"),
            )
        )

    return {
        "status": "COMPLETED",
        "findings": findings,
        "error": None,
    }


def run_gitleaks(project_dir):
    """
    Run Gitleaks with redaction enabled.

    Secret values are never returned.
    """

    if not shutil.which("gitleaks"):
        return {
            "status": "NOT_INSTALLED",
            "findings": [],
            "error": "Gitleaks is not installed.",
        }

    report_file = (
        Path(project_dir)
        / ".ai_project_tester_gitleaks.json"
    )

    try:
        result = _run_command(
            [
                "gitleaks",
                "detect",
                "--source",
                str(project_dir),
                "--no-banner",
                "--redact",
                "--report-format",
                "json",
                "--report-path",
                str(report_file),
            ],
            cwd=project_dir,
        )

        if result["status"] != "COMPLETED":
            return {
                "status": result["status"],
                "findings": [],
                "error": result["stderr"],
            }

        findings = []

        if report_file.exists():
            try:
                with open(
                    report_file,
                    "r",
                    encoding="utf-8",
                    errors="replace",
                ) as handle:
                    data = json.load(handle)

                if isinstance(data, list):
                    for item in data:
                        findings.append(
                            _finding(
                                scanner="gitleaks",
                                severity="CRITICAL",
                                message=(
                                    "Potential leaked secret "
                                    "detected. Secret value redacted."
                                ),
                                file_path=item.get("File"),
                                line=item.get("StartLine"),
                                rule=item.get("RuleID"),
                            )
                        )

            except Exception:
                return {
                    "status": "ERROR",
                    "findings": [],
                    "error": (
                        "Unable to parse Gitleaks output."
                    ),
                }

        return {
            "status": "COMPLETED",
            "findings": findings,
            "error": None,
        }

    finally:
        try:
            if report_file.exists():
                report_file.unlink()
        except Exception:
            pass


def run_osv_scanner(project_dir):
    """
    Run OSV-Scanner.

    CLI syntax can vary between OSV-Scanner versions.
    """

    if not shutil.which("osv-scanner"):
        return {
            "status": "NOT_INSTALLED",
            "findings": [],
            "error": "OSV-Scanner is not installed.",
        }

    result = _run_command(
        [
            "osv-scanner",
            "scan",
            "source",
            "-r",
            str(project_dir),
            "--format",
            "json",
        ],
        cwd=project_dir,
    )

    if result["status"] != "COMPLETED":
        return {
            "status": result["status"],
            "findings": [],
            "error": result["stderr"],
        }

    data = _safe_json(result["stdout"])

    findings = []

    results = data.get("results", [])

    for result_item in results:
        packages = result_item.get(
            "packages",
            [],
        )

        for package_item in packages:
            package = package_item.get(
                "package",
                {},
            )

            package_name = package.get(
                "name",
                "Unknown package",
            )

            vulnerabilities = package_item.get(
                "vulnerabilities",
                [],
            )

            for vulnerability in vulnerabilities:
                vuln_id = vulnerability.get(
                    "id",
                    "Unknown vulnerability",
                )

                severity = "HIGH"

                database_specific = vulnerability.get(
                    "database_specific",
                    {},
                )

                severity_value = database_specific.get(
                    "severity"
                )

                if severity_value:
                    severity = str(
                        severity_value
                    ).upper()

                findings.append(
                    _finding(
                        scanner="osv",
                        severity=severity,
                        message=(
                            f"{package_name}: "
                            f"{vuln_id}"
                        ),
                        file_path=None,
                        line=None,
                        rule=vuln_id,
                    )
                )

    return {
        "status": "COMPLETED",
        "findings": findings,
        "error": None,
    }


SECRET_PATTERNS = [
    (
        "AWS access key",
        re.compile(
            r"\bAKIA[0-9A-Z]{16}\b"
        ),
    ),
    (
        "Generic API key",
        re.compile(
            r"""(?i)\b(api[\_-]?key|apikey)\s*[:=]\s*['"][^'"]{12,}['"]"""
        ),
    ),
    (
        "Generic secret",
        re.compile(
            r"""(?i)\b(secret|token|password)\s*[:=]\s*['"][^'"]{8,}['"]"""
        ),
    ),
    (
        "Private key",
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----"
        ),
    ),
]


def run_secret_heuristics(project_dir):
    """
    Lightweight fallback secret detection.

    Values are never returned.
    """

    findings = []

    project_dir = Path(project_dir)

    for path in project_dir.rglob("*"):

        if not path.is_file():
            continue

        if any(
            part in {
                ".git",
                "node_modules",
                "__pycache__",
                ".venv",
                "venv",
            }
            for part in path.parts
        ):
            continue

        try:
            if path.stat().st_size > 2 * 1024 * 1024:
                continue
        except OSError:
            continue

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except Exception:
            continue

        for description, pattern in SECRET_PATTERNS:

            for match in pattern.finditer(text):

                line_number = (
                    text.count(
                        "\n",
                        0,
                        match.start(),
                    )
                    + 1
                )

                findings.append(
                    _finding(
                        scanner="secret_heuristics",
                        severity="LOW",
                        message=(
                            f"Potential {description} "
                            "detected. Value redacted."
                        ),
                        file_path=str(
                            path.relative_to(
                                project_dir
                            )
                        ),
                        line=line_number,
                        rule="LOCAL_SECRET_HEURISTIC",
                    )
                )

    return {
        "status": "COMPLETED",
        "findings": findings[:100],
        "error": None,
    }


def _calculate_overall_status(tools):
    statuses = [
        item.get("status")
        for item in tools.values()
    ]

    if not statuses:
        return "NOT_ASSESSED"

    if all(
        status == "COMPLETED"
        for status in statuses
    ):
        return "COMPLETED"

    if all(
        status in {
            "NOT_INSTALLED",
            "NOT_APPLICABLE",
        }
        for status in statuses
    ):
        return "NOT_ASSESSED"

    if any(
        status == "ERROR"
        for status in statuses
    ):
        return "PARTIAL"

    if any(
        status == "TIMEOUT"
        for status in statuses
    ):
        return "PARTIAL"

    return "PARTIAL"


def _calculate_risk(findings, tools):
    severities = {
        str(
            item.get("severity", "")
        ).upper()
        for item in findings
    }

    if "CRITICAL" in severities:
        return "CRITICAL"

    if "HIGH" in severities:
        return "HIGH"

    if "MEDIUM" in severities:
        return "MEDIUM"

    if "LOW" in severities:
        return "LOW"

    if any(
        item.get("status")
        in {
            "NOT_INSTALLED",
            "ERROR",
            "TIMEOUT",
        }
        for item in tools.values()
    ):
        return "UNKNOWN"

    return "LOW"


def run_security_audit(
    project_dir,
    enabled=True,
):
    """
    Execute all configured security scanners.
    """

    if not enabled:
        return {
            "enabled": False,
            "status": "DISABLED",
            "risk": "UNKNOWN",
            "tools": {},
            "findings": [],
            "counts": {},
            "assessed_tools": [],
            "not_assessed_tools": SCANNERS.copy(),
        }

    project_dir = Path(project_dir)

    tools = {
        "bandit": run_bandit(project_dir),
        "semgrep": run_semgrep(project_dir),
        "gitleaks": run_gitleaks(project_dir),
        "osv": run_osv_scanner(project_dir),
        "secret_heuristics": run_secret_heuristics(
            project_dir
        ),
    }

    all_findings = []

    for result in tools.values():
        all_findings.extend(
            result.get(
                "findings",
                [],
            )
        )

    assessed_tools = [
        name
        for name, result in tools.items()
        if result.get("status") == "COMPLETED"
    ]

    not_assessed_tools = [
        name
        for name, result in tools.items()
        if result.get("status") != "COMPLETED"
    ]

    counts = {
        "bandit": sum(
            1
            for item in all_findings
            if item.get("scanner") == "bandit"
        ),
        "semgrep": sum(
            1
            for item in all_findings
            if item.get("scanner") == "semgrep"
        ),
        "gitleaks": sum(
            1
            for item in all_findings
            if item.get("scanner") == "gitleaks"
        ),
        "dependency_vulnerabilities": sum(
            1
            for item in all_findings
            if item.get("scanner") == "osv"
        ),
        "secret_heuristics": sum(
            1
            for item in all_findings
            if item.get("scanner") == "secret_heuristics"
        ),
    }

    return {
        "enabled": True,
        "status": _calculate_overall_status(tools),
        "risk": _calculate_risk(
            all_findings,
            tools,
        ),
        "tools": tools,
        "findings": all_findings,
        "counts": counts,
        "assessed_tools": assessed_tools,
        "not_assessed_tools": not_assessed_tools,
    }


# Compatibility alias
security_audit = run_security_audit