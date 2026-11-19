"""
DataFix - Audit Log Module
Maintains an immutable, auditable history of every dataset modification,
supporting before/after inspections, user actions, and export to CSV/JSON.
"""

import json
import uuid
import datetime
from typing import Dict, List, Any, Optional
try:
    import pandas as pd
except (ImportError, Exception):
    import utils.tabular as pd


class AuditLog:
    """
    Tracks and records every single change applied to a dataset.
    """

    def __init__(self):
        self.entries: List[Dict[str, Any]] = []

    def add_entry(
        self,
        action: str,
        column: str,
        row_index: int,
        original_value: Any,
        new_value: Any,
        reason: str,
        method: str,
        confidence: float,
        user_action: str = "auto",
        repair_id: Optional[str] = None
    ) -> str:
        """
        Record a modification event.

        Args:
            action: Action description (e.g., 'Trim Whitespace', 'Standardize Date')
            column: Target column name
            row_index: 0-indexed row number
            original_value: Original value before repair
            new_value: New value after repair
            reason: Diagnostic explanation of why change was made
            method: Method/rule used for the repair
            confidence: Confidence score (0.0 to 1.0)
            user_action: 'auto' | 'manual' | 'undo' | 'restore'
            repair_id: ID of the repair proposal

        Returns:
            entry_id: Unique string identifier for the log entry
        """
        entry_id = f"aud_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        entry = {
            "entry_id": entry_id,
            "timestamp": timestamp,
            "action": action,
            "column": str(column),
            "row_index": int(row_index),
            "original_value": "" if pd.isna(original_value) else str(original_value),
            "new_value": "" if pd.isna(new_value) else str(new_value),
            "reason": str(reason),
            "method": str(method),
            "confidence": round(float(confidence), 2),
            "user_action": user_action,
            "repair_id": repair_id or f"rep_{uuid.uuid4().hex[:6]}"
        }

        self.entries.append(entry)
        return entry_id

    def get_entries(self) -> List[Dict[str, Any]]:
        """Return all audit log entries, newest first."""
        return list(reversed(self.entries))

    def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Find an audit entry by ID."""
        for entry in self.entries:
            if entry.get("entry_id") == entry_id:
                return entry
        return None

    def get_entries_by_action(self, action: str) -> List[Dict[str, Any]]:
        """Filter audit entries by action type."""
        return [e for e in self.entries if e.get("action") == action]

    def to_dataframe(self) -> pd.DataFrame:
        """Convert log entries into a pandas DataFrame for UI tables or CSV export."""
        if not self.entries:
            return pd.DataFrame(columns=[
                "entry_id", "timestamp", "action", "column", "row_index",
                "original_value", "new_value", "reason", "method", "confidence", "user_action"
            ])
        return pd.DataFrame(self.entries)

    def to_json(self) -> str:
        """Export audit log as a formatted JSON string."""
        return json.dumps(self.entries, indent=2, default=str)

    def to_csv_bytes(self) -> bytes:
        """Export audit log as UTF-8 encoded CSV bytes."""
        df = self.to_dataframe()
        return df.to_csv(index=False, encoding="utf-8").encode("utf-8")

    def count(self) -> int:
        """Return total number of modifications logged."""
        return len(self.entries)

    def clear(self) -> None:
        """Clear all audit entries."""
        self.entries.clear()
