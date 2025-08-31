import pandas as pd
from typing import List, Optional


def render_scatter(ax, df: pd.DataFrame, dims: List[str], mets: List[str], color_by: Optional[str], orientation: Optional[str] = None, stacked: bool = False) -> None:
    # Prefer two metrics; else dimension+metric
    if len(mets) >= 2 and mets[0] in df.columns and mets[1] in df.columns:
        x_col, y_col = mets[0], mets[1]
    elif len(mets) >= 1 and len(dims) >= 1 and mets[0] in df.columns and dims[0] in df.columns:
        x_col, y_col = dims[0], mets[0]
    else:
        ax.text(0.5, 0.5, 'Scatter requires two numeric columns', ha='center')
        return

    if color_by and color_by in df.columns:
        for name, group in df.groupby(color_by):
            ax.scatter(group[x_col], group[y_col], label=str(name), alpha=0.7)
        ax.legend()
    else:
        ax.scatter(df[x_col], df[y_col])
