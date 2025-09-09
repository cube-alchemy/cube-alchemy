from __future__ import annotations

from typing import Iterable, Optional

import pandas as pd
from pandas.testing import assert_frame_equal


def normalize_df(
    df: pd.DataFrame,
    index_cols: Optional[Iterable[str]] = None,
    sort_by: Optional[Iterable[str]] = None,
    float_cols: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    out = df.copy()
    if index_cols:
        out = out.set_index(list(index_cols))
    # Ensure comparable column order and sorting
    if sort_by:
        out = out.sort_values(list(sort_by))
    else:
        try:
            out = out.sort_index()
        except Exception:
            pass
    if float_cols:
        for c in float_cols:
            if c in out.columns:
                out[c] = out[c].astype(float)
            elif c in getattr(out, "index", []):
                # leave index as-is if float index
                pass
    return out


def assert_df_equal_loose(
    expected: pd.DataFrame,
    actual: pd.DataFrame,
    *,
    index_cols: Optional[Iterable[str]] = None,
    sort_by: Optional[Iterable[str]] = None,
    float_cols: Optional[Iterable[str]] = None,
    rtol: float = 1e-6,
    atol: float = 1e-12,
    check_dtype: bool = False,
) -> None:
    """Compare two DataFrames for test assertions in a robust, order-insensitive way.

    - Optionally set a stable index (index_cols)
    - Sort rows deterministically (sort_by or index)
    - Coerce selected float columns
    - Use tolerances for numeric comparisons
    """
    exp = normalize_df(expected, index_cols=index_cols, sort_by=sort_by, float_cols=float_cols)
    act = normalize_df(actual, index_cols=index_cols, sort_by=sort_by, float_cols=float_cols)

    # Align columns if actual has extras; compare on expected columns only by default
    common_cols = [c for c in exp.columns if c in act.columns]
    exp = exp[common_cols]
    act = act[common_cols]

    assert_frame_equal(exp, act, check_dtype=check_dtype, rtol=rtol, atol=atol)
