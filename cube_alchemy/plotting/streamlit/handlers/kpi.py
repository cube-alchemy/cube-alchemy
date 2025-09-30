from __future__ import annotations
from typing import Optional, List, Dict, Any, Union
import pandas as pd


# Shared helper function for formatting values
def _format_value(val, col_name, formatter=None):
    """Format a value based on column name and formatter.
    
    Args:
        val: The value to format
        col_name: The column name for context-aware formatting
        formatter: Optional dictionary mapping column names to format strings
        
    Returns:
        Formatted value as a string
    """
    import numpy as np
    
    # Handle already formatted strings
    if isinstance(val, str):
        return val
        
    # Apply formatter if provided for this column
    if formatter and col_name in formatter:
        fmt_spec = formatter[col_name]
        try:
            return fmt_spec.format(val)
        except Exception:
            # If formatting fails, continue to default formatting
            pass
            
    # Special formatting for percentage columns if no explicit formatter
    if isinstance(col_name, str) and ('%' in col_name or 'percent' in col_name.lower() or 'margin' in col_name.lower()):
        if isinstance(val, (int, float, np.integer, np.floating)):
            # Multiply by 100 for proper percentage display
            return f"{val * 100:.2f}%"
    
    # Default to currency formatting for numbers
    if isinstance(val, (int, float, np.integer, np.floating)):
        return f"${val:,.0f}"
        
    # Return other values as-is
    return val


def render_kpi(
    st,
    df: pd.DataFrame,
    *,
    dimensions: List[str] | None = None,
    metrics: List[str] | None = None,
    title: Optional[str] = None,
    columns: int = 4,
    height: int | None = None,
    width: int | None = None,
    use_container_width: bool = True,
    formatter: Optional[Dict[str, str]] = None,
):
    """Render KPI values from a dataframe.

    Behavior:
    - Uses the first row of data
    - If title is provided, uses it as the KPI label
    - Otherwise uses the column name as the label
    - Formats values according to the formatter parameter
    """
    # Basic validation
    if df is None or df.empty:
        return st.write('No data for KPI.')
    
    # Special case for height-controlled chart path for alignment
    if height is not None and height > 0:
        return _render_kpi_with_altair(
            st, df, dimensions=dimensions, metrics=metrics,
            title=title, height=height, width=width,
            use_container_width=use_container_width, formatter=formatter
        )
    
    # Use the dataframe directly
    work_df = df
    
    # Always use the first row directly
    row = work_df.iloc[0]
    
    # Determine which columns to show
    if metrics:
        # Filter to requested metrics that exist in the dataframe
        available = set(work_df.columns)
        cols = [c for c in metrics if c in available]
    else:
        # Use all columns
        cols = work_df.columns.tolist()
    
    if not cols:
        return st.write('No KPI metrics to display.')
    
    # Center everything in a container
    with st.container():
        # For single column case - use title as label if provided
        if len(cols) == 1 and title:
            col = cols[0]
            # Get the value and format it appropriately
            val = row[col]
            formatted_val = _format_value(val, col, formatter)
            
            # Use CSS to center the metric
            # Create a single centered column
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col2:
                # Display as a single metric with the title as label
                st.metric(label=title, value=formatted_val)
            return None
        
        # For multiple columns, use column names as labels
        # Arrange in a grid with the specified number of columns
        if columns <= 0:
            columns = min(4, len(cols))
        
        # Create grid for metrics
        grid = st.columns(min(columns, len(cols)))
        
        # Display each metric
        for i, col in enumerate(cols):
            with grid[i % len(grid)]:
                # Display with column name as label
                # Get the value and format it appropriately
                val = row[col]
                formatted_val = _format_value(val, col, formatter)
                
                # Pass the formatted value to the metric
                st.metric(label=col, value=formatted_val)
        
    return None


def _render_kpi_with_altair(
    st, df, *, dimensions=None, metrics=None, 
    title=None, height=None, width=None, 
    use_container_width=True, formatter=None
):
    """Helper function to render KPIs with Altair charts for precise height control."""
    import altair as alt
    
    # Always use the first row directly
    row = df.iloc[0]
    
    # Determine which columns to show
    if metrics:
        available = set(df.columns)
        cols = [c for c in metrics if c in available]
    else:
        cols = df.columns.tolist()
    
    if not cols:
        return st.write('No KPI metrics to display.')
    
    # Build a small dataframe with metric/value as strings for display
    value_strs = []
    
    # For single column with title, use title as the label
    if len(cols) == 1 and title:
        labels = [title]
        # Get value, format it, and convert to string for display
        col = cols[0]
        val = row[col]
        formatted_val = _format_value(val, col, formatter)
        value_strs = [formatted_val]
    else:
        # Otherwise use column names
        labels = [str(c) for c in cols]
        for c in cols:
            # Get value, format it, and convert to string for display
            val = row[c]
            formatted_val = _format_value(val, c, formatter)
            value_strs.append(formatted_val)
    
    kpi_df = pd.DataFrame({
        'metric': labels,
        'value_str': value_strs,
    })
    
    # Compute per-row step to fill the requested height (clamped)
    n = max(len(kpi_df), 1)
    step = int(max(min(height / n, 90), 34))
    label_fs = int(max(min(step * 0.40, 20), 10))
    value_fs = int(max(min(step * 0.60, 28), 12))
    
    # Use centered x position and offset with dy to put value below label
    kpi_df['pos'] = 0.5
    x_enc = alt.X('pos:Q', scale=alt.Scale(domain=[0, 1]), axis=None)
    y_enc = alt.Y('metric:N', sort=None, axis=alt.Axis(title=None, labels=False, ticks=False))
    
    labels = alt.Chart(kpi_df).mark_text(align='center', baseline='bottom', dy=-4,
                                         color='#666', fontSize=label_fs).encode(
        x=x_enc, y=y_enc, text='metric:N'
    )
    values = alt.Chart(kpi_df).mark_text(align='center', baseline='top', dy=8,
                                         fontSize=value_fs).encode(
        x=x_enc, y=y_enc, text='value_str:N'
    )
    
    chart = (labels + values).properties(height=step * n)
    if width:
        chart = chart.properties(width=width)
    chart = chart.configure_view(strokeWidth=0)
    
    return st.altair_chart(chart, use_container_width=use_container_width)
