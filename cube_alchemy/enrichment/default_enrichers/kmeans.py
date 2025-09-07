from __future__ import annotations

from typing import Any
import pandas as pd

from ..abc import Enricher


class KMeansEnricher(Enricher):
    """Stub KMeans enricher.

    Planned params:
      features: list[str] (required)
      n_clusters: int (default 8)
      new_column: str (default 'cluster')
      random_state: int | None
      scale: bool (default True)
    """

    def enrich(self, df: pd.DataFrame, **p: Any) -> pd.DataFrame:  # pragma: no cover - stub
        raise NotImplementedError("KMeansEnricher is not implemented yet. Consider installing scikit-learn and implementing.")
