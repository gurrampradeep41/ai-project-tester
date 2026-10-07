"""
Safe project ZIP extraction and static project analysis.
"""

from pathlib import Path
import re
import shutil
import zipfile


MAX_ZIP_SIZE = 100 * 1024 * 1024
MAX_EXTRACTED_SIZE = 500 * 1024 * 1024

IGNORED_DIRS = {
    ".git",
    ".svn",
    ".hg",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    ".next",
}


LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++",
    ".hpp": "C++",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".html": "HTML",
    ".css": "CSS",
    ".sql": "SQL",
}


def _safe_member_path(base_dir, member_name):
    base = Path(base_dir).resolve()

    raw = member_name.replace("\\", "/")

    if raw.startswith("/"):
        raise ValueError(
            f"Unsafe absolute ZIP path: {member_name}"
        )

    if re.match(r"^[A-Za-z]:", raw):
        raise ValueError(
            f"Unsafe drive path: {member_name}"
        )

    destination = (base / raw).resolve()

    if destination != base and base not in destination.parents:
        raise ValueError(
            f"Unsafe ZIP path: {member_name}"
        )

    return destination


def extract_zip_safely(zip_path, extract_to):
    """
    Safely extract ZIP contents.

    Protects against:
    - Zip Slip
    - absolute paths
    - drive-letter paths
    - excessive extraction size
    """

    zip_path = Path(zip_path)
    extract_to = Path(extract_to)

    if not zip_path.exists():
        raise FileNotFoundError(
            f"ZIP file not found: {zip_path}"
        )

    if zip_path.stat().st_size > MAX_ZIP_SIZE:
        raise ValueError(
            "ZIP file exceeds the 100 MB limit."
        )

    extract_to.mkdir(
        parents=True,
        exist_ok=True,
    )

    total_size = 0

    with zipfile.ZipFile(zip_path, "r") as archive:
        for info in archive.infolist():

            if info.is_dir():
                _safe_member_path(
                    extract_to,
                    info.filename,
                )
                continue

            total_size += info.file_size

            if total_size > MAX_EXTRACTED_SIZE:
                raise ValueError(
                    "Extracted project exceeds the 500 MB limit."
                )

            destination = _safe_member_path(
                extract_to,
                info.filename,
            )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with archive.open(info, "r") as source:
                with open(destination, "wb") as target:
                    shutil.copyfileobj(
                        source,
                        target,
                    )

    return extract_to


def _discover_files(project_dir):
    project_dir = Path(project_dir)

    files = []

    for path in project_dir.rglob("*"):
        if not path.is_file():
            continue

        relative = path.relative_to(
            project_dir
        )

        if any(
            part in IGNORED_DIRS
            for part in relative.parts
        ):
            continue

        files.append(
            str(relative).replace("\\", "/")
        )

    return sorted(files)


def _detect_languages(files):
    languages = set()

    for file in files:
        suffix = Path(file).suffix.lower()

        language = LANGUAGE_EXTENSIONS.get(
            suffix
        )

        if language:
            languages.add(language)

    return sorted(languages)


def _detect_frameworks(files):
    names = {
        file.lower()
        for file in files
    }

    frameworks = []

    checks = {
        "FastAPI": [
            "fastapi",
        ],
        "Flask": [
            "flask",
        ],
        "Django": [
            "manage.py",
            "django",
        ],
        "Streamlit": [
            "streamlit",
        ],
        "React": [
            "package.json",
            "react",
        ],
        "Next.js": [
            "next.config.js",
            "next.config.mjs",
        ],
        "Angular": [
            "angular.json",
        ],
        "Vue": [
            "vue",
        ],
        "Express": [
            "express",
        ],
    }

    for framework, keywords in checks.items():
        for keyword in keywords:
            if any(
                keyword in name
                for name in names
            ):
                frameworks.append(framework)
                break

    return sorted(set(frameworks))


def _detect_tests(files):
    test_files = []

    for file in files:
        name = Path(file).name.lower()

        if (
            name.startswith("test_")
            or name.endswith("_test.py")
            or "/tests/" in f"/{file.lower()}"
            or name in {
                "pytest.ini",
                "tox.ini",
                "jest.config.js",
                "vitest.config.js",
            }
        ):
            test_files.append(file)

    return test_files


def _detect_documentation(files):
    return [
        file
        for file in files
        if Path(file).name.lower()
        in {
            "readme.md",
            "readme.txt",
            "readme",
            "documentation.md",
            "docs.md",
        }
    ]


def _detect_configuration(files):
    config_names = {
        ".env",
        ".env.example",
        "config.py",
        "settings.py",
        "config.json",
        "config.yaml",
        "config.yml",
        "docker-compose.yml",
        "docker-compose.yaml",
        "Dockerfile",
    }

    return [
        file
        for file in files
        if Path(file).name in config_names
    ]


def _detect_entry_points(files):
    entry_names = {
        "app.py",
        "main.py",
        "server.py",
        "manage.py",
        "index.js",
        "server.js",
        "main.js",
        "main.ts",
        "index.ts",
    }

    return [
        file
        for file in files
        if Path(file).name.lower()
        in {
            name.lower()
            for name in entry_names
        }
    ]


def _detect_dependencies(files):
    dependency_files = {
        "requirements.txt",
        "pyproject.toml",
        "poetry.lock",
        "pipfile",
        "pipfile.lock",
        "package.json",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "pom.xml",
        "build.gradle",
        "go.mod",
        "cargo.toml",
    }

    return [
        file
        for file in files
        if Path(file).name.lower()
        in dependency_files
    ]


def _detect_databases(files):
    text = " ".join(
        file.lower()
        for file in files
    )

    databases = []

    checks = {
        "MySQL": ["mysql"],
        "PostgreSQL": ["postgres", "psycopg"],
        "SQLite": ["sqlite"],
        "MongoDB": ["mongo"],
        "Redis": ["redis"],
    }

    for name, keywords in checks.items():
        if any(
            keyword in text
            for keyword in keywords
        ):
            databases.append(name)

    return sorted(set(databases))


def _detect_apis(files):
    api_files = []

    for file in files:
        lower = file.lower()

        if any(
            keyword in lower
            for keyword in [
                "api",
                "route",
                "endpoint",
                "controller",
            ]
        ):
            api_files.append(file)

    return api_files[:100]


def _detect_ai_tools(files):
    text = " ".join(
        file.lower()
        for file in files
    )

    tools = []

    checks = {
        "OpenAI": ["openai"],
        "Groq": ["groq"],
        "Ollama": ["ollama"],
        "LangChain": ["langchain"],
        "LlamaIndex": ["llamaindex"],
        "Transformers": ["transformers"],
        "PyTorch": ["torch", "pytorch"],
        "TensorFlow": ["tensorflow"],
    }

    for name, keywords in checks.items():
        if any(
            keyword in text
            for keyword in keywords
        ):
            tools.append(name)

    return sorted(set(tools))


def analyze_project(project_dir):
    """
    Static project intelligence.
    """

    project_dir = Path(project_dir)

    files = _discover_files(
        project_dir
    )

    return {
        "file_count": len(files),
        "languages": _detect_languages(files),
        "frameworks": _detect_frameworks(files),
        "dependencies": _detect_dependencies(files),
        "databases": _detect_databases(files),
        "apis": _detect_apis(files),
        "ai_tools": _detect_ai_tools(files),
        "configuration": _detect_configuration(files),
        "tests": _detect_tests(files),
        "documentation": _detect_documentation(files),
        "entry_points": _detect_entry_points(files),
        "files": files,
    }