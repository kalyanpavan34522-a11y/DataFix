"""
DataFix - Quality Score Calculator
Computes 5-Pillar Data Quality Metric:
Completeness, Uniqueness, Validity, Consistency, and Accuracy (Integrity).
"""

from typing import Dict, List, Any
try:
    import pandas as pd
except (ImportError, Exception):
    import utils.tabular as pd


def calculate_quality_score(df: pd.DataFrame, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate dataset quality scores based on detected issues across 5 core dimensions.

    Weights:
        - Completeness: 25%
        - Uniqueness: 20%
        - Validity: 20%
        - Consistency: 15%
        - Accuracy: 20%

    Args:
        df: Input pandas DataFrame
        issues: List of detected issue dictionaries

    Returns:
        Dictionary with overall_score, 5 pillar scores, severity counts, and breakdown.
    """
    total_rows = max(1, len(df))
    total_cols = max(1, len(df.columns))
    total_cells = max(1, total_rows * total_cols)

    # Classify issues by type & severity
    missing_cells = 0
    duplicate_rows = 0
    duplicate_ids = 0
    invalid_format_count = 0
    inconsistency_count = 0
    outlier_count = 0
    schema_count = 0

    severity_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    issues_by_type = {}
    issues_by_column = {}

    for issue in issues:
        itype = issue.get("issue_type", "")
        sev = issue.get("severity", "Medium")
        col = issue.get("column", "Unknown")
        count = issue.get("affected_count", len(issue.get("affected_rows", [])))

        # Update severity counts
        if sev in severity_counts:
            severity_counts[sev] += count

        # By type
        issues_by_type[itype] = issues_by_type.get(itype, 0) + count

        # By column
        if col:
            issues_by_column[col] = issues_by_column.get(col, 0) + count

        # Pillar categorizations
        if itype == "Missing Value":
            missing_cells += count
        elif itype == "Duplicate Record":
            duplicate_rows += count
        elif itype == "Duplicate Identifier":
            duplicate_ids += count
        elif "Invalid" in itype or "Format" in itype:
            invalid_format_count += count
        elif "Inconsistent" in itype or "Whitespace" in itype:
            inconsistency_count += count
        elif "Outlier" in itype or "Anomaly" in itype or "Incorrect" in itype:
            outlier_count += count
        else:
            schema_count += count

    # Pillar 1: Completeness (100 - % missing cells with scaling factor)
    completeness = max(0.0, min(100.0, 100.0 - (missing_cells / total_cells) * 100.0 * 2.0))

    # Pillar 2: Uniqueness (100 - % duplicate rows & clashing IDs)
    uniqueness = max(0.0, min(100.0, 100.0 - ((duplicate_rows * 2 + duplicate_ids) / total_rows) * 100.0))

    # Pillar 3: Validity (100 - % format violations)
    validity = max(0.0, min(100.0, 100.0 - (invalid_format_count / total_cells) * 100.0 * 3.0))

    # Pillar 4: Consistency (100 - % inconsistent casing, whitespace, typos)
    consistency = max(0.0, min(100.0, 100.0 - (inconsistency_count / total_cells) * 100.0 * 2.5))

    # Pillar 5: Accuracy & Integrity (100 - % outliers and schema clashes)
    accuracy = max(0.0, min(100.0, 100.0 - ((outlier_count * 2 + schema_count) / total_cells) * 100.0 * 2.5))

    # Overall weighted score
    overall = (
        completeness * 0.25 +
        uniqueness * 0.20 +
        validity * 0.20 +
        consistency * 0.15 +
        accuracy * 0.20
    )

    return {
        "overall_score": round(overall, 1),
        "completeness": round(completeness, 1),
        "uniqueness": round(uniqueness, 1),
        "validity": round(validity, 1),
        "consistency": round(consistency, 1),
        "accuracy": round(accuracy, 1),
        "total_issues": sum(severity_counts.values()),
        "severity_distribution": severity_counts,
        "issues_by_type": issues_by_type,
        "issues_by_column": issues_by_column,
    }


def get_score_label(score: float) -> str:
    """Return quality label corresponding to score level."""
    if score >= 90:
        return "Excellent"
    elif score >= 75:
        return "Good"
    elif score >= 60:
        return "Fair"
    elif score >= 40:
        return "Poor"
    else:
        return "Critical"


def get_score_color(score: float) -> str:
    """Return hex color corresponding to score level."""
    if score >= 90:
        return "#10b981"  # Emerald green
    elif score >= 75:
        return "#0ea5e9"  # Sky blue
    elif score >= 60:
        return "#f59e0b"  # Amber
    elif score >= 40:
        return "#f97316"  # Orange
    else:
        return "#ef4444"  # Red
