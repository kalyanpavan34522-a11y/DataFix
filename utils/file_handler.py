"""
DataFix - File Handler Utility
Handles reading CSV, Excel (XLSX/XLS), JSON formats, validating uploads,
and exporting cleaned datasets and logs.
"""

import io
import json
from typing import Tuple, Optional
try:
    import pandas as pd
except (ImportError, Exception):
    import utils.tabular as pd


MAX_FILE_SIZE_MB = 50
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}


def validate_file(uploaded_file) -> Tuple[bool, str]:
    """
    Validate uploaded file format and size limits.

    Args:
        uploaded_file: Streamlit UploadedFile or file-like object

    Returns:
        (is_valid, error_or_success_message)
    """
    if uploaded_file is None:
        return False, "No file provided."

    filename = getattr(uploaded_file, "name", "").lower()
    if not any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        return False, f"Unsupported file type. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}"

    file_size_bytes = getattr(uploaded_file, "size", 0)
    if file_size_bytes > MAX_FILE_SIZE_MB * 1024 * 1024:
        return False, f"File size ({file_size_bytes / (1024*1024):.1f} MB) exceeds maximum allowed {MAX_FILE_SIZE_MB} MB."

    return True, "File is valid."


def read_uploaded_file(uploaded_file) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Read uploaded file into a pandas DataFrame. Supports CSV, Excel, and JSON.

    Args:
        uploaded_file: Streamlit UploadedFile or file path/buffer

    Returns:
        (df, error_message)
    """
    is_valid, msg = validate_file(uploaded_file)
    if not is_valid:
        return None, msg

    filename = getattr(uploaded_file, "name", "").lower()

    try:
        if filename.endswith(".csv"):
            # Try utf-8-sig first to strip BOM, fallback to latin-1
            try:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding="utf-8-sig")
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding="latin-1")

        elif filename.endswith((".xlsx", ".xls")):
            import openpyxl
            uploaded_file.seek(0)
            wb = openpyxl.load_workbook(uploaded_file, data_only=True)
            ws = wb.active
            rows_iter = ws.iter_rows(values_only=True)
            header = [str(c).strip() for c in (next(rows_iter, []) or []) if c is not None]
            rows = []
            for r in rows_iter:
                if any(cell is not None for cell in r):
                    rows.append(dict(zip(header, r)))
            df = pd.DataFrame(rows, columns=header)

        elif filename.endswith(".json"):
            uploaded_file.seek(0)
            content = uploaded_file.read()
            if isinstance(content, bytes):
                content = content.decode("utf-8")
            data = json.loads(content)
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                df = pd.DataFrame([data])
            else:
                return None, "JSON root must be an array of objects or an object."

        else:
            return None, "Unrecognized file format."

        # Ensure string column names and strip whitespace
        df.columns = [str(col).strip() for col in df.columns]

        if df.empty:
            return None, "Uploaded dataset contains no records."

        return df, None

    except Exception as exc:
        return None, f"Failed to parse file: {str(exc)}"


def export_to_csv(df: pd.DataFrame) -> bytes:
    """Export DataFrame to UTF-8 encoded CSV bytes."""
    return df.to_csv(index=False, encoding="utf-8").encode("utf-8")


def export_to_excel(df) -> bytes:
    """Export DataFrame to Excel XLSX bytes."""
    output = io.BytesIO()
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "DataFix_Cleaned"
        cols = list(df.columns)
        ws.append(cols)
        if hasattr(df, "to_dict"):
            rows = df.to_dict("records")
            for r in rows:
                ws.append([r.get(c) for c in cols])
        wb.save(output)
        return output.getvalue()
    except Exception:
        # Fallback to CSV bytes if openpyxl fails
        return export_to_csv(df)


def export_to_json(data: dict) -> str:
    """Export dictionary or list data to formatted JSON string."""
    return json.dumps(data, indent=2, default=str)
