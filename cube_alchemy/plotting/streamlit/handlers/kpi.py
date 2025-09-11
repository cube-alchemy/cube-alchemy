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
    width: int | None = None,
    use_container_width: bool = True,
):
    """Render KPI values; aggregates when multiple rows are present (e.g., after selections).

    Behavior:
    - If multiple rows: aggregate numeric columns with sum (default), non-numeric are ignored unless explicitly requested in `metrics`.
    - If `height` is provided, render a compact Altair text chart sized to exactly `height` for alignment.
    - Else render KPI cards with st.metric.
    - If `metrics` provided, restrict to those columns (aggregated if needed).
    """
    if df is None or df.empty:
        return st.write('No data for KPI.')

    work = df.copy()
    # Aggregate if more than one row to make KPI stable under selections
    if len(work) > 1:
        num_cols = work.select_dtypes(include=['number']).columns
        agg_row = work[num_cols].sum(numeric_only=True)
        row = agg_row
    else:
        row = work.iloc[0]

    # Determine which columns to show
    if metrics:
        # Use requested metrics; if aggregated, ensure presence
        available = set(row.index)
        cols = [c for c in metrics if c in available]
    else:
        nums = row.index.tolist() if isinstance(row, pd.Series) else work.select_dtypes(include=['number']).columns.tolist()
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
        if show_title and title:
            chart = chart.properties(title=title)
        return st.altair_chart(chart, use_container_width=use_container_width)

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
