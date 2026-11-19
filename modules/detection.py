"""
DataFix - Automated Data Quality Detection Engine
Inspects datasets to identify missing values, duplicates, format mismatches,
casing and whitespace discrepancies, categorical typos, and numerical outliers.
"""

import re
import difflib
from collections import Counter, defaultdict
from typing import List, Dict, Any, Optional
import statistics

try:
    import numpy as np
    import pandas as pd
except (ImportError, Exception):
    import utils.tabular as pd
    np = None

from utils.data_helpers import (
    clean_whitespace,
    is_valid_email,
    is_valid_phone,
    detect_column_type,
    COMMON_DATE_FORMATS
)

PLACEHOLDER_NULLS = {
    "", "nan", "null", "none", "n/a", "na", "nil", "?", "-", "--",
    "undefined", "missing", "unknown", "blank", "#n/a", "-999", "99999"
}

EMAIL_TYPO_DOMAINS = {
    "gmial.com": "gmail.com",
    "gmai.com": "gmail.com",
    "gamil.com": "gmail.com",
    "yaho.com": "yahoo.com",
    "yahooo.com": "yahoo.com",
    "hotmial.com": "hotmail.com",
    "outlok.com": "outlook.com",
}


class DataQualityDetector:
    """
    Automated Data Quality Detection Engine.
    Executes 12+ specialized inspection routines on a dataset.
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.rows_count = len(df)
        self.cols_count = len(df.columns)
        self.issues: List[Dict[str, Any]] = []

    def run_all_checks(self) -> List[Dict[str, Any]]:
        """Run all data quality checks and return list of detected issue dicts."""
        self.issues = []
        if self.df.empty:
            return self.issues

        self._check_missing_values()
        self._check_duplicate_rows()
        self._check_duplicate_identifiers()
        self._check_date_formats()
        self._check_email_formats()
        self._check_phone_formats()
        self._check_capitalization()
        self._check_whitespace()
        self._check_inconsistent_categories()
        self._check_numeric_types_and_outliers()
        self._check_schema_consistency()

        return self.issues

    def _add_issue(
        self,
        issue_type: str,
        severity: str,
        column: str,
        affected_rows: List[int],
        example_values: List[Any],
        description: str,
        detection_method: str
    ):
        """Helper to append structured issue."""
        issue_id = f"iss_{len(self.issues) + 1:03d}"
        self.issues.append({
            "issue_id": issue_id,
            "issue_type": issue_type,
            "severity": severity,
            "column": column,
            "affected_rows": sorted(list(set(affected_rows))),
            "affected_count": len(set(affected_rows)),
            "example_values": [str(v) for v in example_values[:5]],
            "description": description,
            "detection_method": detection_method
        })

    # 1. Missing Values Check
    def _check_missing_values(self):
        for col in self.df.columns:
            series = self.df[col]
            missing_row_indices = []
            example_vals = []

            for idx, val in enumerate(series):
                if pd.isna(val):
                    missing_row_indices.append(idx)
                    example_vals.append("<NULL>")
                else:
                    s_val = str(val).strip().lower()
                    if s_val in PLACEHOLDER_NULLS:
                        missing_row_indices.append(idx)
                        example_vals.append(str(val))

            if missing_row_indices:
                pct = len(missing_row_indices) / max(1, self.rows_count)
                sev = "Critical" if "id" in col.lower() or pct > 0.3 else "High" if pct > 0.1 else "Medium"
                self._add_issue(
                    issue_type="Missing Value",
                    severity=sev,
                    column=col,
                    affected_rows=missing_row_indices,
                    example_values=example_vals,
                    description=f"{len(missing_row_indices)} cells ({pct*100:.1f}%) in '{col}' are empty or contain sentinel nulls.",
                    detection_method="Sentinel string & NaN inspection"
                )

    # 2. Duplicate Rows Check
    def _check_duplicate_rows(self):
        # Convert all to stripped strings for robust duplicate detection
        normalized_df = self.df.astype(str).map(lambda x: str(x).strip().lower())
        dup_mask = normalized_df.duplicated(keep="first")
        dup_indices = normalized_df.index[dup_mask].tolist()

        if dup_indices:
            examples = [f"Row {idx+1}" for idx in dup_indices]
            self._add_issue(
                issue_type="Duplicate Record",
                severity="High",
                column="All Columns",
                affected_rows=dup_indices,
                example_values=examples,
                description=f"Found {len(dup_indices)} exact duplicate row(s) mirroring earlier records.",
                detection_method="Tuple-based complete row hash matching"
            )

    
    # 3. Duplicate Identifiers (Primary Key Collisions)
    def _check_duplicate_identifiers(self):

        id_cols = [
            c for c in self.df.columns
            if any(
                k in str(c).lower()
                for k in ["id", "code", "uuid", "key", "number"]
            )
        ]

        if not id_cols:
            if len(self.df.columns) == 0:
                return
            id_cols = [self.df.columns[0]]

        for id_col in id_cols:

            series = self.df[id_col].dropna()
            series = series.astype("string").str.strip()
            series = series[series != ""]

            counts = series.value_counts()
            duped_ids = counts[counts > 1].index.tolist()

            if not duped_ids:
                continue

            dup_rows = []

            for dup_id in duped_ids:
                matches = [
                    idx for idx, value in series.items()
                    if str(value).strip() == str(dup_id).strip()
                ]

                dup_rows.extend(matches)

            dup_rows = list(dict.fromkeys(dup_rows))

            self._add_issue(
                issue_type="Duplicate Identifier",
                severity="Critical",
                column=id_col,
                affected_rows=dup_rows,
                example_values=duped_ids,
                description=(
                    f"Primary identifier '{id_col}' has duplicate "
                    f"key occurrences across {len(dup_rows)} records."
                ),
                detection_method="Identifier uniqueness check"
            )


    # 4. Date Formats Check
    def _check_date_formats(self):
        for col in self.df.columns:
            if not any(k in col.lower() for k in ["date", "time", "dob", "hire", "created", "updated"]):
                continue

            series = self.df[col].dropna().astype(str).str.strip()
            clean_series = series[~series.str.lower().isin(PLACEHOLDER_NULLS)]
            if clean_series.empty:
                continue

            detected_formats = Counter()
            non_standard_rows = []
            examples = []

            for idx, val in clean_series.items():
                parsed = False
                matched_fmt = None
                for fmt in COMMON_DATE_FORMATS:
                    try:
                        import datetime
                        datetime.datetime.strptime(val, fmt)
                        matched_fmt = fmt
                        parsed = True
                        break
                    except ValueError:
                        continue

                if parsed:
                    detected_formats[matched_fmt] += 1
                    # ISO-8601 YYYY-MM-DD is canonical standard
                    if matched_fmt != "%Y-%m-%d":
                        non_standard_rows.append(int(idx))
                        examples.append(val)
                else:
                    non_standard_rows.append(int(idx))
                    examples.append(val)

            if len(detected_formats) > 1 or non_standard_rows:
                self._add_issue(
                    issue_type="Invalid Date Format",
                    severity="High",
                    column=col,
                    affected_rows=non_standard_rows,
                    example_values=examples,
                    description=f"Column '{col}' exhibits mixed date formats across {len(non_standard_rows)} records.",
                    detection_method="Multi-pattern datetime parser"
                )

    # 5. Email Formats Check
    def _check_email_formats(self):
        email_cols = [c for c in self.df.columns if "email" in c.lower() or "@" in "".join(self.df[c].dropna().astype(str))]
        for col in email_cols:
            series = self.df[col].dropna().astype(str).str.strip()
            clean_series = series[~series.str.lower().isin(PLACEHOLDER_NULLS)]
            invalid_rows = []
            examples = []

            for idx, val in clean_series.items():
                if not is_valid_email(val) or any(typo in val for typo in EMAIL_TYPO_DOMAINS):
                    invalid_rows.append(int(idx))
                    examples.append(val)

            if invalid_rows:
                self._add_issue(
                    issue_type="Invalid Email Format",
                    severity="High",
                    column=col,
                    affected_rows=invalid_rows,
                    example_values=examples,
                    description=f"Found {len(invalid_rows)} malformed or mistyped email address(es) in '{col}'.",
                    detection_method="RFC 5322 regex & domain typo validator"
                )

    # 6. Phone Formats Check
    def _check_phone_formats(self):
        phone_cols = [c for c in self.df.columns if any(k in c.lower() for k in ["phone", "mobile", "contact", "cell"])]
        for col in phone_cols:
            series = self.df[col].dropna().astype(str).str.strip()
            clean_series = series[~series.str.lower().isin(PLACEHOLDER_NULLS)]
            invalid_rows = []
            examples = []

            for idx, val in clean_series.items():
                digits = re.sub(r"\D", "", val)
                # Proper phone should have 10-12 digits and no letters
                if not is_valid_phone(val) or len(digits) < 10 or len(digits) > 15 or re.search(r"[a-zA-Z]", val):
                    invalid_rows.append(int(idx))
                    examples.append(val)

            if invalid_rows:
                self._add_issue(
                    issue_type="Invalid Phone Format",
                    severity="Medium",
                    column=col,
                    affected_rows=invalid_rows,
                    example_values=examples,
                    description=f"{len(invalid_rows)} phone number(s) in '{col}' fail syntax or digit count standards.",
                    detection_method="E.164 & 10-digit ITU validation"
                )

    # 7. Inconsistent Capitalization Check
    def _check_capitalization(self):
        for col in self.df.columns:
            if self.df[col].dtype != "object":
                continue
            series = self.df[col].dropna().astype(str).str.strip()
            clean_series = series[~series.str.lower().isin(PLACEHOLDER_NULLS)]
            if clean_series.empty or clean_series.nunique() > 50:
                continue

            lower_to_orig = defaultdict(set)
            for val in clean_series:
                lower_to_orig[val.lower()].add(val)

            inconsistent_keys = {k: v for k, v in lower_to_orig.items() if len(v) > 1}
            if inconsistent_keys:
                affected_rows = []
                examples = []
                for k, variants in inconsistent_keys.items():
                    rows = self.df.index[series.str.lower() == k].tolist()
                    affected_rows.extend(rows)
                    examples.extend(list(variants))

                self._add_issue(
                    issue_type="Inconsistent Capitalization",
                    severity="Medium",
                    column=col,
                    affected_rows=affected_rows,
                    example_values=examples,
                    description=f"Column '{col}' contains inconsistent casing variants (e.g. {', '.join(examples[:3])}).",
                    detection_method="Lower-case cluster analysis"
                )

    # 8. Extra Spaces & Formatting Problems
    def _check_whitespace(self):
        for col in self.df.columns:
            series = self.df[col].dropna()
            whitespace_rows = []
            examples = []

            for idx, val in series.items():
                if not isinstance(val, str):
                    continue
                if val.startswith(" ") or val.endswith(" ") or "  " in val:
                    whitespace_rows.append(int(idx))
                    examples.append(repr(val))

            if whitespace_rows:
                self._add_issue(
                    issue_type="Extra Whitespace",
                    severity="Low",
                    column=col,
                    affected_rows=whitespace_rows,
                    example_values=examples,
                    description=f"Found {len(whitespace_rows)} record(s) in '{col}' with leading, trailing, or double spaces.",
                    detection_method="String boundary and whitespace regex"
                )

    # 9. Inconsistent Category Names (Typos & Abbreviations)
    def _check_inconsistent_categories(self):
        for col in self.df.columns:
            if self.df[col].dtype != "object":
                continue
            series = self.df[col].dropna().astype(str).str.strip()
            clean_series = series[~series.str.lower().isin(PLACEHOLDER_NULLS)]
            unique_vals = clean_series.unique().tolist()

            if 2 <= len(unique_vals) <= 30:
                similar_pairs = []
                affected_rows = []
                for i, v1 in enumerate(unique_vals):
                    for v2 in unique_vals[i+1:]:
                        if v1.lower() == v2.lower():
                            continue
                        # Levenshtein ratio
                        ratio = difflib.SequenceMatcher(None, v1.lower(), v2.lower()).ratio()
                        if ratio >= 0.78 or (len(v1) <= 4 and v1.lower() in v2.lower()):
                            similar_pairs.append(f"'{v1}' vs '{v2}'")
                            affected_rows.extend(self.df.index[series.isin([v1, v2])].tolist())

                if similar_pairs:
                    self._add_issue(
                        issue_type="Inconsistent Category",
                        severity="Medium",
                        column=col,
                        affected_rows=affected_rows,
                        example_values=similar_pairs,
                        description=f"Column '{col}' contains near-duplicate or abbreviated categories: {', '.join(similar_pairs[:2])}.",
                        detection_method="Fuzzy string matching & Levenshtein distance"
                    )

    # 10. Numeric Types & Outliers Check
    def _check_numeric_types_and_outliers(self):
        for col in self.df.columns:
            series = self.df[col]
            # Try parsing numeric
            numeric_vals = []
            non_numeric_rows = []

            for idx, val in enumerate(series):
                if pd.isna(val) or str(val).strip().lower() in PLACEHOLDER_NULLS:
                    continue
                clean_str = str(val).replace("$", "").replace("€", "").replace("£", "").replace(",", "").strip()
                try:
                    num = float(clean_str)
                    numeric_vals.append((idx, num))
                except ValueError:
                    if any(k in col.lower() for k in ["salary", "price", "amount", "cost", "score", "rate", "age"]):
                        non_numeric_rows.append(idx)

            if non_numeric_rows:
                self._add_issue(
                    issue_type="Incorrect Numerical Type",
                    severity="High",
                    column=col,
                    affected_rows=non_numeric_rows,
                    example_values=[self.df.loc[i, col] for i in non_numeric_rows[:3]],
                    description=f"Column '{col}' expected numeric values but contains {len(non_numeric_rows)} non-numeric entry/entries.",
                    detection_method="Coercion failure inspection"
                )

            # Outlier detection using IQR
            if len(numeric_vals) >= 5:
                nums = [n for _, n in numeric_vals]
                sorted_nums = sorted(nums)
                n = len(sorted_nums)
                q25 = sorted_nums[int(n * 0.25)]
                q75 = sorted_nums[int(n * 0.75)]
                iqr = q75 - q25
                lower_fence = q25 - 1.5 * iqr
                upper_fence = q75 + 1.5 * iqr

                outlier_rows = []
                outlier_examples = []
                for idx, num in numeric_vals:
                    # Negative salary/price check
                    if any(k in col.lower() for k in ["salary", "price", "amount", "age", "count"]) and num < 0:
                        outlier_rows.append(idx)
                        outlier_examples.append(f"{num} (Negative)")
                    elif num < lower_fence or num > upper_fence:
                        outlier_rows.append(idx)
                        outlier_examples.append(str(num))

                if outlier_rows:
                    self._add_issue(
                        issue_type="Numerical Outlier",
                        severity="Medium",
                        column=col,
                        affected_rows=outlier_rows,
                        example_values=outlier_examples,
                        description=f"Detected {len(outlier_rows)} numerical outlier(s) in '{col}' outside expected distribution [{lower_fence:.1f}, {upper_fence:.1f}].",
                        detection_method="Tukey 1.5x IQR Fence & Non-negativity check"
                    )

    # 11. Schema Consistency Check
    def _check_schema_consistency(self):
        for col in self.df.columns:
            types = set()
            for val in self.df[col].dropna():
                types.add(type(val).__name__)
            if len(types) > 1 and "object" in types:
                self._add_issue(
                    issue_type="Schema Inconsistency",
                    severity="Low",
                    column=col,
                    affected_rows=[],
                    example_values=list(types),
                    description=f"Column '{col}' has mixed internal data types: {', '.join(types)}.",
                    detection_method="Python runtime type checking"
                )
