import pandas as pd
from typing import List, Optional


def render_heatmap(ax, df: pd.DataFrame, dimensions: List[str], metrics: List[str], color_by: Optional[str] = None, orientation: Optional[str] = None, stacked: bool = False) -> None:
    if len(dimensions) >= 2 and len(metrics) >= 1 and dimensions[0] in df.columns and dimensions[1] in df.columns and metrics[0] in df.columns:
        pivot_df = df.pivot_table(index=dimensions[0], columns=dimensions[1], values=metrics[0], aggfunc='first').fillna(0)
        im = ax.imshow(pivot_df)
        ax.set_xticks(range(len(pivot_df.columns)))
        ax.set_yticks(range(len(pivot_df.index)))
        ax.set_xticklabels(pivot_df.columns, rotation=45, ha='right')
        ax.set_yticklabels(pivot_df.index)
        import matplotlib.pyplot as plt
        plt.colorbar(im, ax=ax)
    else:
        ax.text(0.5, 0.5, 'Heatmap requires two dimensions and one metric', ha='center')
