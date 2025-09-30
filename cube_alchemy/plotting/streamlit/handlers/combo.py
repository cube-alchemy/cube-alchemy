from __future__ import annotations
from typing import List, Optional, Dict, Any, Union
import pandas as pd


def render_combo(
    st,
    df: pd.DataFrame,
    *,
    dimensions: List[str] | None,
    metrics: List[str] | None,
    color_by: Optional[str] = None,
    orientation: str = 'vertical',
    height: int | None = None,
    width: int | None = None,
    use_container_width: bool = True,
    title: Optional[str] = None,
    show_title: bool = False,
    formatter: Optional[Dict[str, str]] = None,
):
    """Combo chart: first metric as bars, second metric as line.

    - Requires at least 1 dimension and 2 metrics.
    - Implemented using altair via st.altair_chart to get dual-encoding.
    - Supports formatting of values with the formatter parameter.
    """
    import altair as alt
    import numpy as np
    
    dimensions = dimensions or []
    metrics = metrics or []
    if len(dimensions) < 1 or len(metrics) < 2:
        return st.write('Combo requires at least 1 dimension and 2 metrics')

    dim = dimensions[0]
    m1, m2 = metrics[0], metrics[1]
    if dim not in df.columns or m1 not in df.columns or m2 not in df.columns:
        return st.write('Missing required columns for combo chart')
    
    # Make a copy of the dataframe to avoid modifying the original
    plot_df = df.copy()
    
    # Function to apply formatting based on column names
    def format_value(val: Any, col_name: str) -> Any:
        # Handle already formatted strings
        if isinstance(val, str):
            return val
            
        # Apply formatter if provided for this column
        if formatter and col_name in formatter:
            fmt_spec = formatter[col_name]
            try:
                return fmt_spec.format(val)
            except Exception:
                # If formatting fails, return the original value
                return val
                
        # Special formatting for percentage columns if no explicit formatter
        if isinstance(col_name, str) and ('%' in col_name or 'percent' in col_name.lower() or 'margin' in col_name.lower()):
            if isinstance(val, (int, float, np.integer, np.floating)):
                # Multiply by 100 for proper percentage display
                return f"{val * 100:.2f}%"
        
        # No special formatting needed
        return val

    # Prepare data with formatting if needed
    # For numeric columns that need to be plotted, we need to ensure they're numeric
    # We'll create formatted tooltips separately
    
    # Create tooltip columns with formatted values if needed
    if formatter:
        for col in [m1, m2]:
            if col in formatter:
                # Create tooltip column with formatted values
                tooltip_col = f"{col}_formatted"
                plot_df[tooltip_col] = plot_df[col].apply(lambda x: format_value(x, col))
    
    # Base encodings
    x_enc = alt.X(f'{dim}:N', sort=None, axis=alt.Axis(labelAngle= -45))
    
    # Create tooltip selection based on formatter existence
    tooltip_m1 = f"{m1}_formatted" if formatter and m1 in formatter else m1
    tooltip_m2 = f"{m2}_formatted" if formatter and m2 in formatter else m2
    
    bar = alt.Chart(plot_df).mark_bar(opacity=0.8).encode(
        x=x_enc if orientation == 'vertical' else alt.Y(f'{dim}:N', sort=None),
        y=alt.Y(f'{m1}:Q', title=m1) if orientation == 'vertical' else alt.X(f'{m1}:Q', title=m1),
        color=alt.value('#4C78A8'),
        tooltip=[dim, tooltip_m1]
    )

    line = alt.Chart(plot_df).mark_line(point=True, color='#E45756').encode(
        x=x_enc if orientation == 'vertical' else alt.Y(f'{dim}:N', sort=None),
        y=alt.Y(f'{m2}:Q', title=m2) if orientation == 'vertical' else alt.X(f'{m2}:Q', title=m2),
        tooltip=[dim, tooltip_m2]
    )

    chart = alt.layer(bar, line).resolve_scale(
        y='independent' if orientation == 'vertical' else 'independent',
        x='shared' if orientation == 'vertical' else 'independent',
    )

    if title:
        chart = chart.properties(title=title)
    if height:
        chart = chart.properties(height=height)
    if width:
        chart = chart.properties(width=width)
    if use_container_width:
        return st.altair_chart(chart, use_container_width=True)
    return st.altair_chart(chart)
