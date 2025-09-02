import pandas as pd
from typing import Dict, Any
from ..abc_plot_renderer import PlotRenderer
from .handlers import PLOT_HANDLERS
import matplotlib.pyplot as plt

class MatplotlibRenderer(PlotRenderer):
    """
    Matplotlib implementation of the PlotRenderer interface.
    """

    def render(self, data: pd.DataFrame, plot_config: Dict[str, Any], **kwargs):
        # Control display from caller; default is to show figures
        show: bool = kwargs.pop('show', False)

        plot_type = (plot_config.get('plot_type') or 'table').lower()
        dims = plot_config.get('dimensions') or []
        mets = plot_config.get('metrics') or []
        color_by = plot_config.get('color_by')
        title = plot_config.get('title') or ''
        figsize = plot_config.get('figsize', (10, 6))
        orientation = plot_config.get('orientation', 'vertical')
        sort_values = plot_config.get('sort_values', False)
        sort_ascending = plot_config.get('sort_ascending', True)
        limit = plot_config.get('limit')

        df = data

        # Sort if requested (single-metric convenience only)
        if sort_values and isinstance(mets, list) and len(mets) == 1 and mets[0] in df.columns:
            df = df.sort_values(by=mets[0], ascending=sort_ascending)

        # Limit rows if requested
        if limit is not None:
            df = df.head(limit)

    # Special-case: 'table' plot returns the DataFrame for external display (no figure)
        if plot_type == 'table':
            # simply return the data for tabular display
            if show:
                print(df)
            return df

        fig, ax = plt.subplots(figsize=figsize)

        handler = PLOT_HANDLERS.get(plot_type)
        if handler is None:
            ax.text(0.5, 0.5, f"Unsupported plot type: {plot_type}", ha='center')
        else:
            # Handlers share a unified signature:
            # handler(ax, df, dims, mets, color_by, orientation, stacked=False)
            stacked = bool(plot_config.get('stacked', False))
            # Many handlers ignore stacked; bar uses it.
            handler(ax, df, dims, mets, color_by, orientation, stacked)

        ax.set_title(title)
        fig.tight_layout()

        if show:
            plt.show()
        # Always close to prevent notebook auto-display/double-rendering
        plt.close(fig)

        return fig

    def _category_labels(self, df: pd.DataFrame, dims: list) -> pd.Series:
        # Kept for backward compatibility if ever used externally; not used by new handlers.
        if dims:
            return df[dims].astype(str).agg(' | '.join, axis=1)
        return pd.Series(['All'] * len(df), index=df.index)
