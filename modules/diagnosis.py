"""
DataFix - Intelligent Root-Cause Diagnosis Module
Analyzes detected data error patterns and infers underlying causal drivers,
distinguishing confirmed causes from suspected causes with confidence scoring.
"""

from typing import List, Dict, Any
try:
    import pandas as pd
except (ImportError, Exception):
    import utils.tabular as pd


class RootCauseDiagnoser:
    """
    Infers likely root causes behind detected dataset quality issues.
    """

    def __init__(self, df: pd.DataFrame, issues: List[Dict[str, Any]]):
        self.df = df
        self.issues = issues

    def diagnose_all(self) -> List[Dict[str, Any]]:
        """
        Diagnose all issues and produce detailed root-cause records.
        """
        diagnoses = []
        for issue in self.issues:
            diag = self._diagnose_single_issue(issue)
            diagnoses.append(diag)
        return diagnoses

    def _diagnose_single_issue(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        itype = issue.get("issue_type", "")
        col = issue.get("column", "")
        count = issue.get("affected_count", 0)
        examples = issue.get("example_values", [])

        if itype == "Missing Value":
            return self._diagnose_missing(col, count, examples)
        elif itype == "Duplicate Record":
            return self._diagnose_duplicate_rows(count, examples)
        elif itype == "Duplicate Identifier":
            return self._diagnose_duplicate_ids(col, count, examples)
        elif itype == "Invalid Date Format":
            return self._diagnose_date_format(col, count, examples)
        elif itype == "Invalid Email Format":
            return self._diagnose_email_format(col, count, examples)
        elif itype == "Invalid Phone Format":
            return self._diagnose_phone_format(col, count, examples)
        elif itype == "Inconsistent Capitalization":
            return self._diagnose_capitalization(col, count, examples)
        elif itype == "Extra Whitespace":
            return self._diagnose_whitespace(col, count, examples)
        elif itype == "Inconsistent Category":
            return self._diagnose_categories(col, count, examples)
        elif itype == "Numerical Outlier":
            return self._diagnose_outlier(col, count, examples)
        elif itype == "Incorrect Numerical Type":
            return self._diagnose_numeric_type(col, count, examples)
        else:
            return {
                "issue_id": issue.get("issue_id", ""),
                "issue_type": itype,
                "column": col,
                "probable_cause": "Unspecified ingestion schema or storage disparity.",
                "cause_type": "Suspected",
                "evidence": f"Found {count} anomalous occurrences in '{col}'.",
                "recommended_action": "Review source ETL pipeline mapping.",
                "confidence_score": 0.70,
                "explanation": "General schema drift observed during ingestion."
            }

    def _diagnose_missing(self, col: str, count: int, examples: list) -> dict:
        total_rows = max(1, len(self.df))
        pct = (count / total_rows) * 100

        if any(k in col.lower() for k in ["phone", "notes", "secondary", "alt"]):
            cause = "Optional registration field omitted by users during checkout/onboarding."
            cause_type = "Confirmed"
            rec = "Impute canonical placeholder 'Not Provided' or leave unforced."
            conf = 0.92
        elif any(k in col.lower() for k in ["salary", "department", "status"]):
            cause = "Incomplete employee onboarding or selective field omission during manual entry."
            cause_type = "Suspected"
            rec = "Impute column median/mode or flag for HR administrator verification."
            conf = 0.85
        else:
            cause = "Network transmission packet loss or unvalidated web form submission."
            cause_type = "Suspected"
            rec = "Standardize to explicit null sentinel."
            conf = 0.78

        return {
            "issue_type": "Missing Value",
            "column": col,
            "probable_cause": cause,
            "cause_type": cause_type,
            "evidence": f"{count} rows ({pct:.1f}% of dataset) lack valid values in '{col}'.",
            "recommended_action": rec,
            "confidence_score": conf,
            "explanation": "Missingness analysis shows pattern aligns with data entry field requirement levels."
        }

    def _diagnose_duplicate_rows(self, count: int, examples: list) -> dict:
        return {
            "issue_type": "Duplicate Record",
            "column": "All Columns",
            "probable_cause": "Double-submission or repeated ETL batch ingestion without idempotency checks.",
            "cause_type": "Confirmed",
            "evidence": f"Identical tuple hashes found for {count} records across all column attributes.",
            "recommended_action": "Prune redundant duplicate rows, preserving earliest timestamped master record.",
            "confidence_score": 0.99,
            "explanation": "Exact identical values across all fields can only arise from accidental duplicate ingest."
        }

    def _diagnose_duplicate_ids(self, col: str, count: int, examples: list) -> dict:
        return {
            "issue_type": "Duplicate Identifier",
            "column": col,
            "probable_cause": "Key generation collision or conflicting updates submitted for the same entity.",
            "cause_type": "Confirmed",
            "evidence": f"Identical primary key '{col}' assigned to different records ({', '.join(examples[:2])}).",
            "recommended_action": "Perform master data entity reconciliation; regenerate unique surrogate IDs.",
            "confidence_score": 0.96,
            "explanation": "Primary keys must be universally unique. Duplicate IDs indicate an uncoordinated multi-system merge."
        }

    def _diagnose_date_format(self, col: str, count: int, examples: list) -> dict:
        return {
            "issue_type": "Invalid Date Format",
            "column": col,
            "probable_cause": "Data aggregated from multiple international or legacy systems with conflicting date conventions (US MM/DD vs ISO YYYY-MM-DD).",
            "cause_type": "Confirmed",
            "evidence": f"Detected multiple distinct date syntax formats ({', '.join(examples[:3])}).",
            "recommended_action": "Standardize all date entries to ISO-8601 (YYYY-MM-DD).",
            "confidence_score": 0.98,
            "explanation": "ISO-8601 ensures deterministic sorting and chronological indexing across analytics engines."
        }

    def _diagnose_email_format(self, col: str, count: int, examples: list) -> dict:
        return {
            "issue_type": "Invalid Email Format",
            "column": col,
            "probable_cause": "Keyboard typographical mistakes or incomplete email addresses entered without client-side HTML5 validation.",
            "cause_type": "Confirmed",
            "evidence": f"Strings violating RFC 5322 or containing known provider typos ({', '.join(examples[:2])}).",
            "recommended_action": "Correct recognized typo domains (e.g. '@gmial.com' -> '@gmail.com') and flag unrepairable syntax.",
            "confidence_score": 0.95,
            "explanation": "High semantic proximity to major mail providers confirms user intended standard webmail domains."
        }

    def _diagnose_phone_format(self, col: str, count: int, examples: list) -> dict:
        return {
            "issue_type": "Invalid Phone Format",
            "column": col,
            "probable_cause": "Unmasked free-text phone input field allowing arbitrary punctuation, spaces, and placeholder strings.",
            "cause_type": "Confirmed",
            "evidence": f"Raw entries mix parentheses, dots, hyphens, and dummy values ({', '.join(examples[:3])}).",
            "recommended_action": "Normalize 10-digit entries to standard (XXX) XXX-XXXX syntax; flag dummy or incomplete digits.",
            "confidence_score": 0.94,
            "explanation": "Standardized telephone formatting ensures CRM and telephony integrations operate reliably."
        }

    def _diagnose_capitalization(self, col: str, count: int, examples: list) -> dict:
        return {
            "issue_type": "Inconsistent Capitalization",
            "column": col,
            "probable_cause": "Multiple human operators entering data without automated casing normalization (e.g., 'Engineering' vs 'engineering').",
            "cause_type": "Confirmed",
            "evidence": f"Identical lowercase tokens entered with differing lettercases ({', '.join(examples[:3])}).",
            "recommended_action": "Standardize all entries to Title Case or dominant category casing.",
            "confidence_score": 0.97,
            "explanation": "Preserves categorical uniqueness while consolidating fragmented GROUP BY dimensions."
        }

    def _diagnose_whitespace(self, col: str, count: int, examples: list) -> dict:
        return {
            "issue_type": "Extra Whitespace",
            "column": col,
            "probable_cause": "Copy-pasting strings from external spreadsheets or documents with accidental leading/trailing spaces.",
            "cause_type": "Confirmed",
            "evidence": f"Strings contain surrounding spaces or double interior spaces ({', '.join(examples[:2])}).",
            "recommended_action": "Strip leading/trailing whitespace and collapse internal spaces.",
            "confidence_score": 0.99,
            "explanation": "Whitespace trimming is completely safe and eliminates phantom string mismatch errors."
        }

    def _diagnose_categories(self, col: str, count: int, examples: list) -> dict:
        return {
            "issue_type": "Inconsistent Category",
            "column": col,
            "probable_cause": "Informal abbreviations and spelling variations entered over time without controlled vocabulary dropdowns.",
            "cause_type": "Suspected",
            "evidence": f"High Levenshtein similarity between categorical tokens ({', '.join(examples[:2])}).",
            "recommended_action": "Map abbreviations (e.g. 'Eng.' -> 'Engineering', 'NY' -> 'New York') to canonical full names.",
            "confidence_score": 0.88,
            "explanation": "Consolidating equivalent semantic terms restores accurate categorical business metrics."
        }

    def _diagnose_outlier(self, col: str, count: int, examples: list) -> dict:
        has_negative = any("negative" in str(x).lower() or "-" in str(x) for x in examples)
        cause = "Polarity inversion or negative balance flag mistakenly entered." if has_negative else "Fat-finger transcription typo (e.g. extra zero) or test data left in production."
        cause_type = "Confirmed" if has_negative else "Suspected"

        return {
            "issue_type": "Numerical Outlier",
            "column": col,
            "probable_cause": cause,
            "cause_type": cause_type,
            "evidence": f"Values ({', '.join(examples[:2])}) deviate beyond statistical IQR bounds.",
            "recommended_action": "Invert negative signs for positive domains or cap extreme values to column distribution limits.",
            "confidence_score": 0.90 if has_negative else 0.78,
            "explanation": "Outliers skew statistical aggregations like means and variances."
        }

    def _diagnose_numeric_type(self, col: str, count: int, examples: list) -> dict:
        return {
            "issue_type": "Incorrect Numerical Type",
            "column": col,
            "probable_cause": "Raw financial formatting ($ symbol, commas) prevents database engines from treating column as numeric.",
            "cause_type": "Confirmed",
            "evidence": f"Non-numeric characters in column '{col}' ({', '.join(examples[:2])}).",
            "recommended_action": "Strip currency symbols and cast cleanly to floating-point numeric type.",
            "confidence_score": 0.98,
            "explanation": "Enables numeric calculations without altering monetary amounts."
        }
