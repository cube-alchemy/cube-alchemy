from __future__ import annotations
from typing import Optional, List, Dict
import pandas as pd


def render_pie(
    st,
    df: pd.DataFrame,
    *,
    dimensions: List[str] | None = None,
    metrics: List[str] | None = None,
    height: int | None = 400,
    width: int | None = None,
    use_container_width: bool = True,
    title: Optional[str] = None,
    show_title: bool = False,
    formatter: Optional[Dict[str, str]] = None,
):
    """Render a simple pie chart: exactly one dimension and one metric.

    - Uses Altair arc mark to render a pie.
    - If multiple rows, values are aggregated by sum per category.
    - Ignores extra dimensions/metrics beyond the first of each.
    """
    import altair as alt

    if df is None or df.empty:
        return st.write('No data to plot.')

    dim = (dimensions or [])[:1]
    met = [m for m in (metrics or []) if m in df.columns][:1]

    # Fallbacks if not provided
    if not dim:
        # pick first non-numeric column
        cat_candidates = df.select_dtypes(exclude=['number']).columns.tolist()
        if not cat_candidates:
            # if none, create a single category
            df = df.copy()
            df['__category__'] = 'All'
            dim = ['__category__']
        else:
            dim = [cat_candidates[0]]
    if not met:
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        if not num_cols:
            return st.write('No numeric metric found for pie chart.')
        met = [num_cols[0]]

    d, m = dim[0], met[0]
    if d not in df.columns or m not in df.columns:
        return st.write('Missing required columns for pie chart.')

    # Aggregate by category if needed
    work = df.groupby(d, dropna=False, as_index=False)[m].sum(numeric_only=True)

    # Build pie chart
    total = work[m].sum()
    work['__percent__'] = (work[m] / total) * 100 if total != 0 else 0
    
    # Function to apply formatting based on column names
    def format_value(val, col_name):
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
                # If formatting fails, return the original value
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
    
    # Create formatted tooltip column
    formatted_col = f"{m}_formatted"
    work[formatted_col] = work[m].apply(lambda x: format_value(x, m))

    chart = alt.Chart(work).mark_arc().encode(
        theta=alt.Theta(f'{m}:Q', stack=True),
        color=alt.Color(f'{d}:N', title=d),
        tooltip=[
            alt.Tooltip(f'{d}:N', title=d), 
            alt.Tooltip(f'{m}:Q', title=m, format=',.2f'),
            alt.Tooltip(f'{formatted_col}:N', title=f'{m} Formatted'),
            alt.Tooltip('__percent__:Q', title='% of total', format='.1f')
        ]
    )

    if title:
        chart = chart.properties(title=title)
    if height:
        chart = chart.properties(height=height)
    if width:
        chart = chart.properties(width=width)

    return st.altair_chart(chart, use_container_width=use_container_width)
