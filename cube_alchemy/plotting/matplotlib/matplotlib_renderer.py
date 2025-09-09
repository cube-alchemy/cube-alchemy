import pandas as pd
from typing import Dict, Any, Callable
import inspect
from ..abc_plot_renderer import PlotRenderer
from .handlers import PLOT_HANDLERS, register_plot as _register_plot
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes

class MatplotlibRenderer(PlotRenderer):
    """
    Matplotlib implementation of the PlotRenderer interface.
    """

    def __init__(self) -> None:
        """Renderer uses the global PLOT_HANDLERS registry."""
        pass

    def render(self, data: pd.DataFrame, plot_config: Dict[str, Any], **kwargs):
        # Control display from caller; default is to show figures
        show: bool = kwargs.pop('show', False)

        plot_type = (plot_config.get('plot_type') or 'table').lower()
        dimensions = plot_config.get('dimensions') or []
        metrics = plot_config.get('metrics') or []
        color_by = plot_config.get('color_by')
        title = plot_config.get('title') or ''
        figsize = plot_config.get('figsize', (10, 6))
        orientation = plot_config.get('orientation', 'vertical')
        sort_values = plot_config.get('sort_values', False)
        sort_ascending = plot_config.get('sort_ascending', True)
        limit = plot_config.get('limit')

        df = data

        # Sort if requested (single-metric convenience only)
        if sort_values and isinstance(metrics, list) and len(metrics) == 1 and metrics[0] in df.columns:
            df = df.sort_values(by=metrics[0], ascending=sort_ascending)

        # Limit rows if requested
        if limit is not None:
            df = df.head(limit)

        # Special-case: 'table' plot returns the DataFrame for external display (no figure)
        if plot_type == 'table':
            # simply return the data for tabular display
            if show:
                print(df)
            return df

        # Use the global registry of handlers
        handler = PLOT_HANDLERS.get(plot_type)

        fig: Figure | None = None
        ax: Axes | None = None
        used_fig: Figure | None = None
        used_ax: Axes | None = None

        if handler is None:
            fig, ax = plt.subplots(figsize=figsize)
            ax.text(0.5, 0.5, f"Unsupported plot type: {plot_type}", ha='center')
            used_fig, used_ax = fig, ax
        else:
            # Flexible call: pass only the parameters the handler accepts
            params = set(inspect.signature(handler).parameters.keys())
            needs_ax = any(p in params for p in ("ax", "axes"))

            if needs_ax:
                fig, ax = plt.subplots(figsize=figsize)

            call_kwargs: Dict[str, Any] = {}
            # Build kwargs selectively
            if "df" in params:
                call_kwargs["df"] = df
            if "dimensions" in params:
                call_kwargs["dimensions"] = dimensions
            if "metrics" in params or "metrics" in params:
                # Support either name
                key = "metrics" if "metrics" in params else "metrics"
                call_kwargs[key] = metrics
            if "color_by" in params:
                call_kwargs["color_by"] = color_by
            if "orientation" in params:
                call_kwargs["orientation"] = orientation
            if "stacked" in params:
                call_kwargs["stacked"] = bool(plot_config.get('stacked', False))
            if "ax" in params and ax is not None:
                call_kwargs["ax"] = ax

            # Invoke handler
            result = handler(**call_kwargs)

            # Normalize possible returns
            if isinstance(result, Figure):
                used_fig = result
                used_ax = result.axes[0] if result.axes else None
                # Close any placeholder fig if different
                if fig is not None and used_fig is not fig:
                    plt.close(fig)
            elif isinstance(result, Axes):
                used_ax = result
                used_fig = result.figure
                if fig is not None and used_fig is not fig:
                    plt.close(fig)
            elif isinstance(result, tuple) and len(result) == 2:
                f, a = result
                if isinstance(f, Figure) and isinstance(a, Axes):
                    used_fig, used_ax = f, a
                    if fig is not None and used_fig is not fig:
                        plt.close(fig)
            else:
                # If the handler didn't return a fig/ax but we created one, use it only if it has data
                if ax is not None and (getattr(ax, 'has_data', lambda: False)()):
                    used_fig, used_ax = fig, ax
                else:
                    used_fig, used_ax = None, None

        # Title and layout on the used figure/axes
        if used_ax is not None:
            try:
                used_ax.set_title(title)
            except Exception:
                pass
        elif used_fig is not None:
            try:
                used_fig.suptitle(title)
            except Exception:
                pass

        if used_fig is not None:
            try:
                used_fig.tight_layout()
            except Exception:
                pass

            if show:
                plt.show()
            # Always close to prevent notebook auto-display/double-rendering
            plt.close(used_fig)
            return used_fig
        else:
            # No figure produced/drawn; return data for tabular or downstream use
            return df

    # Convenience method to register into the global registry from user code
    @staticmethod
    def register_plot(plot_type: str, handler: Callable[..., Any]) -> None:
        """Register a plot handler globally for matplotlib backend."""
        _register_plot(plot_type, handler)
