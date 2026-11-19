"""
DataFix - Data Helper Utilities
Provides functions for column type inference, date parsing, data validation,
text normalization, numeric conversions, string similarity, and ID generation.
"""

import re
import uuid
import difflib
from typing import Any, Optional
try:
    import numpy as np
    import pandas as pd
except (ImportError, Exception):
    import utils.tabular as pd
    np = None
from dateutil import parser as dateutil_parser

# Regex patterns
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$"
)
PHONE_ALLOWED_CHARS = re.compile(r"^[\d\s\+\-\(\)\.]+$")
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_-]{2,40}$")

COMMON_DATE_FORMATS = [
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%Y/%m/%d",
    "%m-%d-%Y",
    "%d-%m-%Y",
    "%d-%b-%Y",
    "%d-%B-%Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%Y.%m.%d",
    "%d.%m.%Y",
    "%m/%d/%y",
    "%d/%m/%y",
    "%Y-%m-%d %H:%M:%S",
]


def clean_whitespace(value: Any) -> str:
    """
    Strip leading and trailing whitespace and collapse internal consecutive whitespace.

    Args:
        value: Input value or string to clean.

    Returns:
        Cleaned string with normalized whitespace, or empty string if input is None/NaN.
    """
    if value is None:
        return ""
    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return ""
    text = str(value).strip()
    return re.sub(r"\s+", " ", text)


def normalize_text(value: Any, mode: str = "title") -> str:
    """
    Normalize text casing and whitespace.

    Args:
        value: Input string or value to normalize.
        mode: Normalization mode: 'title', 'upper', 'lower', 'capitalize', or 'strip'.
              Defaults to 'title'.

    Returns:
        Normalized string with cleaned whitespace.
    """
    text = clean_whitespace(value)
    if not text:
        return ""

    mode_clean = str(mode).strip().lower()
    if mode_clean == "title":
        return text.title()
    elif mode_clean == "upper":
        return text.upper()
    elif mode_clean == "lower":
        return text.lower()
    elif mode_clean == "capitalize":
        return text.capitalize()
    elif mode_clean == "strip":
        return text
    else:
        return text


def safe_numeric_convert(value: Any) -> Optional[float]:
    """
    Safely convert a value to float, handling currency symbols, commas, and percentage signs.

    Args:
        value: Numeric, string, or mixed value to convert.

    Returns:
        Float value if convertible, otherwise None.
    """
    if value is None:
        return None
    if isinstance(value, (int, float, np.integer, np.floating)):
        if isinstance(value, (float, np.floating)) and (np.isnan(value) or np.isinf(value)):
            return None
        return float(value)

    val_str = str(value).strip()
    if not val_str or val_str.lower() in {"nan", "none", "null", "n/a", "na", ""}:
        return None

    # Handle financial negative format: (123.45) -> -123.45
    is_negative = False
    if val_str.startswith("(") and val_str.endswith(")"):
        is_negative = True
        val_str = val_str[1:-1].strip()

    # Strip currency signs, commas, percent signs, and spaces
    cleaned = re.sub(r"[$,€£¥% ]", "", val_str)
    if cleaned.startswith("-"):
        is_negative = True
        cleaned = cleaned[1:].strip()
    elif cleaned.startswith("+"):
        cleaned = cleaned[1:].strip()

    try:
        num = float(cleaned)
        return -num if is_negative else num
    except (ValueError, TypeError):
        return None


def is_valid_email(value: Any) -> bool:
    """
    Validate email address format using regular expressions.

    Args:
        value: Email address string to test.

    Returns:
        True if the email format is valid, False otherwise.
    """
    if value is None:
        return False
    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return False

    val_str = str(value).strip()
    if not val_str or len(val_str) > 254:
        return False

    # Disallow consecutive dots or invalid dot placement
    if ".." in val_str or "@." in val_str or ".@" in val_str:
        return False

    return bool(EMAIL_REGEX.match(val_str))


def is_valid_phone(value: Any) -> bool:
    """
    Validate telephone number format.

    Verifies that the string only contains standard phone formatting symbols
    (+, -, (, ), ., space) and contains between 7 and 15 digits.

    Args:
        value: Phone number to test.

    Returns:
        True if valid phone number format, False otherwise.
    """
    if value is None:
        return False
    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return False

    val_str = str(value).strip()
    if not val_str or not PHONE_ALLOWED_CHARS.match(val_str):
        return False

    digits = re.sub(r"\D", "", val_str)
    if len(digits) < 7 or len(digits) > 15:
        return False

    # Disallow dummy/all-zeros like '000-000-0000'
    if len(set(digits)) == 1 and digits[0] == "0":
        return False

    return True


def calculate_similarity(str1: Any, str2: Any) -> float:
    """
    Calculate the string similarity ratio between two strings using difflib.

    Args:
        str1: First string.
        str2: Second string.

    Returns:
        Float similarity score between 0.0 and 1.0.
    """
    if str1 is None and str2 is None:
        return 1.0
    if str1 is None or str2 is None:
        return 0.0

    s1 = clean_whitespace(str(str1)).lower()
    s2 = clean_whitespace(str(str2)).lower()

    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    return difflib.SequenceMatcher(None, s1, s2).ratio()


def generate_id() -> str:
    """
    Generate a UUID-based unique ID for audit records and entities.

    Returns:
        UUID4 string representation.
    """
    return str(uuid.uuid4())


def parse_dates_flexible(series: pd.Series) -> pd.Series:
    """
    Parse a pandas Series of dates flexibly trying multiple date formats.

    Args:
        series: pandas Series containing date strings or datetime values.

    Returns:
        pandas Series with datetime64[ns] dtype, with unparseable values converted to NaT.
    """
    if series is None or len(series) == 0:
        return pd.Series(dtype="datetime64[ns]")

    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(series, errors="coerce")

    parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    cleaned_series = series.astype(str).str.strip()
    mask_valid = (
        series.notna()
        & (cleaned_series != "")
        & (cleaned_series.str.lower() != "nan")
        & (cleaned_series.str.lower() != "nat")
        & (cleaned_series.str.lower() != "none")
    )

    # Attempt standard formats sequentially
    for fmt in COMMON_DATE_FORMATS:
        unparsed_idx = parsed[mask_valid & parsed.isna()].index
        if len(unparsed_idx) == 0:
            break
        attempt = pd.to_datetime(cleaned_series.loc[unparsed_idx], format=fmt, errors="coerce")
        success_idx = attempt[attempt.notna()].index
        if len(success_idx) > 0:
            parsed.loc[success_idx] = attempt.loc[success_idx]

    # Dateutil parser fallback for remaining unparsed values
    remaining_idx = parsed[mask_valid & parsed.isna()].index
    for idx in remaining_idx:
        val_str = cleaned_series.loc[idx]
        try:
            dt = dateutil_parser.parse(val_str)
            parsed.loc[idx] = pd.Timestamp(dt)
        except Exception:
            continue

    return parsed


def detect_column_type(series: pd.Series) -> str:
    """
    Infer the semantic type of a pandas Series.

    Types inferred:
    - 'identifier': Unique ID columns or keys (e.g. employee_id, UUID, code)
    - 'numeric': Quantitative numeric values
    - 'date': Calendar dates or timestamps
    - 'email': Email addresses
    - 'phone': Telephone numbers
    - 'categorical': Low-cardinality discrete categories
    - 'text': General free-form text

    Args:
        series: pandas Series to evaluate.

    Returns:
        String representing the detected semantic type.
    """
    if series is None or len(series) == 0:
        return "text"

    col_name = str(series.name).strip().lower() if series.name is not None else ""
    non_null = series.dropna()
    total_non_null = len(non_null)

    if total_non_null == 0:
        return "text"

    # Filter out empty strings for text analysis
    str_series = non_null.astype(str).str.strip()
    str_valid = str_series[str_series != ""]
    valid_count = len(str_valid)

    if valid_count == 0:
        return "text"

    unique_count = non_null.nunique()
    uniqueness_ratio = unique_count / total_non_null

    # 1. Check for identifier
    id_name_keywords = ("_id", "id", "uuid", "guid", "code", "key", "emp_id", "employee_id")
    has_id_name = any(
        col_name == kw or col_name.endswith(f"_{kw}") or col_name.endswith(kw)
        for kw in id_name_keywords
    )
    if has_id_name and uniqueness_ratio >= 0.8:
        return "identifier"

    if uniqueness_ratio >= 0.9 and total_non_null >= 5:
        pattern_matches = sum(bool(IDENTIFIER_PATTERN.match(val)) for val in str_valid)
        if pattern_matches / valid_count >= 0.85:
            # Avoid classifying standard text or numeric ranges as identifier unless name hints or structured
            if has_id_name or any(re.search(r"[A-Za-z]", val) and re.search(r"\d", val) for val in str_valid):
                return "identifier"

    # 2. Check for date
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"

    sample_size = min(valid_count, 50)
    sample_vals = str_valid.iloc[:sample_size]
    parsed_sample = parse_dates_flexible(sample_vals)
    date_success_ratio = parsed_sample.notna().sum() / sample_size
    if date_success_ratio >= 0.6:
        return "date"

    # 3. Check for email
    email_matches = sum(is_valid_email(val) for val in sample_vals)
    if email_matches / sample_size >= 0.5 or ("@" in col_name or "email" in col_name and email_matches > 0):
        return "email"

    # 4. Check for phone
    phone_matches = sum(is_valid_phone(val) for val in sample_vals)
    if phone_matches / sample_size >= 0.5 or ("phone" in col_name and phone_matches > 0):
        return "phone"

    # 5. Check for numeric
    if pd.api.types.is_numeric_dtype(series):
        if has_id_name and uniqueness_ratio >= 0.95:
            return "identifier"
        return "numeric"

    numeric_converts = sum(safe_numeric_convert(val) is not None for val in sample_vals)
    if numeric_converts / sample_size >= 0.75:
        if has_id_name and uniqueness_ratio >= 0.95:
            return "identifier"
        return "numeric"

    # 6. Check for categorical
    if isinstance(series.dtype, pd.CategoricalDtype) or series.dtype == bool:
        return "categorical"

    max_len = str_valid.str.len().max()
    if unique_count <= 20 and (uniqueness_ratio <= 0.35 or unique_count <= 8) and max_len <= 60:
        return "categorical"

    # 7. Fallback to general text
    return "text"
