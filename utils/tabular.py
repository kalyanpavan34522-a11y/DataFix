"""
DataFix - Pure Python Tabular Engine (Pandas-compatible fallback)
Provides DataFrame, Series, and Index abstractions that work seamlessly
without requiring native compiled C-extension DLLs.
"""

import io
import csv
import json
import statistics
from collections import Counter, defaultdict
from typing import Any, List, Dict, Optional, Union, Tuple


class UniqueList(list):
    def tolist(self):
        return list(self)


class Index(list):
    def __getitem__(self, idx):
        if isinstance(idx, (list, tuple, Series)):
            idx_list = list(idx)
            if idx_list and isinstance(idx_list[0], bool):
                return Index([v for v, m in zip(self, idx_list) if m])
            return Index([self[i] for i in idx_list])
        return super().__getitem__(idx)

    def tolist(self):
        return list(self)


class Series:
    def __init__(self, data: list, name: Optional[str] = None, index: Optional[list] = None):
        self._data = list(data)
        self.name = name
        self.index = Index(index) if index is not None else Index(range(len(self._data)))

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, idx):
        if isinstance(idx, int):
            return self._data[idx]
        elif isinstance(idx, (list, tuple, Series)):
            idx_list = list(idx)
            if idx_list and isinstance(idx_list[0], bool):
                filtered_vals = [d for d, m in zip(self._data, idx_list) if m]
                filtered_idx = [i for i, m in zip(self.index, idx_list) if m]
                return Series(filtered_vals, name=self.name, index=filtered_idx)
            return Series([self._data[i] for i in idx_list], name=self.name)
        raise KeyError(idx)

    def __setitem__(self, idx, val):
        if isinstance(idx, int):
            self._data[idx] = val

    @property
    def empty(self):
        return len(self._data) == 0

    @property
    def values(self):
        return list(self._data)

    @property
    def shape(self):
        return (len(self._data),)

    def to_list(self):
        return list(self._data)

    @property
    def iloc(self):
        return ILocIndexer(self)

    @property
    def values(self):
        return [[r.get(c) for c in self._cols] for r in self._rows]

    @property
    def dtype(self):
        for v in self._data:
            if v is not None and not isinstance(v, (int, float)):
                return "object"
        return "float64"

    def isna(self):
        return Series([v is None or v == "" or (isinstance(v, float) and v != v) for v in self._data])

    def dropna(self):
        clean = [(v, idx) for v, idx in zip(self._data, self.index) if v is not None and v != "" and (not isinstance(v, float) or v == v)]
        vals = [c[0] for c in clean]
        idxs = [c[1] for c in clean]
        return Series(vals, name=self.name, index=idxs)

    def astype(self, dtype):
        if dtype in (str, "str", "object"):
            return Series([str(v) if v is not None else "" for v in self._data], name=self.name, index=self.index)
        elif dtype in (float, "float64"):
            res = []
            for v in self._data:
                try:
                    res.append(float(v))
                except (ValueError, TypeError):
                    res.append(float("nan"))
            return Series(res, name=self.name, index=self.index)
        return self

    def isin(self, values):
        val_set = set(values)
        return Series([v in val_set for v in self._data], index=self.index)

    def __invert__(self):
        return Series([not bool(v) for v in self._data], index=self.index)

    def unique(self):
        seen = set()
        out = []
        for v in self._data:
            if v not in seen:
                seen.add(v)
                out.append(v)
        return UniqueList(out)

    def nunique(self):
        return len(set(self._data))

    def __gt__(self, other):
        return Series([v > other for v in self._data], index=self.index)

    def __lt__(self, other):
        return Series([v < other for v in self._data], index=self.index)

    def __ge__(self, other):
        return Series([v >= other for v in self._data], index=self.index)

    def __le__(self, other):
        return Series([v <= other for v in self._data], index=self.index)

    def __eq__(self, other):
        return Series([v == other for v in self._data], index=self.index)

    def __ne__(self, other):
        return Series([v != other for v in self._data], index=self.index)

    def value_counts(self):
        counts = Counter(self._data)
        keys = list(counts.keys())
        vals = [counts[k] for k in keys]
        return Series(vals, index=keys)

    def tolist(self):
        return list(self._data)

    def sum(self):
        return sum(1 for v in self._data if v)

    def median(self):
        nums = []
        for v in self._data:
            try:
                nums.append(float(v))
            except (ValueError, TypeError):
                pass
        return statistics.median(nums) if nums else 0.0

    def mode(self):
        counts = Counter(self._data)
        if counts:
            return [counts.most_common(1)[0][0]]
        return [None]

    @property
    def str(self):
        return StringAccessor(self)

    def items(self):
        return zip(self.index, self._data)


class StringAccessor:
    def __init__(self, series: Series):
        self._s = series

    def strip(self):
        return Series([str(v).strip() if v is not None else "" for v in self._s._data], index=self._s.index)

    def replace(self, pat, repl, regex=True):
        return Series([str(v).replace(pat, repl) if v is not None else "" for v in self._s._data], index=self._s.index)

    def lower(self):
        return Series([str(v).lower() if v is not None else "" for v in self._s._data], index=self._s.index)

    def isin(self, values):
        val_set = set(values)
        return Series([v in val_set for v in self._s._data], index=self._s.index)


class DataFrame:
    def __init__(self, data: Optional[Union[dict, list]] = None, columns: Optional[list] = None):
        if data is None:
            self._cols = list(columns) if columns else []
            self._rows = []
        elif isinstance(data, dict):
            self._cols = list(data.keys())
            num_rows = len(next(iter(data.values()))) if data else 0
            self._rows = []
            for r in range(num_rows):
                row_dict = {c: data[c][r] for c in self._cols}
                self._rows.append(row_dict)
        elif isinstance(data, list):
            if data and isinstance(data[0], dict):
                self._cols = list(columns) if columns else list(data[0].keys())
                self._rows = [dict(r) for r in data]
            else:
                self._cols = list(columns) if columns else [f"col_{i}" for i in range(len(data[0]))] if data else []
                self._rows = [{c: row[i] for i, c in enumerate(self._cols)} for row in data]
        else:
            self._cols = []
            self._rows = []

        self.index = Index(range(len(self._rows)))

    @property
    def columns(self):
        return list(self._cols)

    @columns.setter
    def columns(self, new_cols):
        mapping = dict(zip(self._cols, new_cols))
        for r in self._rows:
            for old_c, new_c in mapping.items():
                if old_c in r:
                    r[new_c] = r.pop(old_c)
        self._cols = list(new_cols)

    @property
    def shape(self):
        return (len(self._rows), len(self._cols))

    @property
    def empty(self):
        return len(self._rows) == 0

    def __len__(self):
        return len(self._rows)

    def __getitem__(self, col_name):
        if isinstance(col_name, str):
            vals = [r.get(col_name) for r in self._rows]
            return Series(vals, name=col_name, index=self.index)
        elif isinstance(col_name, list):
            return DataFrame([{c: r.get(c) for c in col_name} for r in self._rows], columns=col_name)
        elif isinstance(col_name, Series):
            filtered_rows = [r for r, m in zip(self._rows, col_name._data) if m]
            return DataFrame(filtered_rows, columns=self._cols)
        raise KeyError(col_name)

    def __setitem__(self, col_name, value):
        if col_name not in self._cols:
            self._cols.append(col_name)
        if isinstance(value, (list, tuple, Series)):
            for r_idx, val in enumerate(value):
                if r_idx < len(self._rows):
                    self._rows[r_idx][col_name] = val
        else:
            for r in self._rows:
                r[col_name] = value

    @property
    def loc(self):
        return LocIndexer(self)

    @property
    def at(self):
        return AtIndexer(self)

    @property
    def iloc(self):
        return ILocIndexer(self)

    @property
    def values(self):
        return [[r.get(c) for c in self._cols] for r in self._rows]

    def copy(self, deep: bool = True):
        import copy
        return DataFrame(copy.deepcopy(self._rows), columns=list(self._cols))

    def drop(self, index=None):
        drop_set = set(index) if index is not None else set()
        new_rows = [r for i, r in enumerate(self._rows) if i not in drop_set]
        return DataFrame(new_rows, columns=self._cols)

    def reset_index(self, drop: bool = True):
        self.index = Index(range(len(self._rows)))
        return self

    def isna(self):
        res = []
        for r in self._rows:
            row_bools = {c: (r.get(c) is None or r.get(c) == "" or (isinstance(r.get(c), float) and r.get(c) != r.get(c))) for c in self._cols}
            res.append(row_bools)
        return DataFrame(res, columns=self._cols)

    def sum(self):
        # sum of rows for boolean frame
        total = 0
        for r in self._rows:
            total += sum(1 for v in r.values() if v is True)
        return SumHelper(total)

    def duplicated(self, keep="first"):
        seen = set()
        mask = []
        for r in self._rows:
            t = tuple(str(r.get(c, "")).strip().lower() for c in self._cols)
            if t in seen:
                mask.append(True)
            else:
                seen.add(t)
                mask.append(False)
        return Series(mask, index=self.index)

    def astype(self, dtype):
        if dtype in (str, "str", "object"):
            new_rows = []
            for r in self._rows:
                new_rows.append({c: ("" if r.get(c) is None else str(r.get(c))) for c in self._cols})
            return DataFrame(new_rows, columns=self._cols)
        return self

    def map(self, func):
        new_rows = []
        for r in self._rows:
            new_rows.append({c: func(r.get(c)) for c in self._cols})
        return DataFrame(new_rows, columns=self._cols)

    def to_csv(self, path_or_buf=None, index=False, encoding="utf-8"):
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=self._cols)
        writer.writeheader()
        writer.writerows(self._rows)
        content = output.getvalue()
        if path_or_buf:
            if hasattr(path_or_buf, "write"):
                path_or_buf.write(content)
            else:
                with open(path_or_buf, "w", encoding=encoding) as f:
                    f.write(content)
            return None
        return content

    def to_dict(self, orient="records"):
        import copy
        return copy.deepcopy(self._rows)

    def head(self, n=5):
        return DataFrame(self._rows[:n], columns=self._cols)

    def tail(self, n=5):
        return DataFrame(self._rows[-n:], columns=self._cols)


class SumHelper:
    def __init__(self, val):
        self._val = val

    def sum(self):
        return self._val

    def __int__(self):
        return self._val


class LocIndexer:
    def __init__(self, df: DataFrame):
        self._df = df

    def __getitem__(self, key):
        row_idx, col_name = key
        return self._df._rows[row_idx].get(col_name)

    def __setitem__(self, key, value):
        row_idx, col_name = key
        if col_name not in self._df._cols:
            self._df._cols.append(col_name)
        self._df._rows[row_idx][col_name] = value


class AtIndexer:
    def __init__(self, df: DataFrame):
        self._df = df

    def __getitem__(self, key):
        row_idx, col_name = key
        return self._df._rows[row_idx].get(col_name)

    def __setitem__(self, key, value):
        row_idx, col_name = key
        if col_name not in self._df._cols:
            self._df._cols.append(col_name)
        self._df._rows[row_idx][col_name] = value


class ILocIndexer:
    def __init__(self, obj):
        self._obj = obj

    def __getitem__(self, idx):
        if isinstance(idx, int):
            if hasattr(self._obj, "_data"):
                return self._obj._data[idx]
            elif hasattr(self._obj, "_rows"):
                return self._obj._rows[idx]
        elif isinstance(idx, tuple) and len(idx) == 2:
            r_idx, c_idx = idx
            if hasattr(self._obj, "_rows"):
                row = self._obj._rows[r_idx]
                if isinstance(c_idx, int):
                    col = self._obj._cols[c_idx]
                    return row.get(col)
                return row.get(c_idx)
        return self._obj[idx]


def read_csv(filepath_or_buffer, encoding="utf-8-sig") -> DataFrame:
    """Read CSV into DataFrame."""
    if isinstance(filepath_or_buffer, str):
        with open(filepath_or_buffer, "r", encoding=encoding) as f:
            reader = csv.DictReader(f)
            fields = [c.strip() for c in (reader.fieldnames or [])]
            rows = [dict(r) for r in reader]
    else:
        text = filepath_or_buffer.read()
        if isinstance(text, bytes):
            text = text.decode(encoding)
        reader = csv.DictReader(io.StringIO(text))
        fields = [c.strip() for c in (reader.fieldnames or [])]
        rows = [dict(r) for r in reader]
    return DataFrame(rows, columns=fields)


def isna(val):
    if val is None or val == "":
        return True
    if isinstance(val, float) and val != val:
        return True
    return False


def to_numeric(series, errors="coerce"):
    res = []
    for v in series:
        try:
            res.append(float(v))
        except (ValueError, TypeError):
            res.append(float("nan"))
    return Series(res, name=getattr(series, "name", None))
