from __future__ import annotations

from typing import Any
import pandas as pd

from ..abc import Enricher


class ParetoEnricher(Enricher):
    """Stub Pareto (80/20) analysis enricher.

    Planned params:
      value: str (required)
      by: list[str] | None
      new_columns: dict[str, str] mapping for cumulative share, rank, top_flag
    """

    def enrich(self, df: pd.DataFrame, **p: Any) -> pd.DataFrame:  # pragma: no cover - stub
        raise NotImplementedError("ParetoEnricher is not implemented yet.")
