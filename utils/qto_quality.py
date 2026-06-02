"""QTO professional quality and assumption reporting."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class QualityFinding:
    item: str
    severity: str
    message: str
    action: str


def _as_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def score_boq_quality(boq_df: pd.DataFrame, meta: dict | None = None) -> dict[str, Any]:
    """Return quality score, confidence and review findings for a BOQ."""
    meta = meta or {}
    findings: list[QualityFinding] = []

    if boq_df is None or boq_df.empty:
        return {
            "score": 0,
            "confidence": "none",
            "findings": [
                QualityFinding("BOQ", "critical", "No BOQ data was generated.", "Re-run extraction and calculation.")
            ],
        }

    data_rows = boq_df
    if "_is_header" in boq_df.columns:
        data_rows = boq_df[boq_df["_is_header"] == False]

    zero_rows = []
    for row in data_rows.to_dict("records"):
        qty = _as_float(row.get("Quantity"))
        desc = row.get("Description (English)") or row.get("البيان") or "Item"
        if qty <= 0:
            zero_rows.append(desc)

    if zero_rows:
        findings.append(
            QualityFinding(
                "Zero quantities",
                "warning",
                f"{len(zero_rows)} BOQ items have zero quantity.",
                "Review whether these items are genuinely not applicable or missing from drawings.",
            )
        )

    for item in meta.get("needs_input", []) or []:
        findings.append(
            QualityFinding(
                item,
                "critical",
                "Required drawing/input data is missing.",
                "Ask the QS user to manually enter or approve this value before tender use.",
            )
        )

    for item in meta.get("estimates", []) or []:
        findings.append(
            QualityFinding(
                item,
                "review",
                "Quantity uses an assumed or estimated value.",
                "Show the assumption in the export and require QS approval.",
            )
        )

    total = max(len(data_rows), 1)
    zero_penalty = min(len(zero_rows) / total * 30, 30)
    critical_penalty = 20 * len([f for f in findings if f.severity == "critical"])
    review_penalty = 5 * len([f for f in findings if f.severity == "review"])
    warning_penalty = 5 * len([f for f in findings if f.severity == "warning"])
    score = max(0, round(100 - zero_penalty - critical_penalty - review_penalty - warning_penalty))

    if score >= 90:
        confidence = "high"
    elif score >= 75:
        confidence = "medium"
    elif score >= 50:
        confidence = "low"
    else:
        confidence = "blocked"

    return {"score": score, "confidence": confidence, "findings": findings}


def quality_report_markdown(project_name: str, boq_df: pd.DataFrame, meta: dict | None = None) -> str:
    quality = score_boq_quality(boq_df, meta)
    lines = [
        f"# QTO Quality Report - {project_name}",
        "",
        f"Quality score: {quality['score']}/100",
        f"Confidence: {quality['confidence']}",
        "",
        "## QS Approval Checklist",
        "- Drawing classification reviewed",
        "- Extracted schedules reviewed",
        "- Missing inputs completed",
        "- Assumptions accepted or corrected",
        "- BOQ quantities spot-checked against drawings",
        "- Final tender values approved by responsible QS/Engineer",
        "",
        "## Findings",
    ]
    findings = quality["findings"]
    if not findings:
        lines.append("- No blocking findings detected by automated checks.")
    else:
        for f in findings:
            lines.append(f"- [{f.severity.upper()}] {f.item}: {f.message} Action: {f.action}")
    lines.extend(
        [
            "",
            "## Engineering Disclaimer",
            "This automated QTO report is an assistance tool. Final responsibility for tender, contract, or procurement use remains with the qualified QS/Engineer.",
        ]
    )
    return "\n".join(lines)
