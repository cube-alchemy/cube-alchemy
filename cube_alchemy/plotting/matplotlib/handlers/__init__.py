from .series import render_bar, render_line, render_area
from .combo import render_combo
from .scatter import render_scatter
from .pie import render_pie
from .heatmap import render_heatmap
from typing import Callable, Any, Dict

# Registry mapping plot types to handler callables with a common signature
# handler(ax, df, dims, mets, color_by, orientation)
PLOT_HANDLERS = {
    'bar': render_bar,
    'line': render_line,
    'area': render_area,
    'scatter': render_scatter,
    'pie': render_pie,
    'heatmap': render_heatmap,
    'combo': render_combo,
}

def register_plot(plot_type: str, handler: Callable[..., Any]) -> None:
    """Register or override a matplotlib plot handler at runtime.

    Handler signature is flexible:
      - Minimal:          handler(df)
      - With context:     handler(df, dims, mets, color_by, orientation, stacked=False)
      - Axes-based:       handler(ax, df, ...)
      Declare only the parameters you need; the renderer passes them by name.
      'mets' can also be declared as 'metrics' (alias).
    """
    if not isinstance(plot_type, str) or not plot_type.strip():
        raise ValueError("plot_type must be a non-empty string")
    PLOT_HANDLERS[plot_type.lower()] = handler


def unregister_plot(plot_type: str) -> None:
    """Unregister a previously registered plot handler (no-op if missing)."""
    if isinstance(plot_type, str):
        PLOT_HANDLERS.pop(plot_type.lower(), None)


def get_plot_handlers() -> Dict[str, Callable[..., Any]]:
    """Return a shallow copy of the current handlers registry."""
    return dict(PLOT_HANDLERS)


__all__ = ['PLOT_HANDLERS', 'register_plot', 'unregister_plot', 'get_plot_handlers']
