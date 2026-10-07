"""
HTML and JSON report generation.
"""

from datetime import datetime
import html
import json
from pathlib import Path


def _safe(value, default=""):
    if value is None:
        return default

    if isinstance(value, (dict, list)):
        return value

    return str(value)


def _escape(value):
    return html.escape(
        str(value)
    )


def _status_class(status):
    status = str(
        status or ""
    ).upper()

    if status in {
        "READY",
        "PASS",
        "PASSED",
        "LOW",
        "COMPLETED",
    }:
        return "good"

    if status in {
        "CONDITIONAL",
        "PARTIAL",
        "UNKNOWN",
        "NOT_ASSESSED",
    }:
        return "warning"

    if status in {
        "BLOCKED",
        "FAILED",
        "ERROR",
        "CRITICAL",
        "HIGH",
        "BUILD_FAILED",
        "TIMEOUT",
    }:
        return "bad"

    return "neutral"


def _findings_html(findings):
    if not findings:
        return """
        <div class="empty">
            No findings were reported by the available scanners.
        </div>
        """

    rows = []

    for finding in findings:
        if not isinstance(finding, dict):
            continue

        severity = finding.get(
            "severity",
            "UNKNOWN",
        )

        rows.append(
            f"""
            <tr>
                <td>
                    <span class="badge {_status_class(severity)}">
                        {_escape(severity)}
                    </span>
                </td>
                <td>{_escape(finding.get("scanner", ""))}</td>
                <td>{_escape(finding.get("message", ""))}</td>
                <td>{_escape(finding.get("file", ""))}</td>
                <td>{_escape(finding.get("line", ""))}</td>
                <td>{_escape(finding.get("rule", ""))}</td>
            </tr>
            """
        )

    if not rows:
        return """
        <div class="empty">
            No findings available.
        </div>
        """

    return f"""
    <table>
        <thead>
            <tr>
                <th>Severity</th>
                <th>Scanner</th>
                <th>Message</th>
                <th>File</th>
                <th>Line</th>
                <th>Rule</th>
            </tr>
        </thead>
        <tbody>
            {''.join(rows)}
        </tbody>
    </table>
    """


def generate_html_report(audit):
    """
    Generate a standalone HTML audit report.
    """

    audit = audit or {}

    generated_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    project = audit.get(
        "project",
        {},
    )

    requirements = audit.get(
        "requirements",
        {},
    )

    security = audit.get(
        "security_score",
        audit.get(
            "security",
            {},
        ),
    )

    testing = audit.get(
        "testing",
        audit.get(
            "test_score",
            {},
        ),
    )

    ai = audit.get(
        "ai",
        {},
    )

    final_score = audit.get(
        "final_score",
        {},
    )

    release_gate = audit.get(
        "release_gate",
        {},
    )

    if isinstance(
        release_gate,
        str,
    ):
        release_status = release_gate
    else:
        release_status = release_gate.get(
            "status",
            "UNKNOWN",
        )

    score = final_score.get(
        "score",
        0,
    ) if isinstance(
        final_score,
        dict,
    ) else 0

    languages = project.get(
        "languages",
        [],
    )

    frameworks = project.get(
        "frameworks",
        [],
    )

    findings = security.get(
        "findings",
        [],
    )

    if not findings:
        raw_security = audit.get(
            "security",
            {},
        )

        findings = raw_security.get(
            "findings",
            [],
        )

    requirement_items = requirements.get(
        "requirements",
        [],
    )

    requirement_rows = []

    for item in requirement_items:
        if not isinstance(item, dict):
            continue

        status = item.get(
            "status",
            "UNKNOWN",
        )

        evidence = item.get(
            "evidence",
            [],
        )

        if isinstance(
            evidence,
            list,
        ):
            evidence_text = "<br>".join(
                _escape(x)
                for x in evidence
            )
        else:
            evidence_text = _escape(
                evidence
            )

        requirement_rows.append(
            f"""
            <tr>
                <td>{_escape(item.get("requirement", ""))}</td>
                <td>
                    <span class="badge {_status_class(status)}">
                        {_escape(status)}
                    </span>
                </td>
                <td>{_escape(item.get("confidence", ""))}%</td>
                <td>{evidence_text}</td>
            </tr>
            """
        )

    testing_status = testing.get(
        "status",
        "UNKNOWN",
    )

    security_risk = security.get(
        "risk",
        "UNKNOWN",
    )

    html_report = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>AI Project Tester Report</title>

<style>
* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    padding: 0;
    font-family: Arial, Helvetica, sans-serif;
    background: #f4f6f8;
    color: #202124;
}}

.container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 32px;
}}

.header {{
    background: #ffffff;
    border-radius: 14px;
    padding: 28px;
    margin-bottom: 24px;
    border: 1px solid #e0e0e0;
}}

.header h1 {{
    margin: 0 0 8px 0;
}}

.header p {{
    margin: 5px 0;
    color: #666;
}}

.grid {{
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
}}

.card {{
    background: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 14px;
    padding: 20px;
}}

.card h3 {{
    margin-top: 0;
}}

.score {{
    font-size: 42px;
    font-weight: bold;
}}

.section {{
    background: #ffffff;
    border-radius: 14px;
    padding: 24px;
    margin-bottom: 24px;
    border: 1px solid #e0e0e0;
}}

.badge {{
    display: inline-block;
    padding: 5px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: bold;
}}

.good {{
    background: #d9f7df;
    color: #126b2d;
}}

.warning {{
    background: #fff0c7;
    color: #7a5600;
}}

.bad {{
    background: #ffdada;
    color: #9c1c1c;
}}

.neutral {{
    background: #e8eaed;
    color: #444;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 15px;
}}

th, td {{
    padding: 10px;
    border-bottom: 1px solid #e5e5e5;
    text-align: left;
    vertical-align: top;
}}

th {{
    background: #f7f7f7;
}}

ul {{
    line-height: 1.7;
}}

.empty {{
    padding: 18px;
    background: #f7f7f7;
    border-radius: 8px;
    color: #666;
}}

.footer {{
    color: #777;
    font-size: 13px;
    text-align: center;
    padding: 20px;
}}

@media print {{
    body {{
        background: white;
    }}

    .container {{
        max-width: none;
    }}
}}
</style>
</head>

<body>

<div class="container">

<div class="header">
    <h1>AI Project Tester</h1>

    <p>
        Pre-Deployment Software Quality & Release-Readiness Audit
    </p>

    <p>
        Generated: {_escape(generated_at)}
    </p>

    <p>
        <span class="badge {_status_class(release_status)}">
            Release Gate: {_escape(release_status)}
        </span>
    </p>
</div>


<div class="grid">

<div class="card">
    <h3>Final Score</h3>
    <div class="score">{_escape(score)}/100</div>
</div>

<div class="card">
    <h3>Requirements</h3>
    <div class="score">
        {_escape(requirements.get("score", 0))}
    </div>
</div>

<div class="card">
    <h3>Security</h3>
    <div class="score">
        {_escape(security.get("score", 0))}
    </div>
</div>

<div class="card">
    <h3>Testing</h3>
    <div class="score">
        {_escape(testing.get("score", 0))}
    </div>
</div>

</div>


<div class="section">
<h2>Project Intelligence</h2>

<p>
<strong>Files:</strong>
{_escape(project.get("file_count", 0))}
</p>

<p>
<strong>Languages:</strong>
{_escape(", ".join(languages) if languages else "None detected")}
</p>

<p>
<strong>Frameworks:</strong>
{_escape(", ".join(frameworks) if frameworks else "None detected")}
</p>

<p>
<strong>AI Tools:</strong>
{_escape(", ".join(project.get("ai_tools", [])) if project.get("ai_tools") else "None detected")}
</p>

</div>


<div class="section">
<h2>Requirements Coverage</h2>

<p>
{_escape(requirements.get("summary", ""))}
</p>

<p>
<strong>
Coverage:
{_escape(requirements.get("coverage_score", requirements.get("score", 0)))}%
</strong>
</p>

{
    f'''
    <table>
        <thead>
            <tr>
                <th>Requirement</th>
                <th>Status</th>
                <th>Confidence</th>
                <th>Evidence</th>
            </tr>
        </thead>
        <tbody>
            {"".join(requirement_rows)}
        </tbody>
    </table>
    '''
    if requirement_rows
    else '<div class="empty">No requirements were provided.</div>'
}

</div>


<div class="section">
<h2>Security Audit</h2>

<p>
<strong>Security risk:</strong>
<span class="badge {_status_class(security_risk)}">
{_escape(security_risk)}
</span>
</p>

<p>
<strong>Status:</strong>
{_escape(security.get("status", "UNKNOWN"))}
</p>

<p>
<strong>Total findings:</strong>
{_escape(security.get("total_findings", len(findings)))}
</p>

<p>
<strong>Scanner coverage:</strong>
{_escape(
    security.get(
        "coverage",
        {}
    ).get(
        "coverage_percent",
        0
    )
)}%
</p>

{_findings_html(findings)}

</div>


<div class="section">
<h2>Automated Testing</h2>

<p>
<strong>Status:</strong>

<span class="badge {_status_class(testing_status)}">
{_escape(testing_status)}
</span>
</p>

<p>
<strong>Score:</strong>
{_escape(testing.get("score", 0))}/100
</p>

<p>
{_escape(testing.get("summary", ""))}
</p>

</div>


<div class="section">
<h2>AI Audit</h2>

<p>
<strong>AI Score:</strong>
{_escape(ai.get("score", 0))}/100
</p>

<p>
{_escape(ai.get("summary", ""))}
</p>

</div>


<div class="section">
<h2>Release Decision</h2>

<p>
<span class="badge {_status_class(release_status)}">
{_escape(release_status)}
</span>
</p>

<ul>
{
    "".join(
        f"<li>{_escape(reason)}</li>"
        for reason in (
            release_gate.get("reasons", [])
            if isinstance(release_gate, dict)
            else []
        )
    )
}
</ul>

</div>


<div class="footer">
    AI Project Tester — Evidence-based pre-deployment audit.
    This report does not guarantee that software is bug-free,
    completely secure, or production-ready.
</div>

</div>

</body>
</html>
"""

    return html_report


def build_html_report(audit):
    """
    Backward-compatible alias.
    """
    return generate_html_report(audit)


def save_html_report(
    audit,
    output_path,
):
    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    content = generate_html_report(
        audit
    )

    output_path.write_text(
        content,
        encoding="utf-8",
    )

    return output_path


def generate_json_report(audit):
    """
    Generate formatted JSON report.
    """

    return json.dumps(
        audit or {},
        indent=2,
        ensure_ascii=False,
        default=str,
    )