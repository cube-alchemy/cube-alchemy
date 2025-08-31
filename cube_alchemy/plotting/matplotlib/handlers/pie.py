import pandas as pd
from typing import List, Optional


def render_pie(ax, df: pd.DataFrame, dims: List[str], mets: List[str], color_by: Optional[str] = None, orientation: Optional[str] = None, stacked: bool = False) -> None:
    labels = df[dims].astype(str).agg(' | '.join, axis=1) if dims else df.index.astype(str)
    if len(mets) >= 1 and mets[0] in df.columns:
        ax.pie(df[mets[0]], labels=labels, autopct='%1.1f%%')
    else:
        ax.text(0.5, 0.5, 'Pie requires one metric', ha='center')
