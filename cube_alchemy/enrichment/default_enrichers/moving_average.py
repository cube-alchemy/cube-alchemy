from __future__ import annotations

from typing import Any, List, Optional
import pandas as pd

from ..abc import Enricher


class MovingAverageEnricher(Enricher):
    """Compute a moving average and append as a new column.

    Params:
      on: str (required) column to smooth
      window: int (default 3)
      by: List[str] optional grouping keys
      new_column: Optional[str] name for result (default: f"{on}_ma_{window}")
      min_periods: Optional[int]
      center: bool (default False)
      sort_by: Optional[List[str]] ordering columns before rolling
    """

    def enrich(self, df: pd.DataFrame, **p: Any) -> pd.DataFrame:
        on: Optional[str] = p.get('on')
        if not on:
            raise ValueError("moving_average: 'on' parameter is required")
        window: int = int(p.get('window', 3))
        by: List[str] = p.get('by') or []
        new_col: str = p.get('new_column') or f"{on}_ma_{window}"
        min_periods: Optional[int] = p.get('min_periods', None)
        center: bool = bool(p.get('center', False))
        sort_by: List[str] = p.get('sort_by') or []

        out = df.copy()
        if sort_by:
            out = out.sort_values(sort_by)

        if by:
            out[new_col] = (
                out.groupby(by, dropna=False)[on]
                   .transform(lambda s: s.rolling(window=window, min_periods=min_periods, center=center).mean())
            )
        else:
            out[new_col] = out[on].rolling(window=window, min_periods=min_periods, center=center).mean()
        return out
