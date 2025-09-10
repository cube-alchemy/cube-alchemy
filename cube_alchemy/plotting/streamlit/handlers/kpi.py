from __future__ import annotations
from typing import Optional, List
import pandas as pd


def render_kpi(
    st,
    df: pd.DataFrame,
    *,
    dimensions: List[str] | None = None,
    metrics: List[str] | None = None,
    title: Optional[str] = None,
    show_title: bool = False,
    columns: int = 4,
    height: int | None = None,
):
    """Render all KPI values from a single-row DataFrame.

    - If `height` is provided, renders a compact Altair text chart sized to exactly `height` for alignment.
    - Otherwise, renders KPI cards using st.metric in a responsive grid.
    - If metrics are provided, only those columns are shown; else show numeric columns or all.
    """
    if df is None or df.empty:
        return st.write('No data for KPI.')

    row = df.iloc[0]

    # Determine which columns to show
    if metrics:
        cols = [c for c in metrics if c in df.columns]
    else:
        nums = df.select_dtypes(include=['number']).columns.tolist()
        cols = nums if nums else df.columns.tolist()

    if not cols:
        return st.write('No KPI metrics to display.')

    # Height-controlled chart path for alignment
    if height is not None and height > 0:
        import altair as alt
        # Build a small dataframe with metric/value as strings for display
        from numbers import Number
        import math
        value_strs = []
        for c in cols:
            v = row[c]
            if isinstance(v, Number) and not (isinstance(v, float) and math.isnan(v)):
                try:
                    value_strs.append(f"{v:,.2f}")
                except Exception:
                    value_strs.append(str(v))
            else:
                value_strs.append(str(v))

        kpi_df = pd.DataFrame({
            'metric': [str(c) for c in cols],
            'value_str': value_strs,
        })
        # Compute per-row step to fill the requested height (clamped)
        n = max(len(kpi_df), 1)
        step = int(max(min(height / n, 80), 26))
        font_size = int(max(min(step * 0.55, 22), 11))

        y_enc = alt.Y('metric:N', sort=None,
                       axis=alt.Axis(title=None, labels=False, ticks=False))
        x_enc = alt.X('pos:Q', scale=alt.Scale(domain=[0, 1]), axis=None)

        labels_df = kpi_df.copy()
        labels_df['pos'] = 0
        values_df = kpi_df.copy()
        values_df['pos'] = 1

        labels = alt.Chart(labels_df).mark_text(align='left', baseline='middle', dx=6,
                                                color='#666', fontSize=font_size).encode(
            x=x_enc, y=y_enc, text='metric:N'
        )
        values = alt.Chart(values_df).mark_text(align='right', baseline='middle', dx=-6,
                                                fontSize=font_size).encode(
            x=x_enc, y=y_enc, text='value_str:N'
        )
        chart = (labels + values).properties(height=step * n).configure_view(
            strokeWidth=0
        )
        if show_title and title:
            chart = chart.properties(title=title)
        return st.altair_chart(chart, use_container_width=True)

    # Fallback to KPI cards
    if show_title and title:
        st.subheader(title)

    n = len(cols)
    if columns <= 0:
        columns = min(4, n)
    grid = st.columns(min(columns, n))
    for i, col in enumerate(cols):
        with grid[i % len(grid)]:
            st.metric(label=str(col), value=row[col])
    return None
