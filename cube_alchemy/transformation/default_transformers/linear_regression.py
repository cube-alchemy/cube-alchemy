from __future__ import annotations

from typing import Any
import pandas as pd

from ..abc import Transformer


class LinearRegressionTransformer(Transformer):
    """Stub Linear Regression transformer.

    Planned params:
      target: str (required)
      features: list[str] (required)
      new_column: str (default 'predicted')
      train_by: list[str] | None
      alpha: float | None
    """

    def transform(self, df: pd.DataFrame, **p: Any) -> pd.DataFrame:  # pragma: no cover - stub
        raise NotImplementedError("LinearRegressionTransformer is not implemented yet.")
