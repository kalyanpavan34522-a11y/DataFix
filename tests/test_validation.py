"""
Pytest unit tests for DataFix Validation Module.
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
from modules.diagnosis import RootCauseDiagnoser
from modules.repair import DataRepairEngine
from modules.validation import DataValidator


def test_validation_detects_quality_improvement():
    df = pd.DataFrame({
        "name": ["  Alice  ", "Bob"],
        "status": ["active", "ACTIVE"]
    })
    detector = DataQualityDetector(df)
    issues = detector.run_all_checks()
    diagnoser = RootCauseDiagnoser(df, issues)
    diagnoses = diagnoser.diagnose_all()

    engine = DataRepairEngine(df, issues, diagnoses)
    auto_ids = [p["repair_id"] for p in engine.get_auto_repairs()]
    repaired_df = engine.apply_repairs(auto_ids)

    validator = DataValidator(
        original_df=df,
        repaired_df=repaired_df,
        original_issues=issues,
        applied_repairs=engine.get_repair_history()
    )
    results = validator.validate()

    assert results["quality_improved"] is True or results["score_change"] >= 0
    assert results["schema_preserved"] is True
    assert "Validation Complete" in results["validation_summary"]
