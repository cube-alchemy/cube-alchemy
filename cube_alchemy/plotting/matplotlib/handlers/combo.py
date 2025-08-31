import pandas as pd
from typing import List, Optional


def render_combo(ax, df: pd.DataFrame, dims: List[str], mets: List[str], color_by: Optional[str] = None, orientation: str = 'vertical', stacked: bool = False) -> None:
    """
    Combo chart: first metric as bars (primary y-axis), second metric as line (secondary y-axis).
    Requires exactly 1 dimension and at least 2 metrics present in df.
    """
    import numpy as np

    if len(dims) < 1 or len(mets) < 2:
        ax.text(0.5, 0.5, 'Combo requires 1 dimension and 2 metrics', ha='center')
        return

    dim = dims[0]
    m1, m2 = mets[0], mets[1]
    if dim not in df.columns or m1 not in df.columns or m2 not in df.columns:
        ax.text(0.5, 0.5, 'Missing required columns for combo chart', ha='center')
        return

    labels = df[dim].astype(str).values
    idx = np.arange(len(labels))

    # Bars for first metric
    if orientation == 'horizontal':
        bars = ax.barh(idx, df[m1].values, label=m1, alpha=0.8)
        ax.set_yticks(idx)
        ax.set_yticklabels(labels)
        ax.set_xlabel(m1)
        # Secondary axis for line is less common in horizontal; overlay using twinx equivalent doesn't map cleanly.
        # We'll still plot a line on a twin axis using the same ytick positions as categories.
        ax2 = ax.twiny()
        ax2.plot(df[m2].values, idx, marker='o', color='tab:red', label=m2)
        ax2.set_xlabel(m2, color='tab:red')
        ax2.tick_params(axis='x', colors='tab:red')
    else:
        bars = ax.bar(idx, df[m1].values, label=m1, alpha=0.8)
        ax.set_xticks(idx)
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.set_ylabel(m1)
        # Secondary y-axis for second metric
        ax2 = ax.twinx()
        ax2.plot(idx, df[m2].values, marker='o', color='tab:red', label=m2)
        ax2.set_ylabel(m2, color='tab:red')
        ax2.tick_params(axis='y', colors='tab:red')

    # Legends: combine from both axes
    lines_labels = []
    for a in [ax, ax2]:
        handles, labels = a.get_legend_handles_labels()
        if handles:
            lines_labels.append((handles, labels))
    if lines_labels:
        handles = sum((h for h, _ in lines_labels), [])
        labels = sum((l for _, l in lines_labels), [])
        ax.legend(handles, labels, loc='best')
