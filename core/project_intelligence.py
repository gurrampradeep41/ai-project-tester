"""
Project intelligence layer.

This module performs static analysis only.
It does not execute uploaded project code.
"""

from pathlib import Path


def _safe_list(value):
    if isinstance(value, list):
        return value
    return []


def analyze_project_intelligence(project_dir):
    """
    Build a normalized project-intelligence report.

    The function is compatible with the flat structure returned
    by core.project.analyze_project().
    """

    project_dir = Path(project_dir)

    if not project_dir.exists():
        return {
            "file_count": 0,
            "languages": [],
            "frameworks": [],
            "dependencies": [],
            "databases": [],
            "apis": [],
            "ai_tools": [],
            "configuration": [],
            "tests": [],
            "documentation": [],
            "entry_points": [],
            "files": [],
        }

    # Import here to avoid circular imports.
    from core.project import analyze_project

    project = analyze_project(project_dir)

    return {
        "file_count": int(
            project.get("file_count", 0)
        ),
        "languages": _safe_list(
            project.get("languages")
        ),
        "frameworks": _safe_list(
            project.get("frameworks")
        ),
        "dependencies": _safe_list(
            project.get("dependencies")
        ),
        "databases": _safe_list(
            project.get("databases")
        ),
        "apis": _safe_list(
            project.get("apis")
        ),
        "ai_tools": _safe_list(
            project.get("ai_tools")
        ),
        "configuration": _safe_list(
            project.get("configuration")
        ),
        "tests": _safe_list(
            project.get("tests")
        ),
        "documentation": _safe_list(
            project.get("documentation")
        ),
        "entry_points": _safe_list(
            project.get("entry_points")
        ),
        "files": _safe_list(
            project.get("files")
        ),
    }


def build_project_summary(project):
    """
    Create a short human-readable project summary.
    """

    if not isinstance(project, dict):
        return "No project intelligence available."

    file_count = project.get(
        "file_count",
        0,
    )

    languages = project.get(
        "languages",
        [],
    )

    frameworks = project.get(
        "frameworks",
        [],
    )

    dependencies = project.get(
        "dependencies",
        [],
    )

    tests = project.get(
        "tests",
        [],
    )

    return (
        f"Project contains {file_count} files. "
        f"Languages: {', '.join(languages) or 'None detected'}. "
        f"Frameworks: {', '.join(frameworks) or 'None detected'}. "
        f"Dependency files: {len(dependencies)}. "
        f"Test files/configurations: {len(tests)}."
    )


# Compatibility aliases
analyze_project = analyze_project_intelligence
get_project_intelligence = analyze_project_intelligence