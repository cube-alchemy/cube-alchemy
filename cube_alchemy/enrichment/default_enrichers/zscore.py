from __future__ import annotations

from typing import Any, List, Optional
import numpy as np
import pandas as pd

from ..abc import Enricher


class ZScoreEnricher(Enricher):
    """Compute z-score for a column, optionally by groups, as a new column.

    Params:
      on: str (required) column to standardize
      by: List[str] optional grouping keys
      new_column: Optional[str] name for result (default: f"{on}_z")
      ddof: int degrees of freedom for std (default pandas std ddof)
    """

    def enrich(self, df: pd.DataFrame, **p: Any) -> pd.DataFrame:
        on: Optional[str] = p.get('on')
        if not on:
            raise ValueError("zscore: 'on' parameter is required")
        by: List[str] = p.get('by') or []
        new_col: str = p.get('new_column') or f"{on}_z"
        ddof: Optional[int] = p.get('ddof', None)

        out = df.copy()

        if by:
            grp = out.groupby(by, dropna=False)[on]
            mean = grp.transform('mean')
            std = grp.transform(lambda s: s.std(ddof=ddof) if ddof is not None else s.std())
            z = (out[on] - mean) / std
        else:
            mean = out[on].mean()
            std = out[on].std(ddof=ddof) if ddof is not None else out[on].std()
            z = (out[on] - mean) / std

        # Replace inf where std == 0
        z = z.replace([np.inf, -np.inf], np.nan)
        out[new_col] = z
        return out
