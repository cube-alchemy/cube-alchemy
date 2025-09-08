from __future__ import annotations

from typing import Any
import pandas as pd

from ..abc import Transformer


class KMeansTransformer(Transformer):
    """Stub KMeans transformer.

    Planned params:
      features: list[str] (required)
      n_clusters: int (default 8)
      new_column: str (default 'cluster')
      random_state: int | None
      scale: bool (default True)
    """

    def transform(self, df: pd.DataFrame, **p: Any) -> pd.DataFrame:  # pragma: no cover - stub
        raise NotImplementedError("KMeansTransformer is not implemented yet. Consider installing scikit-learn and implementing.")
