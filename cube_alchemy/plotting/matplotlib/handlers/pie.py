import pandas as pd
from typing import List, Optional


def render_pie(ax, df: pd.DataFrame, dimensions: List[str], metrics: List[str], color_by: Optional[str] = None, orientation: Optional[str] = None, stacked: bool = False) -> None:
    labels = df[dimensions].astype(str).agg(' | '.join, axis=1) if dimensions else df.index.astype(str)
    if len(metrics) >= 1 and metrics[0] in df.columns:
        ax.pie(df[metrics[0]], labels=labels, autopct='%1.1f%%')
    else:
        ax.text(0.5, 0.5, 'Pie requires one metric', ha='center')
