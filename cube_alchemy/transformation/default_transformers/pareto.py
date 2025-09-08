from __future__ import annotations

from typing import Any
import pandas as pd

from ..abc import Transformer


class ParetoTransformer(Transformer):
    """Stub Pareto (80/20) analysis transformer.

    Planned params:
      value: str (required)
      by: list[str] | None
      new_columns: dict[str, str] mapping for cumulative share, rank, top_flag
    """

    def transform(self, df: pd.DataFrame, **p: Any) -> pd.DataFrame:  # pragma: no cover - stub
        raise NotImplementedError("ParetoTransformer is not implemented yet.")
