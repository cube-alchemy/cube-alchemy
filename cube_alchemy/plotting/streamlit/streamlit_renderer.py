import pandas as pd
from typing import Dict, Any, Callable, List
import inspect
from ..abc_plot_renderer import PlotRenderer
from .handlers import PLOT_HANDLERS, register_plot as _register_plot


def _ensure_numeric_columns(df: pd.DataFrame, metrics: List[str]) -> None:
    """Convert string columns that contain numeric data back to float type for charting.
    
    This modifies the DataFrame in-place.
    """
    for col in df.columns:
        # Only process metrics and string columns
        if col in metrics and df[col].dtype == 'object':
            # Try to convert back to numeric
            try:
                # First, clean any formatting characters ($, %, commas, etc.)
                cleaned_series = df[col].astype(str).str.replace(r'[$,%]', '', regex=True)
                # Convert to numeric
                numeric_series = pd.to_numeric(cleaned_series, errors='coerce')
                
                # Only replace if conversion was successful
                if not numeric_series.isna().all():
                    df[col] = numeric_series
            except Exception:
                # If conversion fails, leave as is
                pass


class StreamlitRenderer(PlotRenderer):
    """
    Streamlit implementation of the PlotRenderer interface.

    This renderer dispatches to a registry of Streamlit-native plot handlers
    (PLOT_HANDLERS). Handlers can use st.* primitives directly and may return
    None (Streamlit renders inline) or a value; whatever they return will be
    passed back to the caller.
    """

    def __init__(self) -> None:
        """Renderer uses the global PLOT_HANDLERS registry."""
        pass

    def render(self, data: pd.DataFrame, plot_config: Dict[str, Any], **kwargs):
        import streamlit as st  # imported here to avoid hard dependency for non-Streamlit use

        plot_type = (plot_config.get('plot_type') or 'table').lower()
        dimensions = plot_config.get('dimensions') or []
        metrics = plot_config.get('metrics') or []
        color_by = plot_config.get('color_by')
        title = plot_config.get('title') or ''
        orientation = plot_config.get('orientation', 'vertical')
        sort_values = plot_config.get('sort_values', False)
        sort_ascending = plot_config.get('sort_ascending', True)
        limit = plot_config.get('limit')

        df = data
        
        # Ensure metrics are numeric for charts that need numeric data
        if metrics and plot_type not in ['table', 'markdown', 'pivot']:
            _ensure_numeric_columns(df, metrics)

        # Sort if requested (single-metric convenience only)
        if sort_values and isinstance(metrics, list) and len(metrics) == 1 and metrics[0] in df.columns:
            df = df.sort_values(by=metrics[0], ascending=sort_ascending)

        # Limit rows if requested
        if limit is not None:
            df = df.head(limit)

        # Use the global registry of handlers
        handler = PLOT_HANDLERS.get(plot_type)

        if handler is None:
            # Fallback: if no handler, try a simple display heuristic
            st.info(f"Unsupported plot type for Streamlit renderer: {plot_type}. Falling back to table view.")
            return PLOT_HANDLERS['table'](st=st, df=df, use_container_width=True)

        # Flexible call: we pass only parameters that the handler declares
        params = set(inspect.signature(handler).parameters.keys())
        call_kwargs: Dict[str, Any] = {}

        # Builder for kwargs
        if 'st' in params:
            call_kwargs['st'] = st
        if 'df' in params:
            call_kwargs['df'] = df
        if 'dimensions' in params:
            call_kwargs['dimensions'] = dimensions
        if 'metrics' in params:
            call_kwargs['metrics'] = metrics
        if 'color_by' in params:
            call_kwargs['color_by'] = color_by
        if 'orientation' in params:
            call_kwargs['orientation'] = orientation
        if 'stacked' in params:
            call_kwargs['stacked'] = bool(plot_config.get('stacked', False))
        if 'title' in params:
            call_kwargs['title'] = title
        if 'show_title' in params:
            call_kwargs['show_title'] = bool(kwargs.get('show_title', False))
        if 'pivot' in params:
            call_kwargs['pivot'] = plot_config.get('pivot')
        if 'sort_values' in params:
            call_kwargs['sort_values'] = plot_config.get('sort_values', False)
        if 'sort_ascending' in params:
            call_kwargs['sort_ascending'] = plot_config.get('sort_ascending', True)
        if 'sort_by' in params:
            call_kwargs['sort_by'] = plot_config.get('sort_by')
        if 'legend_position' in params:
            call_kwargs['legend_position'] = plot_config.get('legend_position', 'right')
        # Pass common visual kwargs if declared by handler
        for key in ('height', 'width', 'use_container_width'):
            if key in params and key in kwargs:
                call_kwargs[key] = kwargs[key]

        # Invoke handler
        result = handler(**call_kwargs)

        # If the handler didn't render a title and it's declared not to manage titles, set a header
        # Convention: if handler returns a truthy value 'rendered' with attribute _manages_title, skip. Keep it simple.
        if title and not getattr(result, '_manages_title', False) and plot_type not in ('table',):
            # Streamlit charts usually don't show a title; prepend a caption
            # Note: placing the title before handler would push it above charts; leave as-is for simplicity
            pass

        return result

    # Convenience method to register into the global registry from user code
    @staticmethod
    def register_plot(plot_type: str, handler: Callable[..., Any]) -> None:
        """Register a plot handler globally for Streamlit backend."""
        _register_plot(plot_type, handler)
