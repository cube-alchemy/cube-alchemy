from __future__ import annotations

from typing import Any
import pandas as pd

from ..abc import Enricher


class LinearRegressionEnricher(Enricher):
    """Stub Linear Regression enricher.

    Planned params:
      target: str (required)
      features: list[str] (required)
      new_column: str (default 'predicted')
      train_by: list[str] | None
      alpha: float | None
    """

    def enrich(self, df: pd.DataFrame, **p: Any) -> pd.DataFrame:  # pragma: no cover - stub
        raise NotImplementedError("LinearRegressionEnricher is not implemented yet.")
