"""
Backward-compatible scanner interface.

The actual security scanning implementation lives in
core.security_audit.

This module keeps the older scanner API available so that
existing code does not break.
"""

from core.security_audit import (
    run_bandit,
    run_semgrep,
    run_gitleaks,
    run_osv_scanner,
    run_secret_heuristics,
    run_security_audit,
)


def run_scanners(project_dir):
    """
    Run all security scanners.

    Compatibility wrapper around run_security_audit().
    """

    return run_security_audit(
        project_dir,
        enabled=True,
    )


def scan_project(project_dir):
    """
    Compatibility alias.
    """

    return run_scanners(project_dir)


def run_all_scanners(project_dir):
    """
    Compatibility alias.
    """

    return run_scanners(project_dir)


__all__ = [
    "run_bandit",
    "run_semgrep",
    "run_gitleaks",
    "run_osv_scanner",
    "run_secret_heuristics",
    "run_security_audit",
    "run_scanners",
    "scan_project",
    "run_all_scanners",
]