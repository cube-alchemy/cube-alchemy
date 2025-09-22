from typing import Callable, Any, Dict
from .series import render_bar, render_line, render_area
from .combo import render_combo
from .kpi import render_kpi
from .pie import render_pie

# Registry mapping plot types to handler callables with a common signature
# Handlers can accept a flexible subset of arguments:
#   handler(df)
#   handler(df, dimensions, metrics, color_by, orientation, **kwargs)
#   handler(st, df, ...)  # if access to the streamlit module is needed
PLOT_HANDLERS: Dict[str, Callable[..., Any]] = {
    'bar': render_bar,
    'line': render_line,
    'area': render_area,
    'combo': render_combo,
    'kpi': render_kpi,
    'pie': render_pie,
}


def register_plot(plot_type: str, handler: Callable[..., Any]) -> None:
    """Register or override a Streamlit plot handler at runtime.

    The handler signature is flexible and parameters are passed by name.
    Valid parameter names include: df, dimensions, metrics, color_by,
    orientation, stacked, st (streamlit module), and any future ones.
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
