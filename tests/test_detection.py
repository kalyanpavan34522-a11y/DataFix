"""
Pytest unit tests for DataFix Detection Module.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
try:
    import pandas as pd
except (ImportError, Exception):
    import utils.tabular as pd
from modules.detection import DataQualityDetector


@pytest.fixture
def dirty_dataframe():
    """Create a sample DataFrame with known quality issues."""
    data = {
        "id": ["EMP-01", "EMP-02", "EMP-03", "EMP-01", "EMP-04"],
        "name": ["Alice Smith", "  Bob Jones  ", "Charlie Brown", "Alice Smith", "David Miller"],
        "email": ["alice@gmail.com", "bob@gmial.com", "invalid-email", "alice@gmail.com", "david@company.com"],
        "phone": ["(555) 123-4567", "555-987-6543", "phone123", "(555) 123-4567", "5550001122"],
        "hire_date": ["2023-01-15", "03/14/2022", "15-Jan-2021", "2023-01-15", "2022/11/05"],
        "department": ["Engineering", "engineering", "ENGINEERING", "Engineering", "HR"],
        "salary": [100000, -5000, 120000, 100000, 9999999],
        "notes": ["Good", None, "N/A", "Good", "Excellent"]
    }
    return pd.DataFrame(data)


def test_detector_finds_issues(dirty_dataframe):
    detector = DataQualityDetector(dirty_dataframe)
    issues = detector.run_all_checks()
    assert len(issues) > 0, "Detector should find multiple issues in dirty dataset."


def test_missing_values_detected(dirty_dataframe):
    detector = DataQualityDetector(dirty_dataframe)
    issues = detector.run_all_checks()
    missing_issues = [i for i in issues if i["issue_type"] == "Missing Value"]
    assert len(missing_issues) > 0, "Should detect missing or placeholder values in 'notes'."


def test_duplicate_records_detected(dirty_dataframe):
    detector = DataQualityDetector(dirty_dataframe)
    issues = detector.run_all_checks()
    dup_issues = [i for i in issues if i["issue_type"] == "Duplicate Record"]
    assert len(dup_issues) > 0, "Should detect exact duplicate row for Alice Smith."


def test_duplicate_ids_detected(dirty_dataframe):
    detector = DataQualityDetector(dirty_dataframe)
    issues = detector.run_all_checks()
    dup_id_issues = [i for i in issues if i["issue_type"] == "Duplicate Identifier"]
    assert len(dup_id_issues) > 0, "Should detect key collision for EMP-01."


def test_duplicate_ids_with_missing_values_on_100_rows():
    ids = [None] + [f"EMP-{i:03d}" for i in range(1, 99)] + ["EMP-001"]
    df = pd.DataFrame({"employee_id": ids})

    detector = DataQualityDetector(df)
    issues = detector.run_all_checks()
    duplicate_issue = next(i for i in issues if i["issue_type"] == "Duplicate Identifier")

    assert len(df) == 100
    assert duplicate_issue["affected_rows"] == [1, 99]


def test_email_formats_detected(dirty_dataframe):
    detector = DataQualityDetector(dirty_dataframe)
    issues = detector.run_all_checks()
    email_issues = [i for i in issues if i["issue_type"] == "Invalid Email Format"]
    assert len(email_issues) > 0, "Should detect malformed and typo emails (bob@gmial.com, invalid-email)."


def test_date_formats_detected(dirty_dataframe):
    detector = DataQualityDetector(dirty_dataframe)
    issues = detector.run_all_checks()
    date_issues = [i for i in issues if i["issue_type"] == "Invalid Date Format"]
    assert len(date_issues) > 0, "Should detect mixed date formatting."


def test_whitespace_detected(dirty_dataframe):
    detector = DataQualityDetector(dirty_dataframe)
    issues = detector.run_all_checks()
    ws_issues = [i for i in issues if i["issue_type"] == "Extra Whitespace"]
    assert len(ws_issues) > 0, "Should detect extra spaces around Bob Jones."


def test_outliers_detected(dirty_dataframe):
    detector = DataQualityDetector(dirty_dataframe)
    issues = detector.run_all_checks()
    outlier_issues = [i for i in issues if i["issue_type"] == "Numerical Outlier"]
    assert len(outlier_issues) > 0, "Should detect negative salary (-5000) and extreme salary (9999999)."
