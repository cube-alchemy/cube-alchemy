from __future__ import annotations

from typing import Any
import pandas as pd

from ..abc import Transformer


class BasketAnalysisTransformer(Transformer):
    """Stub Market Basket analysis transformer (associations).

    Planned params:
      transaction_id: str (required)
      item_id: str (required)
      min_support: float (default 0.01)
      min_confidence: float (default 0.2)
      top_n: int | None
    """

    def transform(self, df: pd.DataFrame, **p: Any) -> pd.DataFrame:  # pragma: no cover - stub
        raise NotImplementedError("BasketAnalysisTransformer is not implemented yet.")
