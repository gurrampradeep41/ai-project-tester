# core/phase8/report_builder.py

from __future__ import annotations

from html import escape
from typing import Any


def build_executive_summary(
    result: dict[str, Any],
) -> dict[str, Any]:

    final_score = result.get(
        "final_score",
        {}
    )

    release_gate = result.get(
        "release_gate",
        {}
    )

    production = result.get(
        "production_readiness",
        {}
    )

    requirement_score = result.get(
        "requirement_score",
        {}
    )

    security = result.get(
        "security",
        {}
    )

    testing = result.get(
        "testing",
        {}
    )

    ai = result.get(
        "ai",
        {}
    )

    remediation = result.get(
        "remediation_plan",
        []
    )

    return {
        "audit_id": result.get(
            "audit_id",
            "N/A",
        ),

        "final_score": final_score.get(
            "score",
            0,
        ),

        "release_status": release_gate.get(
            "status",
            "UNKNOWN",
        ),

        "production_score": production.get(
            "score",
            0,
        ),

        "requirement_score": requirement_score.get(
            "score",
            0,
        ),

        "security_score": security.get(
            "score",
            0,
        ),

        "testing_score": testing.get(
            "score",
            0,
        ),

        "ai_score": ai.get(
            "score",
            0,
        ),

        "open_remediation_items": len(
            remediation
        ),
    }


def build_executive_html(
    result: dict[str, Any],
) -> str:

    summary = build_executive_summary(
        result
    )

    status = escape(
        str(
            summary[
                "release_status"
            ]
        )
    )

    score = summary[
        "final_score"
    ]

    return f"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<title>
AI Project Tester - Executive Audit
</title>

<style>

body {{
    font-family: Arial, sans-serif;
    margin: 40px;
    color: #222;
}}

h1 {{
    margin-bottom: 5px;
}}

.subtitle {{
    color: #666;
    margin-bottom: 30px;
}}

.grid {{
    display: grid;
    grid-template-columns:
        repeat(3, 1fr);
    gap: 16px;
}}

.card {{
    border: 1px solid #ddd;
    border-radius: 10px;
    padding: 20px;
}}

.score {{
    font-size: 32px;
    font-weight: bold;
}}

.status {{
    font-size: 24px;
    font-weight: bold;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 30px;
}}

th, td {{
    border: 1px solid #ddd;
    padding: 10px;
    text-align: left;
}}

</style>

</head>

<body>

<h1>
AI Project Tester
</h1>

<div class="subtitle">
Pre-Deployment Software Quality & Release-Readiness Audit
</div>

<div class="card">

<div>
Audit ID
</div>

<strong>
{escape(str(summary["audit_id"]))}
</strong>

</div>

<br>

<div class="grid">

<div class="card">

<div>
Final Score
</div>

<div class="score">
{score}/100
</div>

</div>

<div class="card">

<div>
Release Status
</div>

<div class="status">
{status}
</div>

</div>

<div class="card">

<div>
Open Remediation Items
</div>

<div class="score">
{summary["open_remediation_items"]}
</div>

</div>

</div>

<h2>
Component Scores
</h2>

<table>

<tr>
<th>Component</th>
<th>Score</th>
</tr>

<tr>
<td>Requirements</td>
<td>{summary["requirement_score"]}/100</td>
</tr>

<tr>
<td>Security</td>
<td>{summary["security_score"]}/100</td>
</tr>

<tr>
<td>Testing</td>
<td>{summary["testing_score"]}/100</td>
</tr>

<tr>
<td>AI</td>
<td>{summary["ai_score"]}/100</td>
</tr>

<tr>
<td>Production</td>
<td>{summary["production_score"]}/100</td>
</tr>

</table>

<h2>
Release Decision
</h2>

<p>
<strong>{status}</strong>
</p>

</body>

</html>
"""