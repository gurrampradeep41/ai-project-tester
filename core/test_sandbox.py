"""
Docker-based isolated project test execution.

The uploaded project is NOT executed directly on the host.

The sandbox applies:
- memory limit
- CPU limit
- PID limit
- network disabled
- dropped Linux capabilities
- no-new-privileges
- read-only filesystem
- temporary writable directories
- execution timeout

This is an isolation layer, not a claim of perfect security.
"""

from pathlib import Path
import shutil
import subprocess
import uuid


DOCKER_TIMEOUT = 180
MEMORY_LIMIT = "512m"
CPU_LIMIT = "1.0"
PIDS_LIMIT = "128"


def docker_available():
    """
    Check whether Docker CLI is available.
    """

    if not shutil.which("docker"):
        return False

    try:
        result = subprocess.run(
            [
                "docker",
                "info",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            shell=False,
        )

        return result.returncode == 0

    except Exception:
        return False


def _run_command(
    command,
    cwd=None,
    timeout=DOCKER_TIMEOUT,
):
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )

        try:
            stdout, stderr = process.communicate(
                timeout=timeout
            )

        except subprocess.TimeoutExpired:
            process.kill()

            stdout, stderr = process.communicate()

            return {
                "returncode": None,
                "stdout": stdout or "",
                "stderr": stderr or "",
                "timeout": True,
            }

        return {
            "returncode": process.returncode,
            "stdout": stdout or "",
            "stderr": stderr or "",
        }

    except Exception as exc:
        return {
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "error": True,
        }


def detect_test_framework(project_dir):
    """
    Detect a supported test framework.
    """

    project_dir = Path(project_dir)

    python_test_files = list(
        project_dir.rglob("test_*.py")
    )

    python_test_files += list(
        project_dir.rglob("*_test.py")
    )

    python_requirements = (
        project_dir / "requirements.txt"
    )

    pyproject = (
        project_dir / "pyproject.toml"
    )

    package_json = (
        project_dir / "package.json"
    )

    if python_test_files:
        return "python"

    if (
        python_requirements.exists()
        or pyproject.exists()
    ):
        if any(
            project_dir.rglob("*.py")
        ):
            return "python"

    if package_json.exists():
        return "node"

    return None


def _has_python_tests(project_dir):
    project_dir = Path(project_dir)

    return bool(
        list(
            project_dir.rglob("test_*.py")
        )
        or list(
            project_dir.rglob("*_test.py")
        )
    )


def _has_node_tests(project_dir):
    package_json = (
        Path(project_dir)
        / "package.json"
    )

    if not package_json.exists():
        return False

    try:
        text = package_json.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        return (
            '"test"' in text
            and "scripts" in text
        )

    except Exception:
        return False


def _build_python_dockerfile():
    return """
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /workspace

COPY . /workspace

RUN rm -rf /workspace/.git \\
    /workspace/.env \\
    /workspace/.env.* \\
    /workspace/__pycache__ \\
    /workspace/.pytest_cache

RUN python -m pip install --no-cache-dir --upgrade pip

RUN if [ -f requirements.txt ]; then \\
        pip install --no-cache-dir --ignore-installed -r requirements.txt; \\
    fi

RUN if [ -f pyproject.toml ]; then \\
        pip install --no-cache-dir . || true; \\
    fi

CMD ["pytest", "-q"]
""".strip()


def _build_node_dockerfile():
    return """
FROM node:22-bookworm-slim

WORKDIR /workspace

COPY . /workspace

RUN rm -rf /workspace/.git \\
    /workspace/.env \\
    /workspace/.env.* \\
    /workspace/node_modules

RUN if [ -f package-lock.json ]; then \\
        npm ci --ignore-scripts; \\
    elif [ -f package.json ]; then \\
        npm install --ignore-scripts; \\
    fi

CMD ["npm", "test", "--", "--runInBand"]
""".strip()


def _write_sandbox_dockerfile(
    project_dir,
    framework,
):
    if framework == "python":
        content = _build_python_dockerfile()

    elif framework == "node":
        content = _build_node_dockerfile()

    else:
        raise ValueError(
            f"Unsupported framework: {framework}"
        )

    dockerfile = (
        Path(project_dir)
        / ".ai_project_tester_Dockerfile"
    )

    dockerfile.write_text(
        content,
        encoding="utf-8",
    )

    return dockerfile


def _safe_output(text, limit=10000):
    if not text:
        return ""

    return str(text)[-limit:]


def _docker_cleanup_container(container_name):
    """
    Remove a potentially running test container.

    UTF-8 decoding is explicitly configured for Windows.
    """

    try:
        subprocess.run(
            [
                "docker",
                "rm",
                "-f",
                container_name,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            shell=False,
        )
    except Exception:
        pass


def _docker_cleanup_image(image_name):
    """
    Remove temporary Docker image.

    UTF-8 decoding is explicitly configured for Windows.
    """

    try:
        subprocess.run(
            [
                "docker",
                "image",
                "rm",
                "-f",
                image_name,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            shell=False,
        )
    except Exception:
        pass


def run_docker_tests(
    project_dir,
    timeout=DOCKER_TIMEOUT,
):
    """
    Build and execute project tests inside Docker.
    """

    project_dir = Path(project_dir)

    if not docker_available():
        return {
            "status": "NOT_ASSESSED",
            "framework": None,
            "exit_code": None,
            "stdout": "",
            "stderr": "Docker is unavailable.",
        }

    framework = detect_test_framework(
        project_dir
    )

    if framework is None:
        return {
            "status": "NOT_ASSESSED",
            "framework": None,
            "exit_code": None,
            "stdout": "",
            "stderr": (
                "No supported test framework detected."
            ),
        }

    dockerfile = _write_sandbox_dockerfile(
        project_dir,
        framework,
    )

    suffix = uuid.uuid4().hex[:12]

    image_name = (
        f"ai-project-tester-test-{suffix}"
    )

    container_name = (
        f"ai-project-tester-container-{suffix}"
    )

    try:
        # -------------------------------------------------
        # BUILD
        # -------------------------------------------------

        build_result = _run_command(
            [
                "docker",
                "build",
                "--file",
                str(dockerfile),
                "--tag",
                image_name,
                str(project_dir),
            ],
            cwd=project_dir,
            timeout=timeout,
        )

        if build_result.get("timeout"):
            return {
                "status": "BUILD_FAILED",
                "framework": framework,
                "exit_code": None,
                "stdout": _safe_output(
                    build_result["stdout"]
                ),
                "stderr": _safe_output(
                    build_result["stderr"]
                ),
            }

        if build_result.get("returncode") != 0:
            return {
                "status": "BUILD_FAILED",
                "framework": framework,
                "exit_code": build_result.get(
                    "returncode"
                ),
                "stdout": _safe_output(
                    build_result["stdout"]
                ),
                "stderr": _safe_output(
                    build_result["stderr"]
                ),
            }

        # -------------------------------------------------
        # TEST
        # -------------------------------------------------

        test_command = [
            "docker",
            "run",
            "--name",
            container_name,
            "--rm",
            "--memory",
            MEMORY_LIMIT,
            "--cpus",
            CPU_LIMIT,
            "--pids-limit",
            PIDS_LIMIT,
            "--network",
            "none",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=100m",
            "--tmpfs",
            "/run:rw,noexec,nosuid,size=50m",
            image_name,
        ]

        test_result = _run_command(
            test_command,
            cwd=project_dir,
            timeout=timeout,
        )

        if test_result.get("timeout"):

            _docker_cleanup_container(
                container_name
            )

            return {
                "status": "TIMEOUT",
                "framework": framework,
                "exit_code": None,
                "stdout": _safe_output(
                    test_result["stdout"]
                ),
                "stderr": _safe_output(
                    test_result["stderr"]
                ),
            }

        exit_code = test_result.get(
            "returncode"
        )

        if exit_code == 0:
            status = "PASSED"

        elif exit_code is None:
            status = "ERROR"

        else:
            status = "FAILED"

        return {
            "status": status,
            "framework": framework,
            "exit_code": exit_code,
            "stdout": _safe_output(
                test_result["stdout"]
            ),
            "stderr": _safe_output(
                test_result["stderr"]
            ),
        }

    finally:

        try:
            dockerfile.unlink(
                missing_ok=True
            )
        except Exception:
            pass

        _docker_cleanup_image(
            image_name
        )


# Compatibility aliases

def run_sandbox_tests(
    project_dir,
    timeout=DOCKER_TIMEOUT,
):
    return run_docker_tests(
        project_dir,
        timeout=timeout,
    )


def run_project_tests(
    project_dir,
    timeout=DOCKER_TIMEOUT,
):
    return run_docker_tests(
        project_dir,
        timeout=timeout,
    )