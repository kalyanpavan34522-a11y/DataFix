"""DataFix - Safe Data Repair Engine.

Creates explainable repair proposals, applies approved changes to a working copy,
and supports undo/restore while retaining stable source-row references.
"""

from __future__ import annotations

import copy
import datetime as dt
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

from utils.data_helpers import clean_whitespace, COMMON_DATE_FORMATS


PLACEHOLDER_NULLS = {
    "", "nan", "null", "none", "n/a", "na", "nil", "?", "-", "--",
    "undefined", "missing", "unknown", "blank", "#n/a", "-999", "99999",
}

EMAIL_TYPOS = {
    "gmial.com": "gmail.com",
    "gmai.com": "gmail.com",
    "gamil.com": "gmail.com",
    "yaho.com": "yahoo.com",
    "yahooo.com": "yahoo.com",
    "hotmial.com": "hotmail.com",
    "outlok.com": "outlook.com",
}

CATEGORY_SYNONYMS = {
    "eng.": "Engineering",
    "engineering": "Engineering",
    "eng": "Engineering",
    "human resources": "Human Resources",
    "hr": "Human Resources",
    "ny": "New York",
    "new york": "New York",
    "la": "Los Angeles",
    "los angeles": "Los Angeles",
    "sf": "San Francisco",
    "san francisco": "San Francisco",
    "mktg": "Marketing",
    "marketing": "Marketing",
}


class DataRepairEngine:
    """Build and apply safe repair proposals without modifying the uploaded data."""

    def __init__(
        self,
        df: pd.DataFrame,
        issues: Optional[List[Dict[str, Any]]] = None,
        diagnoses: Optional[List[Dict[str, Any]]] = None,
    ):
        if not isinstance(df, pd.DataFrame):
            raise TypeError("DataRepairEngine expects a pandas DataFrame.")

        # All proposal row references use stable zero-based source-row positions.
        self._original_df = df.copy(deep=True).reset_index(drop=True)
        self._working_df = self._original_df.copy(deep=True)
        self.issues = issues or []
        self.diagnoses = diagnoses or []
        self._repair_history: List[Dict[str, Any]] = []
        self.proposals = self._generate_proposals()

    @staticmethod
    def _is_missing(value: Any) -> bool:
        try:
            if pd.isna(value):
                return True
        except (TypeError, ValueError):
            pass
        return str(value).strip().lower() in PLACEHOLDER_NULLS

    @staticmethod
    def _column_name(col: Any) -> str:
        return str(col).lower()

    def get_auto_repairs(self) -> List[Dict[str, Any]]:
        return [
            p for p in self.proposals
            if p["repair_type"] == "auto" and p["status"] == "pending"
        ]

    def get_manual_repairs(self) -> List[Dict[str, Any]]:
        return [
            p for p in self.proposals
            if p["repair_type"] == "manual" and p["status"] == "pending"
        ]

    def get_all_proposals(self) -> List[Dict[str, Any]]:
        return self.proposals

    def apply_repairs(
        self,
        repair_ids: List[str],
        approved_repair_ids: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Apply pending proposals. Manual proposals require explicit approval.

        Existing callers can continue using apply_repairs(ids) for automatic
        repairs. For a manual proposal, pass its ID in approved_repair_ids or
        call apply_manual_repair(repair_id) from the approval button handler.
        """
        requested: Set[str] = set(repair_ids or [])
        approved: Set[str] = set(approved_repair_ids or [])

        for proposal in self.proposals:
            repair_id = proposal["repair_id"]
            if repair_id not in requested or proposal["status"] != "pending":
                continue
            if proposal["repair_type"] == "manual" and repair_id not in approved:
                continue

            before = self._working_df.copy(deep=True)
            self._working_df, details = self._execute_proposal(
                self._working_df, proposal
            )

            # Do not mark proposals as applied when they made no changes.
            if not details["changed_cells"] and not details["dropped_rows"]:
                continue

            proposal["status"] = "applied"
            self._repair_history.append({
                "repair_id": repair_id,
                "timestamp": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "proposal": copy.deepcopy(proposal),
                "changed_cells": details["changed_cells"],
                "dropped_rows": details["dropped_rows"],
                # The snapshot is retained for transparent auditing/debugging.
                "rows_before": int(len(before)),
                "rows_after": int(len(self._working_df)),
            })

        return self._working_df

    def apply_manual_repair(self, repair_id: str) -> pd.DataFrame:
        """Approve and apply one manual proposal (use from an explicit UI action)."""
        return self.apply_repairs(
            [repair_id], approved_repair_ids=[repair_id]
        )

    def _execute_proposal(
        self, frame: pd.DataFrame, proposal: Dict[str, Any]
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        result = frame.copy(deep=True)
        changed_cells: List[Dict[str, Any]] = []
        dropped_rows: List[Dict[str, Any]] = []

        if proposal["repair_method"] == "drop_duplicate_row":
            valid_rows = [
                idx for idx in proposal.get("affected_rows", [])
                if idx in result.index
            ]
            for idx in valid_rows:
                dropped_rows.append({
                    "row_index": idx,
                    "original_row": result.loc[idx].to_dict(),
                })
            if valid_rows:
                # Keep original row labels stable. Do not reset the index here.
                result = result.drop(index=valid_rows)
        else:
            col = proposal.get("column")
            if col in result.columns:
                for row_idx, new_value in proposal.get("proposed_values", {}).items():
                    if row_idx not in result.index:
                        continue
                    old_value = result.at[row_idx, col]
                    if self._values_equal(old_value, new_value):
                        continue
                    changed_cells.append({
                        "row_index": row_idx,
                        "column": col,
                        "original_value": old_value,
                        "new_value": new_value,
                    })
                    result.at[row_idx, col] = new_value

        return result, {
            "changed_cells": changed_cells,
            "dropped_rows": dropped_rows,
        }

    @staticmethod
    def _values_equal(left: Any, right: Any) -> bool:
        try:
            left_missing = bool(pd.isna(left))
        except (TypeError, ValueError):
            left_missing = False
        try:
            right_missing = bool(pd.isna(right))
        except (TypeError, ValueError):
            right_missing = False
        if left_missing and right_missing:
            return True
        try:
            return bool(left == right)
        except (TypeError, ValueError):
            return False

    def undo_repair(self, repair_id: str) -> pd.DataFrame:
        """Undo one repair and replay later repairs so unrelated changes remain."""
        if not any(entry["repair_id"] == repair_id for entry in self._repair_history):
            return self._working_df

        self._repair_history = [
            entry for entry in self._repair_history
            if entry["repair_id"] != repair_id
        ]
        for proposal in self.proposals:
            if proposal["repair_id"] == repair_id:
                proposal["status"] = "pending"
                break

        # Rebuild from the untouched source and replay the remaining history.
        rebuilt = self._original_df.copy(deep=True)
        for entry in self._repair_history:
            rebuilt, _ = self._execute_proposal(rebuilt, entry["proposal"])
        self._working_df = rebuilt

        # Keep status flags synchronized with the surviving history.
        applied_ids = {entry["repair_id"] for entry in self._repair_history}
        for proposal in self.proposals:
            if proposal["repair_id"] in applied_ids:
                proposal["status"] = "applied"
            elif proposal["repair_id"] == repair_id:
                proposal["status"] = "pending"

        return self._working_df

    def restore_original(self) -> pd.DataFrame:
        """Restore the full dataset and reset all proposal statuses."""
        self._working_df = self._original_df.copy(deep=True)
        for proposal in self.proposals:
            proposal["status"] = "pending"
        self._repair_history.clear()
        return self._working_df

    def get_working_df(self) -> pd.DataFrame:
        return self._working_df

    def get_original_df(self) -> pd.DataFrame:
        # Return a copy so external code cannot mutate the protected source copy.
        return self._original_df.copy(deep=True)

    def get_repair_history(self) -> List[Dict[str, Any]]:
        return copy.deepcopy(self._repair_history)

    def _add_proposal(
        self,
        proposals: List[Dict[str, Any]],
        *,
        repair_id: str,
        repair_type: str,
        column: Any,
        proposed_values: Dict[int, Any],
        repair_method: str,
        confidence: float,
        reason: str,
        requires_approval: bool,
    ) -> None:
        df = self._original_df
        original_values = {
            idx: df.at[idx, column] for idx in proposed_values
        }
        proposals.append({
            "repair_id": repair_id,
            "repair_type": repair_type,
            "column": column,
            "affected_rows": list(proposed_values.keys()),
            "original_values": original_values,
            "proposed_values": proposed_values,
            "repair_method": repair_method,
            "confidence": float(confidence),
            "reason": reason,
            "status": "pending",
            "requires_approval": bool(requires_approval),
        })

    def _generate_proposals(self) -> List[Dict[str, Any]]:
        proposals: List[Dict[str, Any]] = []
        df = self._original_df

        # 1. Leading/trailing and repeated whitespace: safe formatting repair.
        for col in df.columns:
            proposed: Dict[int, Any] = {}
            for idx, value in df[col].items():
                if isinstance(value, str):
                    cleaned = clean_whitespace(value)
                    if cleaned != value:
                        proposed[idx] = cleaned
            if proposed:
                self._add_proposal(
                    proposals,
                    repair_id=f"rep_ws_{col}",
                    repair_type="auto",
                    column=col,
                    proposed_values=proposed,
                    repair_method="strip_and_collapse_whitespace",
                    confidence=0.99,
                    reason=f"Remove leading/trailing and repeated whitespace in '{col}'.",
                    requires_approval=False,
                )

        # 2. Date standardization. Only auto-repair values with one unambiguous
        # interpretation; ambiguous dates are deliberately left unchanged.
        for col in df.columns:
            col_name = self._column_name(col)
            if not any(k in col_name for k in ["date", "time", "dob", "hire"]):
                continue
            proposed = {}
            for idx, value in df[col].items():
                if self._is_missing(value):
                    continue
                text = str(value).strip()
                parsed_dates = set()
                for fmt in COMMON_DATE_FORMATS:
                    try:
                        parsed_dates.add(dt.datetime.strptime(text, fmt).date())
                    except (ValueError, TypeError):
                        continue
                if len(parsed_dates) == 1:
                    iso_value = next(iter(parsed_dates)).isoformat()
                    if text != iso_value:
                        proposed[idx] = iso_value
            if proposed:
                self._add_proposal(
                    proposals,
                    repair_id=f"rep_date_{col}",
                    repair_type="auto",
                    column=col,
                    proposed_values=proposed,
                    repair_method="iso_date_standardization",
                    confidence=0.98,
                    reason=f"Standardize unambiguous dates in '{col}' to YYYY-MM-DD.",
                    requires_approval=False,
                )

        # 3. Capitalization: suggest only; title-casing can change names/acronyms.
        for col in df.columns:
            col_name = self._column_name(col)
            if not any(k in col_name for k in ["status", "gender", "department", "dept", "city", "state"]):
                continue
            proposed = {}
            for idx, value in df[col].items():
                if not isinstance(value, str) or self._is_missing(value):
                    continue
                text = value.strip()
                normalized = text.title()
                acronyms = {"hr": "HR", "it": "IT", "ny": "NY", "la": "LA", "sf": "SF", "usa": "USA", "uk": "UK", "api": "API", "sql": "SQL", "ai": "AI"}
                if text.lower() in acronyms:
                    normalized = acronyms[text.lower()]
                if text != normalized:
                    proposed[idx] = normalized
            if proposed:
                self._add_proposal(
                    proposals,
                    repair_id=f"rep_case_{col}",
                    repair_type="manual",
                    column=col,
                    proposed_values=proposed,
                    repair_method="title_case_normalization",
                    confidence=0.90,
                    reason=f"Review capitalization suggestions in '{col}' before applying.",
                    requires_approval=True,
                )

        # 4. Category synonyms are manual because abbreviations can be context-dependent.
        for col in df.columns:
            if not (pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col])):
                continue
            proposed = {}
            for idx, value in df[col].items():
                if self._is_missing(value):
                    continue
                normalized = CATEGORY_SYNONYMS.get(str(value).strip().lower())
                if normalized and str(value).strip() != normalized:
                    proposed[idx] = normalized
            if proposed:
                self._add_proposal(
                    proposals,
                    repair_id=f"rep_cat_{col}",
                    repair_type="manual",
                    column=col,
                    proposed_values=proposed,
                    repair_method="category_synonym_reconciliation",
                    confidence=0.90,
                    reason=f"Review possible abbreviations or synonyms in '{col}'.",
                    requires_approval=True,
                )

        # 5. Known email-domain typos require approval because they change contact data.
        for col in df.columns:
            col_has_email = "email" in self._column_name(col)
            if not col_has_email:
                try:
                    col_has_email = df[col].dropna().astype(str).str.contains("@", regex=False).any()
                except (AttributeError, TypeError):
                    col_has_email = False
            if not col_has_email:
                continue
            proposed = {}
            for idx, value in df[col].items():
                if self._is_missing(value):
                    continue
                text = str(value).strip()
                if "@" not in text:
                    continue
                local, domain = text.rsplit("@", 1)
                corrected_domain = EMAIL_TYPOS.get(domain.lower())
                if corrected_domain:
                    proposed[idx] = f"{local}@{corrected_domain}"
            if proposed:
                self._add_proposal(
                    proposals,
                    repair_id=f"rep_email_{col}",
                    repair_type="manual",
                    column=col,
                    proposed_values=proposed,
                    repair_method="email_domain_typo_correction",
                    confidence=0.95,
                    reason=f"Review known email-domain typo suggestions in '{col}' before changing contact details.",
                    requires_approval=True,
                )

        # 6. Phone formatting is locale-specific. Suggest digits-only formatting
        # for review, never auto-apply a country-specific presentation format.
        for col in df.columns:
            if not any(k in self._column_name(col) for k in ["phone", "mobile", "contact"]):
                continue
            proposed = {}
            for idx, value in df[col].items():
                if self._is_missing(value):
                    continue
                text = str(value).strip()
                digits = re.sub(r"\D", "", text)
                if len(digits) == 10 and not re.search(r"[A-Za-z]", text) and text != digits:
                    proposed[idx] = digits
            if proposed:
                self._add_proposal(
                    proposals,
                    repair_id=f"rep_phone_{col}",
                    repair_type="manual",
                    column=col,
                    proposed_values=proposed,
                    repair_method="phone_separator_normalization",
                    confidence=0.90,
                    reason=f"Review separator removal in '{col}'; no country-specific phone format is assumed.",
                    requires_approval=True,
                )

        # 7. Negative amounts are ambiguous (refunds/credits may be valid), so
        # absolute-value suggestions are manual only.
        for col in df.columns:
            if not any(k in self._column_name(col) for k in ["salary", "price", "amount", "cost"]):
                continue
            proposed = {}
            for idx, value in df[col].items():
                if self._is_missing(value):
                    continue
                try:
                    number = float(str(value).replace("$", "").replace(",", "").strip())
                except (ValueError, TypeError):
                    continue
                if number < 0:
                    proposed[idx] = abs(number)
            if proposed:
                self._add_proposal(
                    proposals,
                    repair_id=f"rep_neg_{col}",
                    repair_type="manual",
                    column=col,
                    proposed_values=proposed,
                    repair_method="review_negative_magnitude",
                    confidence=0.60,
                    reason=f"Negative values in '{col}' may be valid credits/refunds; verify before considering absolute values.",
                    requires_approval=True,
                )

        # 8. Missing-value imputation: review only and retain the exact original values.
        for col in df.columns:
            missing_indices = [
                idx for idx, value in df[col].items() if self._is_missing(value)
            ]
            if not missing_indices:
                continue

            valid_values = [
                value for value in df[col].tolist() if not self._is_missing(value)
            ]
            if not valid_values:
                # No evidence exists to infer a replacement.
                continue
            
            text_values = pd.Series(valid_values, dtype="object").astype(str)
            numeric_values = pd.to_numeric(
                text_values.str.replace("$", "", regex=False)
                .str.replace(",", "", regex=False),
                errors="coerce",
            )

            if numeric_values.notna().all():
                median = float(numeric_values.median())
                imputed_value: Any = int(median) if median.is_integer() else round(median, 2)
                strategy = f"Proposed median value ({imputed_value})"
                confidence = 0.80
            else:
                modes = pd.Series(valid_values, dtype="object").mode(dropna=True)
                if len(modes) != 1:
                    # No unique dominant category: avoid an arbitrary guess.
                    continue
                imputed_value = modes.iloc[0]
                strategy = f"Proposed most frequent value ({imputed_value})"
                confidence = 0.72

            proposed = {idx: imputed_value for idx in missing_indices}
            self._add_proposal(
                proposals,
                repair_id=f"rep_miss_{col}",
                repair_type="manual",
                column=col,
                proposed_values=proposed,
                repair_method="statistical_imputation",
                confidence=confidence,
                reason=f"{strategy} for {len(missing_indices)} missing cells in '{col}'. Review before applying.",
                requires_approval=True,
            )

        # 9. Normalized duplicate records: deletion always requires approval.
        seen_rows = set()
        duplicate_indices = []
        for idx, row in df.iterrows():
            normalized_row = tuple(
                "<NULL>" if self._is_missing(value) else str(value).strip().lower()
                for value in row.tolist()
            )
            if normalized_row in seen_rows:
                duplicate_indices.append(idx)
            else:
                seen_rows.add(normalized_row)

        if duplicate_indices:
            proposals.append({
                "repair_id": "rep_dup_rows",
                "repair_type": "manual",
                "column": "All Columns",
                "affected_rows": duplicate_indices,
                "original_values": {idx: f"Row {idx + 1}" for idx in duplicate_indices},
                "original_rows": {
                    idx: df.loc[idx].to_dict() for idx in duplicate_indices
                },
                "proposed_values": {idx: "DELETE_ROW" for idx in duplicate_indices},
                "repair_method": "drop_duplicate_row",
                "confidence": 0.99,
                "reason": f"Review {len(duplicate_indices)} normalized duplicate record(s) before deletion.",
                "status": "pending",
                "requires_approval": True,
            })

        return proposals