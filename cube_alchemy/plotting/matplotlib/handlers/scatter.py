import pandas as pd
from typing import List, Optional


def render_scatter(ax, df: pd.DataFrame, dimensions: List[str], metrics: List[str], color_by: Optional[str], orientation: Optional[str] = None, stacked: bool = False) -> None:
    # Prefer two metrics; else dimension+metric
    if len(metrics) >= 2 and metrics[0] in df.columns and metrics[1] in df.columns:
        x_col, y_col = metrics[0], metrics[1]
    elif len(metrics) >= 1 and len(dimensions) >= 1 and metrics[0] in df.columns and dimensions[0] in df.columns:
        x_col, y_col = dimensions[0], metrics[0]
    else:
        ax.text(0.5, 0.5, 'Scatter requires two numeric columns', ha='center')
        return

    if color_by and color_by in df.columns:
        for name, group in df.groupby(color_by):
            ax.scatter(group[x_col], group[y_col], label=str(name), alpha=0.7)
        ax.legend()
    else:
        ax.scatter(df[x_col], df[y_col])
