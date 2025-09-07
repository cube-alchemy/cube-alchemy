from __future__ import annotations

from typing import Any
import pandas as pd

from ..abc import Enricher


class BasketAnalysisEnricher(Enricher):
    """Stub Market Basket analysis enricher (associations).

    Planned params:
      transaction_id: str (required)
      item_id: str (required)
      min_support: float (default 0.01)
      min_confidence: float (default 0.2)
      top_n: int | None
    """

    def enrich(self, df: pd.DataFrame, **p: Any) -> pd.DataFrame:  # pragma: no cover - stub
        raise NotImplementedError("BasketAnalysisEnricher is not implemented yet.")
