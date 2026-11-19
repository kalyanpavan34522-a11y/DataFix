"""
Pytest unit tests for DataFix Repair Module.
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


@pytest.fixture
def repair_setup():
    df = pd.DataFrame({
        "name": ["  Alice  ", "Bob"],
        "department": ["engineering", "ENGINEERING"],
        "salary": [-5000.0, 100000.0],
        "notes": [None, "Valid"]
    })
    detector = DataQualityDetector(df)
    issues = detector.run_all_checks()
    diagnoser = RootCauseDiagnoser(df, issues)
    diagnoses = diagnoser.diagnose_all()
    engine = DataRepairEngine(df, issues, diagnoses)
    return engine, df


def test_auto_repairs_generated(repair_setup):
    engine, _ = repair_setup
    auto = engine.get_auto_repairs()
    assert len(auto) > 0, "Engine should propose automated safe repairs for whitespace and casing."


def test_apply_repair_updates_working_df(repair_setup):
    engine, orig = repair_setup
    auto = engine.get_auto_repairs()
    ws_repair = next((r for r in auto if "ws" in r["repair_id"]), None)
    assert ws_repair is not None, "Whitespace repair should exist."

    updated_df = engine.apply_repairs([ws_repair["repair_id"]])
    assert updated_df.loc[0, "name"] == "Alice", "Leading/trailing whitespace should be stripped."
    assert orig.loc[0, "name"] == "  Alice  ", "Original DataFrame must remain immutable."


def test_undo_repair(repair_setup):
    engine, _ = repair_setup
    auto = engine.get_auto_repairs()
    rep = auto[0]
    rep_id = rep["repair_id"]

    engine.apply_repairs([rep_id])
    assert len(engine.get_repair_history()) == 1

    restored_df = engine.undo_repair(rep_id)
    assert len(engine.get_repair_history()) == 0


def test_restore_original(repair_setup):
    engine, orig = repair_setup
    auto = engine.get_auto_repairs()
    rep_ids = [r["repair_id"] for r in auto]
    engine.apply_repairs(rep_ids)

    fresh_df = engine.restore_original()
    assert fresh_df.loc[0, "name"] == orig.loc[0, "name"], "Restoring must reset all values back to original."


def test_manual_repairs_require_approval(repair_setup):
    engine, _ = repair_setup
    manual = engine.get_manual_repairs()
    for m in manual:
        assert m["requires_approval"] is True, "All manual repairs must enforce explicit approval."
