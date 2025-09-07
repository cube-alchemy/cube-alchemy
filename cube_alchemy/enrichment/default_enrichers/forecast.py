from __future__ import annotations

from typing import Any
import pandas as pd

from ..abc import Enricher


class ForecastEnricher(Enricher):
    """Stub Forecast enricher.

    Planned params:
      on: str (required) series to forecast
      horizon: int (default 12)
      by: list[str] | None
      model: str (e.g., 'naive', 'holtwinters', 'prophet')
      new_column: str (default f"{on}_forecast")
    """

    def enrich(self, df: pd.DataFrame, **p: Any) -> pd.DataFrame:  # pragma: no cover - stub
        raise NotImplementedError("ForecastEnricher is not implemented yet.")
