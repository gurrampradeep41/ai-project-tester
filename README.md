# AI Project Tester

AI-assisted pre-deployment software audit tool.

## MVP capabilities

- Upload ZIP project
- Safe ZIP extraction with path traversal protection
- Detect languages/frameworks
- Detect tests, documentation and configuration
- Compare client requirements heuristically
- Run optional Semgrep/Bandit/Gitleaks/ESLint scanners
- Run local Ollama AI audit
- Generate release status
- Download HTML and JSON audit reports

## Run

```bash
python -m venv venv
```

Windows:

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Optional local AI

Install Ollama separately and pull a model, for example:

```bash
ollama pull qwen3:4b
```

Then keep Ollama running and enable "Use local Ollama AI".

## Optional scanners

Install the scanners separately and make sure their commands are on PATH:

- Semgrep
- Bandit
- Gitleaks
- ESLint

The application still runs when these tools are unavailable.

## Important

This is an MVP. It does not prove that a project is bug-free or secure. It combines deterministic tools, heuristics and AI-assisted review. Production use should add sandboxed execution, authentication, resource limits, dependency scanning, API testing, browser testing, stronger requirement traceability and human approval.
