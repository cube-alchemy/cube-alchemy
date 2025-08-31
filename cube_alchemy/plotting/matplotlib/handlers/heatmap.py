import pandas as pd
from typing import List, Optional


def render_heatmap(ax, df: pd.DataFrame, dims: List[str], mets: List[str], color_by: Optional[str] = None, orientation: Optional[str] = None, stacked: bool = False) -> None:
    if len(dims) >= 2 and len(mets) >= 1 and dims[0] in df.columns and dims[1] in df.columns and mets[0] in df.columns:
        pivot_df = df.pivot_table(index=dims[0], columns=dims[1], values=mets[0], aggfunc='first').fillna(0)
        im = ax.imshow(pivot_df)
        ax.set_xticks(range(len(pivot_df.columns)))
        ax.set_yticks(range(len(pivot_df.index)))
        ax.set_xticklabels(pivot_df.columns, rotation=45, ha='right')
        ax.set_yticklabels(pivot_df.index)
        import matplotlib.pyplot as plt
        plt.colorbar(im, ax=ax)
    else:
        ax.text(0.5, 0.5, 'Heatmap requires two dimensions and one metric', ha='center')
